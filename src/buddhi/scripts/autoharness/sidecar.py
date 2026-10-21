"""Sidecar JSON (.sidecar.json) management and ownership barriers."""

from __future__ import annotations

import json
from pathlib import Path

from buddhi.scripts.autoharness.atomic import atomic_write_text
from buddhi.scripts.autoharness.lock import file_lock
from buddhi.scripts.autoharness.models import SidecarData

SIDECAR_FILENAME = ".sidecar.json"


def read_sidecar(skill_dir: Path) -> SidecarData | None:
    """Read .sidecar.json from skill_dir. Returns None if absent or malformed."""
    sidecar_path = skill_dir / SIDECAR_FILENAME
    if not sidecar_path.is_file():
        return None
    try:
        raw = sidecar_path.read_text(encoding="utf-8")
        data = json.loads(raw)
        return SidecarData(
            created_by=data.get("created_by", "human"),
            use=int(data.get("use", data.get("calls", 0))),
            view=int(data.get("view", 0)),
            patch=int(data.get("patch", 0)),
            reused_gen=int(data.get("reused_gen", 0)),
            anchor=int(data.get("anchor", 0)),
            verification=data.get("verification", {}),
        )
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def write_sidecar(skill_dir: Path, data: SidecarData) -> None:
    """Write SidecarData to .sidecar.json atomically."""
    sidecar_path = skill_dir / SIDECAR_FILENAME
    payload = {
        "created_by": data.created_by,
        "use": data.use,
        "view": data.view,
        "patch": data.patch,
        "reused_gen": data.reused_gen,
        "anchor": data.anchor,
        "verification": data.verification,
    }
    atomic_write_text(sidecar_path, json.dumps(payload, indent=2))


def is_agent_created(skill_dir: Path) -> bool:
    """Check if skill_dir contains .sidecar.json with created_by: 'agent'."""
    sidecar = read_sidecar(skill_dir)
    return sidecar is not None and sidecar.created_by == "agent"


def bump_sidecar_counter(skill_dir: Path, counter_name: str, delta: int = 1) -> None:
    """Atomically increment a counter in .sidecar.json under file lock."""
    lock_path = skill_dir / f"{SIDECAR_FILENAME}.lock"
    with file_lock(lock_path):
        sidecar = read_sidecar(skill_dir)
        if sidecar is None:
            return
        if counter_name == "use":
            sidecar.use += delta
        elif counter_name == "view":
            sidecar.view += delta
        elif counter_name == "patch":
            sidecar.patch += delta
        elif counter_name == "reused_gen":
            sidecar.reused_gen += delta
        write_sidecar(skill_dir, sidecar)
