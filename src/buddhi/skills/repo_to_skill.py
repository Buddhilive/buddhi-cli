from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def is_git_url(target: str) -> bool:
    """Check if target string looks like a git remote repository URL."""
    return target.startswith(("https://", "http://", "git@")) or target.endswith(".git")


def clone_repo(url: str, dest_dir: Path) -> bool:
    """Perform shallow clone of remote repository."""
    try:
        cmd = ["git", "clone", "--depth", "1", url, str(dest_dir)]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return proc.returncode == 0
    except (OSError, subprocess.SubprocessError) as exc:
        err_console.print(f"[red]error:[/red] failed to execute git clone: {exc}")
        return False


def detect_languages_and_type(root: Path) -> dict[str, Any]:
    """Detect project languages, manifests, and classification."""
    languages: list[str] = []
    manifests: list[str] = []
    is_cli = False

    if (root / "pyproject.toml").is_file() or (root / "setup.py").is_file():
        languages.append("python")
        manifests.append("pyproject.toml" if (root / "pyproject.toml").is_file() else "setup.py")
        if (root / "pyproject.toml").is_file():
            content = (root / "pyproject.toml").read_text(encoding="utf-8", errors="replace")
            if "project.scripts" in content or "tool.poetry.scripts" in content:
                is_cli = True

    if (root / "package.json").is_file():
        languages.append("javascript/typescript")
        manifests.append("package.json")
        try:
            pkg_data = json.loads((root / "package.json").read_text(encoding="utf-8", errors="replace"))
            if "bin" in pkg_data:
                is_cli = True
        except (json.JSONDecodeError, OSError):
            pass

    if (root / "Cargo.toml").is_file():
        languages.append("rust")
        manifests.append("Cargo.toml")
        content = (root / "Cargo.toml").read_text(encoding="utf-8", errors="replace")
        if "[[bin]]" in content or "clap" in content:
            is_cli = True

    if (root / "go.mod").is_file():
        languages.append("go")
        manifests.append("go.mod")

    # Check common CLI entry files
    for candidate in ("cli.py", "main.py", "index.ts", "main.go", "src/main.rs"):
        if (root / candidate).is_file():
            try:
                txt = (root / candidate).read_text(encoding="utf-8", errors="replace")
                if any(k in txt for k in ("argparse", "click", "typer", "commander", "yargs", "cobra")):
                    is_cli = True
            except OSError:
                pass

    project_type = "CLI Tool" if is_cli else ("Library / Package" if manifests else "General Codebase")

    return {
        "languages": languages or ["unknown"],
        "manifests": manifests,
        "is_cli": is_cli,
        "project_type": project_type,
    }


def extract_readme_summary(root: Path) -> dict[str, Any]:
    """Extract summary, installation instructions, and code blocks from README."""
    readme_path = None
    for name in ("README.md", "README.rst", "README.txt", "readme.md"):
        cand = root / name
        if cand.is_file():
            readme_path = cand
            break

    if not readme_path:
        return {"has_readme": False, "title": root.name, "description": "", "commands": []}

    try:
        content = readme_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {"has_readme": False, "title": root.name, "description": "", "commands": []}


    # Extract title
    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else root.name

    # Extract first non-header paragraph
    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.strip().startswith("#")]
    description = paragraphs[0] if paragraphs else ""

    # Extract command snippets from bash/shell blocks
    code_blocks = re.findall(r"```(?:bash|shell|sh|console)?\s*\n(.*?)\n```", content, re.DOTALL)
    commands: list[str] = []
    for block in code_blocks:
        for line in block.splitlines():
            line = line.strip().lstrip("$").strip()
            if line and not line.startswith("#") and len(line) < 120:
                commands.append(line)
                if len(commands) >= 5:
                    break
        if len(commands) >= 5:
            break

    return {
        "has_readme": True,
        "title": title,
        "description": description[:300],
        "commands": commands,
    }


def analyze_repository(target_path: Path) -> dict[str, Any]:
    """Inspect local repository directory and return structured analysis."""
    type_info = detect_languages_and_type(target_path)
    readme_info = extract_readme_summary(target_path)

    has_docs = (target_path / "docs").is_dir() or (target_path / "documentation").is_dir()
    has_examples = (target_path / "examples").is_dir()

    return {
        "name": target_path.name,
        "project_type": type_info["project_type"],
        "is_cli": type_info["is_cli"],
        "languages": type_info["languages"],
        "manifests": type_info["manifests"],
        "title": readme_info["title"],
        "description": readme_info["description"],
        "suggested_commands": readme_info["commands"],
        "has_docs": has_docs,
        "has_examples": has_examples,
    }


def run_repo_to_skill(target: str, json_mode: bool = False) -> int:
    """Analyze a repository target (path or URL) and print findings."""
    temp_dir: Path | None = None
    try:
        if is_git_url(target):
            temp_dir = Path(tempfile.mkdtemp(prefix="buddhi_repo_"))
            console.print(f"[cyan]Cloning remote repository:[cyan] {target} ...")
            if not clone_repo(target, temp_dir):
                err_console.print(f"[red]error:[/red] failed to clone {target}")
                return 1
            analysis_path = temp_dir
        else:
            analysis_path = Path(target).resolve()
            if not analysis_path.exists():
                err_console.print(f"[red]error:[/red] path does not exist: {analysis_path}")
                return 1
            if not analysis_path.is_dir():
                err_console.print(f"[red]error:[/red] target must be a directory: {analysis_path}")
                return 1

        analysis = analyze_repository(analysis_path)

        if json_mode:
            print(json.dumps(analysis, indent=2))
            return 0

        # Rich formatted human readable output
        table = Table(title="Repository Analysis", show_header=True, header_style="bold cyan")
        table.add_column("Property", style="bold green")
        table.add_column("Details", style="white")

        table.add_row("Project Name", analysis["name"])
        table.add_row("Classification", analysis["project_type"])
        table.add_row("Languages", ", ".join(analysis["languages"]))
        table.add_row("Manifests", ", ".join(analysis["manifests"]) or "None detected")
        table.add_row("Documentation", "Yes (docs/)" if analysis["has_docs"] else "README only")
        table.add_row("Examples", "Yes (examples/)" if analysis["has_examples"] else "None")

        console.print(table)

        if analysis["suggested_commands"]:
            cmd_table = Table(title="Extracted Usage Commands", show_header=False)
            cmd_table.add_column("Command", style="yellow")
            for c in analysis["suggested_commands"]:
                cmd_table.add_row(c)
            console.print(cmd_table)

        console.print(
            Panel(
                f"[bold cyan]Antigravity Skill Strategy:[/bold cyan]\n"
                f"Scaffold as [bold]{analysis['project_type']}[/bold]. "
                f"Include detected CLI flags / public APIs in `references/api-reference.md` "
                f"and common commands in `SKILL.md`.",
                title="Next Steps",
                border_style="green",
            )
        )

        return 0

    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
