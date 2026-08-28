"""Shared helpers for Spec-Driven Development (SDD) Python scripts in buddhi-cli."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path


def _trim_trailing_separators(value: Path) -> str:
    text = str(value)
    while len(text) > 1 and text.endswith((os.sep, "/")):
        text = text[:-1]
    return text


def find_buddhi_root(start_dir: Path | None = None) -> Path | None:
    current = (start_dir or Path.cwd()).resolve()
    while True:
        if (current / ".buddhi").is_dir() or (current / ".agents").is_dir() or (current / ".specify").is_dir():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def resolve_specify_init_dir() -> Path:
    raw = os.environ.get("SPECIFY_INIT_DIR", "")
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    try:
        init_root = candidate.resolve(strict=True)
    except OSError:
        print(
            f"ERROR: SPECIFY_INIT_DIR does not point to an existing directory: {raw}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not init_root.is_dir():
        print(
            f"ERROR: SPECIFY_INIT_DIR does not point to an existing directory: {raw}",
            file=sys.stderr,
        )
        raise SystemExit(1)
    return init_root


def get_repo_root(script_file: Path | None = None) -> Path:
    if os.environ.get("SPECIFY_INIT_DIR"):
        return resolve_specify_init_dir()

    root = find_buddhi_root()
    if root is not None:
        return root

    if script_file is not None:
        script_root = find_buddhi_root(script_file.resolve().parent)
        if script_root is not None:
            return script_root

    return Path.cwd().resolve()


def get_current_branch() -> str:
    env_branch = os.environ.get("SPECIFY_FEATURE", "")
    if env_branch:
        return env_branch
    try:
        res = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def read_feature_json_feature_directory(repo_root: Path) -> str:
    for candidate in [
        repo_root / ".buddhi" / "feature.json",
        repo_root / ".specify" / "feature.json",
    ]:
        if candidate.is_file():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    val = data.get("feature_directory")
                    if isinstance(val, str) and val.strip():
                        return val.strip()
            except (OSError, UnicodeError, json.JSONDecodeError):
                pass
    return ""


def _json_dump(data: dict[str, str]) -> str:
    return json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n"


def persist_feature_json(repo_root: Path, feature_dir_value: str) -> None:
    value = feature_dir_value
    relative = Path(value)
    if relative.is_absolute():
        try:
            value = relative.relative_to(repo_root).as_posix()
        except ValueError:
            value = str(relative)

    current = read_feature_json_feature_directory(repo_root)
    if current == value:
        return

    buddhi_dir = repo_root / ".buddhi"
    buddhi_dir.mkdir(parents=True, exist_ok=True)
    (buddhi_dir / "feature.json").write_bytes(
        _json_dump({"feature_directory": value}).encode("utf-8")
    )


@dataclass(frozen=True)
class FeaturePaths:
    repo_root: Path
    current_branch: str
    feature_dir: Path
    feature_spec: Path
    impl_plan: Path
    tasks: Path
    research: Path
    data_model: Path
    quickstart: Path
    contracts_dir: Path


def get_feature_paths(
    *, no_persist: bool = False, script_file: Path | None = None
) -> FeaturePaths:
    repo_root = get_repo_root(script_file)
    current_branch = get_current_branch()

    feature_dir_raw = os.environ.get("SPECIFY_FEATURE_DIRECTORY", "")
    if feature_dir_raw:
        feature_dir = Path(feature_dir_raw)
        if not feature_dir.is_absolute():
            feature_dir = repo_root / feature_dir
        if not no_persist:
            persist_feature_json(repo_root, feature_dir_raw)
    else:
        stored = read_feature_json_feature_directory(repo_root)
        if stored:
            feature_dir = Path(stored)
            if not feature_dir.is_absolute():
                feature_dir = repo_root / feature_dir
        elif current_branch:
            # Check if .buddhi/specs/<branch> or specs/<branch> exists
            buddhi_spec_dir = repo_root / ".buddhi" / "specs" / current_branch
            root_spec_dir = repo_root / "specs" / current_branch
            if buddhi_spec_dir.is_dir():
                feature_dir = buddhi_spec_dir
            elif root_spec_dir.is_dir():
                feature_dir = root_spec_dir
            else:
                feature_dir = buddhi_spec_dir
        else:
            print(
                "ERROR: Feature directory not found. Set SPECIFY_FEATURE_DIRECTORY "
                "or run the /specify command to create .buddhi/specs/<feature>.",
                file=sys.stderr,
            )
            raise SystemExit(1)

    if not current_branch:
        current_branch = Path(_trim_trailing_separators(feature_dir)).name

    return FeaturePaths(
        repo_root=repo_root,
        current_branch=current_branch,
        feature_dir=feature_dir,
        feature_spec=feature_dir / "spec.md",
        impl_plan=feature_dir / "plan.md",
        tasks=feature_dir / "tasks.md",
        research=feature_dir / "research.md",
        data_model=feature_dir / "data-model.md",
        quickstart=feature_dir / "quickstart.md",
        contracts_dir=feature_dir / "contracts",
    )


_SAFE_COMPONENT_PATTERN = re.compile(r"[a-z0-9-]+")


def _is_safe_component(value: object) -> bool:
    return (
        isinstance(value, str)
        and _SAFE_COMPONENT_PATTERN.fullmatch(value) is not None
    )


def _normalize_priority(value: object) -> int:
    if isinstance(value, bool):
        return 10
    if isinstance(value, (int, str)):
        try:
            priority = int(value)
            return priority if priority >= 1 else 10
        except (TypeError, ValueError, OverflowError):
            return 10
    return 10


def _conventional_template(
    base_dir: Path, template_name: str
) -> Path | None:
    for candidate in (
        base_dir / "templates" / f"{template_name}.md",
        base_dir / f"{template_name}.md",
    ):
        if candidate.is_file():
            return candidate
    return None


def resolve_template(template_name: str, repo_root: Path) -> Path | None:
    """Resolve a template name to a file path using the priority stack.

    Order:
      1. .agents/templates/overrides/
      2. .agents/templates/
      3. .specify/templates/overrides/
      4. .specify/templates/
    """
    if not _is_safe_component(template_name):
        return None

    for base in [
        repo_root / ".agents" / "templates",
        repo_root / ".specify" / "templates",
    ]:
        override = base / "overrides" / f"{template_name}.md"
        if override.is_file():
            return override
        core = base / f"{template_name}.md"
        if core.is_file():
            return core

    return None


class TemplateResolutionError(RuntimeError):
    """Raised when template layers exist but cannot be composed safely."""


def _get_bundled_template_content(template_name: str) -> str | None:
    try:
        template_file = resources.files("buddhi.templates.agents.templates") / f"{template_name}.md"
        if template_file.is_file():
            return template_file.read_text(encoding="utf-8")
    except (OSError, UnicodeError, AttributeError, ModuleNotFoundError, TypeError):
        pass
    return None


def resolve_template_content(template_name: str, repo_root: Path) -> str | None:
    """Resolve and compose template content through the project layer stack."""
    if not _is_safe_component(template_name):
        return None

    # 1. Project overrides and templates under .agents/templates/
    agents_templates = repo_root / ".agents" / "templates"
    override = agents_templates / "overrides" / f"{template_name}.md"
    if override.is_file():
        try:
            return override.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise TemplateResolutionError(f"Failed to read {override}: {exc}") from exc

    core = agents_templates / f"{template_name}.md"
    if core.is_file():
        try:
            return core.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise TemplateResolutionError(f"Failed to read {core}: {exc}") from exc

    # 2. Legacy .specify/templates/
    specify_templates = repo_root / ".specify" / "templates"
    specify_override = specify_templates / "overrides" / f"{template_name}.md"
    if specify_override.is_file():
        try:
            return specify_override.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise TemplateResolutionError(f"Failed to read {specify_override}: {exc}") from exc

    specify_core = specify_templates / f"{template_name}.md"
    if specify_core.is_file():
        try:
            return specify_core.read_bytes().decode("utf-8")
        except (OSError, UnicodeError) as exc:
            raise TemplateResolutionError(f"Failed to read {specify_core}: {exc}") from exc

    # 3. Built-in bundled template fallback
    bundled = _get_bundled_template_content(template_name)
    if bundled is not None:
        return bundled

    return None


def format_speckit_command(command_name: str, repo_root: Path | None = None) -> str:
    name = command_name.lstrip("/")
    if name.startswith("speckit."):
        name = name[len("speckit.") :]
    elif name.startswith("speckit-"):
        name = name[len("speckit-") :]
    elif name.startswith("sdd-"):
        name = name[len("sdd-") :]
    return f"/{name}"
