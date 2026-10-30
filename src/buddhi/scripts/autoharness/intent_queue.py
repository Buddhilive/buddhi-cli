"""File-locked JSONL intent queue management for intents/<run_id>.jsonl."""

from __future__ import annotations

import json
from pathlib import Path

from buddhi.scripts.autoharness.layer import resolve_autoharness_dir
from buddhi.scripts.autoharness.lock import file_lock
from buddhi.scripts.autoharness.models import SkillIntent

INTENTS_DIRNAME = "intents"


def get_queue_file(layer: str, run_id: str, project_root: Path | None = None) -> Path:
    autoharness_dir = resolve_autoharness_dir(layer, project_root)
    return autoharness_dir / INTENTS_DIRNAME / f"{run_id}.jsonl"


def append_intent(
    intent: SkillIntent, run_id: str = "interactive", project_root: Path | None = None
) -> None:
    """Append a SkillIntent to the target queue under file lock."""
    q_file = get_queue_file(intent.layer, run_id, project_root)
    q_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file = q_file.parent / f"{run_id}.lock"

    payload = {
        "action": intent.action,
        "name": intent.name,
        "layer": intent.layer,
        "body": intent.body,
        "old_string": intent.old_string,
        "new_string": intent.new_string,
        "files": intent.files,
        "reason": intent.reason,
        "evidence": intent.evidence,
        "absorbed_into": intent.absorbed_into,
    }
    line = json.dumps(payload) + "\n"

    with file_lock(lock_file), open(q_file, "a", encoding="utf-8") as f:
        f.write(line)
        f.flush()


def read_intents(
    layer: str, run_id: str = "interactive", project_root: Path | None = None
) -> list[SkillIntent]:
    """Read all queued intents for run_id."""
    q_file = get_queue_file(layer, run_id, project_root)
    if not q_file.is_file():
        return []

    intents: list[SkillIntent] = []
    try:
        with open(q_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    data = json.loads(line)
                    intents.append(
                        SkillIntent(
                            action=data["action"],
                            name=data["name"],
                            layer=data.get("layer", layer),
                            body=data.get("body"),
                            old_string=data.get("old_string"),
                            new_string=data.get("new_string"),
                            files=data.get("files", {}),
                            reason=data.get("reason", ""),
                            evidence=data.get("evidence", ""),
                            absorbed_into=data.get("absorbed_into"),
                        )
                    )
    except (OSError, json.JSONDecodeError):
        pass
    return intents


def clear_queue(
    layer: str, run_id: str = "interactive", project_root: Path | None = None
) -> None:
    """Safely clear/delete the intent queue file under lock."""
    q_file = get_queue_file(layer, run_id, project_root)
    lock_file = q_file.parent / f"{run_id}.lock"
    with file_lock(lock_file):
        if q_file.is_file():
            q_file.unlink()
