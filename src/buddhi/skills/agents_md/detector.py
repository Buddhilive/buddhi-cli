"""Repository facts detector for agents-md."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from buddhi.skills.agents_md.models import CommandSet, RepoFacts

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return {}


def detect_repo_facts(root: Path | None = None) -> RepoFacts:
    """Analyze a repository and extract facts for AGENTS.md."""
    base = Path(root or Path.cwd()).resolve()

    name = base.name
    description = ""
    primary_language = "unknown"
    commands = CommandSet()

    # 1. Python detection
    pyproject_path = base / "pyproject.toml"
    setup_py = base / "setup.py"
    if pyproject_path.is_file() or setup_py.is_file():
        primary_language = "python"
        data = _read_toml(pyproject_path) if pyproject_path.is_file() else {}

        # Project metadata
        project_sec = data.get("project", {})
        poetry_sec = data.get("tool", {}).get("poetry", {})
        if project_sec.get("name"):
            name = project_sec["name"]
        elif poetry_sec.get("name"):
            name = poetry_sec["name"]

        if project_sec.get("description"):
            description = project_sec["description"]
        elif poetry_sec.get("description"):
            description = poetry_sec["description"]

        # Package manager & runners
        has_uv = (base / "uv.lock").is_file()
        has_poetry = (base / "poetry.lock").is_file()
        has_pipfile = (base / "Pipfile.lock").is_file()

        if has_uv:
            commands.install = "uv sync"
            runner = "uv run"
            commands.build = "uv build"
        elif has_poetry:
            commands.install = "poetry install"
            runner = "poetry run"
            commands.build = "poetry build"
        elif has_pipfile:
            commands.install = "pipenv install --dev"
            runner = "pipenv run"
        else:
            commands.install = "pip install -e ."
            runner = ""

        # Test command
        has_pytest = (
            "pytest" in data.get("tool", {})
            or "pytest" in str(project_sec.get("dependencies", []))
            or "pytest" in str(poetry_sec.get("group", {}))
            or (base / "tests").is_dir()
        )
        if has_pytest:
            commands.test = f"{runner} pytest".strip()
        else:
            commands.test = f"{runner} python -m unittest".strip()

        # Lint command
        tool_sec = data.get("tool", {})
        if "ruff" in tool_sec:
            commands.lint = f"{runner} ruff check .".strip()
        elif "flake8" in str(poetry_sec) or (base / ".flake8").is_file():
            commands.lint = f"{runner} flake8".strip()

        # Typecheck command
        if "mypy" in tool_sec or (base / "mypy.ini").is_file():
            commands.typecheck = f"{runner} mypy src/".strip()
        elif "pyright" in tool_sec or (base / "pyrightconfig.json").is_file():
            commands.typecheck = f"{runner} pyright".strip()

    # 2. Node / JS / TS detection
    pkg_json_path = base / "package.json"
    if pkg_json_path.is_file():
        pkg_data = _read_json(pkg_json_path)
        if primary_language == "unknown":
            primary_language = "javascript"

        if pkg_data.get("name"):
            name = pkg_data["name"]
        if pkg_data.get("description"):
            description = pkg_data["description"]

        scripts = pkg_data.get("scripts", {})
        dev_deps = pkg_data.get("devDependencies", {})

        if "typescript" in dev_deps or (base / "tsconfig.json").is_file():
            primary_language = "typescript"

        if (base / "pnpm-lock.yaml").is_file():
            pm = "pnpm"
        elif (base / "yarn.lock").is_file():
            pm = "yarn"
        elif (base / "bun.lockb").is_file():
            pm = "bun"
        else:
            pm = "npm"

        commands.install = f"{pm} install"

        if "build" in scripts:
            commands.build = f"{pm} run build"
        if "test" in scripts:
            commands.test = f"{pm} run test"
        if "lint" in scripts:
            commands.lint = f"{pm} run lint"
        elif "eslint" in dev_deps:
            commands.lint = f"{pm} exec eslint ."

        if "typecheck" in scripts:
            commands.typecheck = f"{pm} run typecheck"
        elif primary_language == "typescript":
            commands.typecheck = f"{pm} exec tsc --noEmit"

    # 3. Rust detection
    cargo_path = base / "Cargo.toml"
    if cargo_path.is_file():
        if primary_language == "unknown":
            primary_language = "rust"
        cargo_data = _read_toml(cargo_path)
        pkg = cargo_data.get("package", {})
        if pkg.get("name"):
            name = pkg["name"]
        if pkg.get("description"):
            description = pkg["description"]

        commands.build = "cargo build"
        commands.test = "cargo test"
        commands.lint = "cargo clippy"

    # 4. Go detection
    go_mod_path = base / "go.mod"
    if go_mod_path.is_file():
        if primary_language == "unknown":
            primary_language = "go"
        try:
            go_mod_text = go_mod_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            go_mod_text = ""

        lines = go_mod_text.splitlines()
        if lines and lines[0].startswith("module "):
            name = lines[0].split("module ", 1)[1].strip().split("/")[-1]

        commands.install = "go mod download"
        commands.build = "go build ./..."
        commands.test = "go test ./..."
        commands.lint = "golangci-lint run"

    # 5. Makefile detection (fallback or supplements)
    makefile_path = base / "Makefile"
    if makefile_path.is_file():
        try:
            content = makefile_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = ""

        targets = [
            line.split(":")[0].strip()
            for line in content.splitlines()
            if ":" in line and not line.startswith(("\t", " ", "#", "."))
        ]
        if "build" in targets and not commands.build:
            commands.build = "make build"
        if "test" in targets and not commands.test:
            commands.test = "make test"
        if "lint" in targets and not commands.lint:
            commands.lint = "make lint"

    # 6. Readme fallback for description
    readme_path = base / "README.md"
    if not description and readme_path.is_file():
        try:
            readme_text = readme_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            readme_text = ""

        for line in (ln.strip() for ln in readme_text.splitlines() if ln.strip()):
            if not line.startswith("#") and not line.startswith("["):
                description = line
                break

    # 7. Antigravity harness & OKF documentation detection
    skills_dir = base / ".agents" / "skills"
    skills = (
        [p.name for p in skills_dir.iterdir() if p.is_dir()]
        if skills_dir.is_dir()
        else []
    )
    has_rules = (base / ".agents" / "rules").is_dir()
    has_buddhi_docs = (base / ".buddhi" / "docs").is_dir()

    return RepoFacts(
        name=name,
        description=description,
        commands=commands,
        primary_language=primary_language,
        skills=skills,
        has_skills=bool(skills),
        has_rules=has_rules,
        has_buddhi_docs=has_buddhi_docs,
    )
