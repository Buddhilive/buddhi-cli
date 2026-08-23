"""`.buddhi/` filesystem bootstrap: directories, gitignore, and template scaffolding."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

BUDDHI_DIR_NAME = ".buddhi"
GRAPHS_DIR_NAME = "graphs"
DOCS_DIR_NAME = "docs"
GITIGNORE_CONTENT = "graphs/\n"


class BuddhiFsError(Exception):
    pass


def ensure_buddhi_dirs(root: Path) -> Path:
    """Ensure `.buddhi/` and `.buddhi/graphs/` exist under root; return the graphs dir.

    Never overwrites an existing `.buddhi/.gitignore`.
    """
    buddhi_dir = root / BUDDHI_DIR_NAME
    graphs_dir = buddhi_dir / GRAPHS_DIR_NAME

    try:
        buddhi_dir.mkdir(exist_ok=True)
        gitignore_path = buddhi_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        graphs_dir.mkdir(exist_ok=True)
    except OSError as exc:
        raise BuddhiFsError(f"could not prepare {buddhi_dir}: {exc}") from exc

    return graphs_dir


def ensure_docs_dir(root: Path) -> Path:
    """Ensure `.buddhi/docs/` exists under root; return it."""
    docs_dir = root / BUDDHI_DIR_NAME / DOCS_DIR_NAME
    try:
        docs_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BuddhiFsError(f"could not prepare {docs_dir}: {exc}") from exc
    return docs_dir


@dataclass
class TemplateSyncReport:
    created: list[Path] = field(default_factory=list)
    kept_existing: list[Path] = field(default_factory=list)


def sync_template_tree(src_dir: Path, dest_dir: Path) -> TemplateSyncReport:
    """Copy every file under `src_dir` into `dest_dir`, preserving relative paths.

    Never overwrites a file that already exists at the destination — a file
    once written there may have been hand-edited by the user, and buddhi has
    no way to distinguish "untouched since last init" from "customized", so
    the safe default is to leave any existing file alone and only fill in
    what's missing.
    """
    report = TemplateSyncReport()
    if not src_dir.is_dir():
        raise BuddhiFsError(f"template source missing: {src_dir}")

    for src_path in sorted(src_dir.rglob("*")):
        if src_path.is_dir():
            continue
        if "__pycache__" in src_path.parts:
            continue
        if src_path.suffix in (".pyc", ".pyo"):
            continue
        if src_path.name == "__init__.py":
            # The template tree is itself a Python package (so it can be
            # packaged/imported), but __init__.py exists only for that
            # purpose — it is not harness content and must never be
            # scaffolded into a target project's `.agents/`.
            continue
        rel = src_path.relative_to(src_dir)
        dest_path = dest_dir / rel
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path.exists():
                report.kept_existing.append(dest_path)
                continue
            shutil.copyfile(src_path, dest_path)
            report.created.append(dest_path)
        except OSError as exc:
            raise BuddhiFsError(f"could not write {dest_path}: {exc}") from exc

    return report




