"""Append-only audit log (.ledger.jsonl) reader and writer."""

from __future__ import annotations

import json
import time
from pathlib import Path

from buddhi.scripts.autoharness.lock import file_lock

LEDGER_FILENAME = ".ledger.jsonl"


def append_ledger(
    skill_dir: Path,
    action: str,
    reason: str,
    evidence_path: str,
    absorbed_into: str | None = None,
) -> None:
    """Append a timestamped mutation entry to .ledger.jsonl under file lock."""
    ledger_path = skill_dir / LEDGER_FILENAME
    lock_path = skill_dir / f"{LEDGER_FILENAME}.lock"

    entry: dict[str, str | int | float | None] = {
        "timestamp": time.time(),
        "iso_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "action": action,
        "reason": reason,
        "evidence": evidence_path,
        "absorbed_into": absorbed_into,
    }
    raw = json.dumps(entry) + "\n"

    with file_lock(lock_path):
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(raw)
            f.flush()


def read_ledger(skill_dir: Path) -> list[dict]:
    """Read all entries from .ledger.jsonl."""
    ledger_path = skill_dir / LEDGER_FILENAME
    if not ledger_path.is_file():
        return []
    entries: list[dict] = []
    try:
        with open(ledger_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
    except (OSError, json.JSONDecodeError):
        pass
    return entries

