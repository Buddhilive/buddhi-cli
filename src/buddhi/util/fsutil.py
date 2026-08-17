"""`.buddhi/` filesystem bootstrap: directories + the graphs/ .gitignore."""

from __future__ import annotations

from pathlib import Path

BUDDHI_DIR_NAME = ".buddhi"
GRAPHS_DIR_NAME = "graphs"
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
