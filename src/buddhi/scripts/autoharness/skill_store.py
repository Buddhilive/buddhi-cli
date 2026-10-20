"""Skill directory CRUD operations, delta patching, atomic landing, and archival."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from buddhi.scripts.autoharness.atomic import atomic_write_text

SKILL_MAIN_FILE = "SKILL.md"
ARCHIVE_DIRNAME = ".archive"


def get_skill_path(skills_dir: Path, name: str) -> Path:
    return skills_dir / name


def exists(skills_dir: Path, name: str) -> bool:
    return (skills_dir / name).is_dir()


def read_body(skills_dir: Path, name: str) -> str | None:
    skill_file = skills_dir / name / SKILL_MAIN_FILE
    if not skill_file.is_file():
        return None
    try:
        return skill_file.read_text(encoding="utf-8")
    except OSError:
        return None


def apply_delta(current_body: str, old_string: str, new_string: str) -> str:
    """Apply exact string replacement to current_body, ensuring unique match."""
    count = current_body.count(old_string)
    if count == 0:
        raise ValueError(
            f"Target old_string '{old_string[:50]}...' not found in SKILL.md."
        )
    if count > 1:
        raise ValueError(
            f"Target old_string matches {count} occurrences in SKILL.md; must be unique."
        )
    return current_body.replace(old_string, new_string, 1)


def write_body(skills_dir: Path, name: str, body: str) -> None:
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_text(skill_dir / SKILL_MAIN_FILE, body)


def write_subfile(skill_dir: Path, rel_path: str, content: str) -> None:
    target = skill_dir / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(target, content)


def remove_subfile(skill_dir: Path, rel_path: str) -> None:
    target = skill_dir / rel_path
    if target.is_file():
        target.unlink()


def archive_skill(skills_dir: Path, name: str) -> Path:
    """Move skill directory to .archive/<timestamp>-<name>/."""
    src = skills_dir / name
    if not src.is_dir():
        raise FileNotFoundError(f"Skill '{name}' does not exist.")

    archive_root = skills_dir / ARCHIVE_DIRNAME
    archive_root.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    dest = archive_root / f"{timestamp}-{name}"
    counter = 1
    while dest.exists():
        dest = archive_root / f"{timestamp}-{name}-{counter}"
        counter += 1

    shutil.move(str(src), str(dest))
    return dest


def sweep_orphans(skills_dir: Path) -> int:
    """Clean up orphan .tmp files left over from aborted writes."""
    swept = 0
    if not skills_dir.is_dir():
        return 0
    for root, _, files in os.walk(skills_dir):
        for f in files:
            if f.endswith(".tmp") or (f.startswith(".") and ".tmp" in f):
                try:
                    os.remove(os.path.join(root, f))
                    swept += 1
                except OSError:
                    pass
    return swept
