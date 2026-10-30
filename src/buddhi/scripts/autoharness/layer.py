"""Layer resolution, path validation, and Windows reserved name sanitization."""

from __future__ import annotations

import re
from pathlib import Path

from buddhi.scripts.autoharness.config import (
    get_disable_global,
    resolve_global_root,
    resolve_project_root,
)

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    "com1",
    "com2",
    "com3",
    "com4",
    "com5",
    "com6",
    "com7",
    "com8",
    "com9",
    "lpt1",
    "lpt2",
    "lpt3",
    "lpt4",
    "lpt5",
    "lpt6",
    "lpt7",
    "lpt8",
    "lpt9",
}
_ALLOWED_SUBFILE_DIRS = {"references", "templates", "scripts", "assets"}


def check_new_name(name: str) -> None:
    """Validate a skill or directory name against naming and safety conventions."""
    if not name or len(name) < 2 or len(name) > 64:
        raise ValueError(f"Skill name '{name}' must be between 2 and 64 characters.")

    if not _NAME_RE.match(name):
        raise ValueError(
            f"Skill name '{name}' must be lowercase alphanumeric with hyphens (e.g. 'pytest-matcher')."
        )

    stem = name.split(".")[0].lower()
    if stem in _WINDOWS_RESERVED:
        raise ValueError(
            f"Skill name '{name}' collides with Windows reserved device name '{stem}'."
        )


def check_subfile_path(rel_path: str) -> None:
    """Validate a subfile relative path within a skill directory."""
    if not rel_path or rel_path.startswith(("/", "\\")):
        raise ValueError(f"Subfile path '{rel_path}' must be relative.")

    norm = rel_path.replace("\\", "/")
    parts = norm.split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError(
            f"Subfile path '{rel_path}' contains invalid traversal components."
        )

    top_dir = parts[0]
    if top_dir not in _ALLOWED_SUBFILE_DIRS:
        allowed = ", ".join(sorted(_ALLOWED_SUBFILE_DIRS))
        raise ValueError(
            f"Subfile '{rel_path}' must reside under an allowed directory ({allowed}/)."
        )

    for part in parts:
        stem = part.split(".")[0].lower()
        if stem in _WINDOWS_RESERVED:
            raise ValueError(
                f"Subfile '{rel_path}' contains Windows reserved component '{stem}'."
            )


def resolve_layer_root(layer: str, project_root: Path | None = None) -> Path:
    """Resolve target layer root (.agents for project, ~/.gemini/config for global)."""
    if layer == "global":
        if get_disable_global():
            raise ValueError(
                "Global layer is disabled via AUTOHARNESS_DISABLE_GLOBAL=1."
            )
        return resolve_global_root()
    if layer == "project":
        root = project_root or resolve_project_root()
        return root / ".agents"
    raise ValueError(f"Unknown layer '{layer}'. Must be 'project' or 'global'.")


def resolve_skills_dir(layer: str, project_root: Path | None = None) -> Path:
    """Resolve the skills/ directory for the specified layer."""
    return resolve_layer_root(layer, project_root) / "skills"


def resolve_autoharness_dir(layer: str, project_root: Path | None = None) -> Path:
    """Resolve the autoharness/ state directory for the specified layer."""
    return resolve_layer_root(layer, project_root) / "autoharness"
