"""Token tracking and analytics ledger for RTK.

Records compressed vs raw token counts in `.buddhi/rtk/runs.jsonl` with strict argument
redaction to prevent secret/credential leakage.
"""

from __future__ import annotations

import json
import logging
import os
import shlex
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_LEDGER_PATH = Path(".buddhi/rtk/runs.jsonl")

SAFE_SUBCOMMANDS = {
    "git": {
        "status",
        "diff",
        "log",
        "branch",
        "show",
        "commit",
        "push",
        "pull",
        "fetch",
        "checkout",
    },
    "uv": {"sync", "lock", "pip", "run", "add", "remove"},
    "npm": {"test", "run", "build", "install"},
    "pnpm": {"test", "run", "build", "install"},
    "yarn": {"test", "run", "build", "install"},
    "cargo": {"build", "test", "check", "clippy", "run"},
    "docker": {"build", "run", "ps", "images"},
    "ruff": {"check", "format"},
}


@dataclass
class RunRecord:
    timestamp: int
    command: str
    filter_name: str
    raw_tokens: int
    filtered_tokens: int
    saved_tokens: int
    exit_code: int


@dataclass
class SavingsSummary:
    total_runs: int
    total_raw_tokens: int
    total_filtered_tokens: int
    total_saved_tokens: int
    savings_percentage: float
    by_command: dict[str, dict[str, Any]]


def redact_command_line(command: str) -> str:
    """Retain command binary and safe subcommands while redacting parameters and secrets."""
    stripped = command.strip()
    try:
        parts = shlex.split(stripped, posix=False)
    except Exception:  # noqa: BLE001
        parts = stripped.split()

    if not parts:
        return ""

    prog = os.path.basename(parts[0]).lower()
    if prog.endswith((".exe", ".cmd", ".bat")):
        prog = prog.rsplit(".", 1)[0]

    safe_parts: list[str] = [parts[0]]

    if len(parts) > 1:
        sub = parts[1].lower()
        if prog in SAFE_SUBCOMMANDS and sub in SAFE_SUBCOMMANDS[prog]:
            safe_parts.append(parts[1])
            if len(parts) > 2:
                safe_parts.append("[args redacted]")
        else:
            safe_parts.append("[args redacted]")

    return " ".join(safe_parts)


def record_run(record: RunRecord, ledger_path: Path = DEFAULT_LEDGER_PATH) -> None:
    """Append a run record to the local JSON-lines ledger."""
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        data = asdict(record)
        line = json.dumps(data) + "\n"
        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as err:  # noqa: BLE001
        logger.warning("Failed to record RTK run in %s: %s", ledger_path, err)


def aggregate_savings(ledger_path: Path = DEFAULT_LEDGER_PATH) -> SavingsSummary:
    """Aggregate token savings statistics from the ledger."""
    total_runs = 0
    total_raw = 0
    total_filtered = 0
    total_saved = 0
    by_command: dict[str, dict[str, Any]] = {}

    if ledger_path.is_file():
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    raw_tok = entry.get("raw_tokens", 0)
                    filt_tok = entry.get("filtered_tokens", 0)
                    saved_tok = entry.get("saved_tokens", raw_tok - filt_tok)
                    cmd = entry.get("command", "other")
                    filter_name = entry.get("filter_name", "unknown")

                    total_runs += 1
                    total_raw += raw_tok
                    total_filtered += filt_tok
                    total_saved += max(0, saved_tok)

                    cat = f"{cmd} ({filter_name})"
                    if cat not in by_command:
                        by_command[cat] = {
                            "runs": 0,
                            "raw": 0,
                            "filtered": 0,
                            "saved": 0,
                        }

                    by_command[cat]["runs"] += 1
                    by_command[cat]["raw"] += raw_tok
                    by_command[cat]["filtered"] += filt_tok
                    by_command[cat]["saved"] += max(0, saved_tok)

        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to read ledger from %s: %s", ledger_path, err)

    percentage = (total_saved / total_raw * 100.0) if total_raw > 0 else 0.0

    return SavingsSummary(
        total_runs=total_runs,
        total_raw_tokens=total_raw,
        total_filtered_tokens=total_filtered,
        total_saved_tokens=total_saved,
        savings_percentage=round(percentage, 1),
        by_command=by_command,
    )
