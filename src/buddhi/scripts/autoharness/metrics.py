"""Read-only telemetry and status metrics aggregator for AutoHarness."""

from __future__ import annotations

import json
from pathlib import Path

from buddhi.scripts.autoharness.layer import resolve_autoharness_dir, resolve_skills_dir
from buddhi.scripts.autoharness.sidecar import is_agent_created, read_sidecar


def collect_metrics(layer: str = "project", project_root: Path | None = None) -> dict:
    """Collect telemetry metrics across active agent-authored skills and runs."""
    skills_dir = resolve_skills_dir(layer, project_root)
    autoharness_dir = resolve_autoharness_dir(layer, project_root)

    total_live = 0
    total_uses = 0
    total_views = 0
    total_patches = 0

    if skills_dir.is_dir():
        for item in skills_dir.iterdir():
            if item.is_dir() and is_agent_created(item):
                sidecar = read_sidecar(item)
                if sidecar:
                    total_live += 1
                    total_uses += sidecar.use
                    total_views += sidecar.view
                    total_patches += sidecar.patch

    archive_dir = skills_dir / ".archive"
    total_archived = len(list(archive_dir.iterdir())) if archive_dir.is_dir() else 0

    last_run_file = autoharness_dir / "last_run.json"
    last_run_data = {}
    if last_run_file.is_file():
        try:
            last_run_data = json.loads(last_run_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass

    return {
        "layer": layer,
        "live_skills": total_live,
        "total_uses": total_uses,
        "total_views": total_views,
        "total_patches": total_patches,
        "archived_skills": total_archived,
        "last_run": last_run_data,
    }

