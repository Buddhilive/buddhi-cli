"""Subprocess execution runner with streaming capture, exit-code fidelity, and tee-on-failure."""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from buddhi.scripts.rtk.engine import apply_filter
from buddhi.scripts.rtk.filters import (
    FilterSpec,
    find_matching_filter,
    load_builtin_filters,
)
from buddhi.scripts.rtk.generic import apply_generic_filter

logger = logging.getLogger(__name__)

DEFAULT_RAW_DIR = Path(".buddhi/rtk/raw")
MAX_RAW_LOGS = 50


@dataclass
class ExecutionResult:
    exit_code: int
    filtered_output: str
    raw_output: str
    raw_log_path: str | None
    filter_applied: str
    raw_token_est: int
    filtered_token_est: int


def estimate_tokens(text: str) -> int:
    """Fast, dependency-free token estimator (4 characters per token)."""
    return max(1, (len(text) + 3) // 4) if text else 0


def sanitize_filename(name: str) -> str:
    """Convert command name into a safe filesystem string."""
    return re.sub(r"[^\w\-.]+", "_", name).strip("_")[:40]


def save_raw_failure_log(cmd_name: str, raw_content: str, raw_dir: Path) -> Path:
    """Save raw command failure output and prune older logs if needed."""
    raw_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    safe_slug = sanitize_filename(cmd_name)
    log_file = raw_dir / f"{timestamp}_{safe_slug}.log"

    try:
        log_file.write_text(raw_content, encoding="utf-8", errors="replace")
    except Exception as err:  # noqa: BLE001
        logger.warning("Failed to write failure recovery log to %s: %s", log_file, err)

    # Prune old logs to avoid unbounded directory growth
    try:
        existing = sorted(raw_dir.glob("*.log"), key=lambda p: p.stat().st_mtime)
        if len(existing) > MAX_RAW_LOGS:
            for p in existing[:-MAX_RAW_LOGS]:
                try:
                    p.unlink(missing_ok=True)
                except OSError:
                    pass
    except Exception:  # noqa: BLE001, S110
        pass

    return log_file


def run_command_filtered(
    cmd_args: Sequence[str],
    cwd: str | Path | None = None,
    env: dict[str, str] | None = None,
    raw_dir: Path = DEFAULT_RAW_DIR,
    custom_filters: list[FilterSpec] | None = None,
    force_generic: bool = False,
    record_savings: bool = True,
) -> ExecutionResult:
    """Execute a command, capture output, apply matching or generic filter, and preserve exit code."""
    if not cmd_args:
        return ExecutionResult(
            exit_code=0,
            filtered_output="",
            raw_output="",
            raw_log_path=None,
            filter_applied="none",
            raw_token_est=0,
            filtered_token_est=0,
        )

    cmd_line = " ".join(cmd_args)
    cmd_base = Path(cmd_args[0]).name

    # Check for executable resolution on Windows (.cmd / .bat / .exe)
    resolved_cmd = list(cmd_args)
    if shutil.which(resolved_cmd[0]):
        pass

    # Load filters
    available_filters: list[FilterSpec] = []
    if not force_generic:
        if custom_filters:
            available_filters.extend(custom_filters)
        available_filters.extend(load_builtin_filters())

    matched_filter = (
        find_matching_filter(cmd_line, available_filters) if not force_generic else None
    )

    # Run subprocess merging stdout and stderr
    exec_env = os.environ.copy() if env is None else env.copy()
    exec_env["BUDDHI_RTK_ACTIVE"] = "1"

    try:
        proc = subprocess.run(
            resolved_cmd,
            cwd=str(cwd) if cwd else None,
            env=exec_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            check=False,
        )
        raw_output = proc.stdout or ""
        exit_code = proc.returncode
    except FileNotFoundError:
        # Fallback to shell execution for shell-builtins on Windows (e.g. dir, echo) or path resolution
        try:
            proc = subprocess.run(
                cmd_line,
                cwd=str(cwd) if cwd else None,
                env=exec_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=True,
                check=False,
            )
            raw_output = proc.stdout or ""
            exit_code = proc.returncode
        except Exception as e:  # noqa: BLE001
            raw_output = f"Execution error: {e}"
            exit_code = 127
    except Exception as e:  # noqa: BLE001
        raw_output = f"Execution error: {e}"
        exit_code = 1

    # Filter output
    filter_name = "generic"
    if matched_filter is not None:
        filtered_output = apply_filter(raw_output, matched_filter)
        filter_name = matched_filter.name
    else:
        filtered_output = apply_generic_filter(raw_output)

    # Save recovery log on failure
    raw_log_path: str | None = None
    if exit_code != 0:
        saved_path = save_raw_failure_log(cmd_base, raw_output, raw_dir)
        raw_log_path = str(saved_path)

    raw_tokens = estimate_tokens(raw_output)
    filtered_tokens = estimate_tokens(filtered_output)

    if record_savings:
        try:
            from buddhi.scripts.rtk.tracking import (
                RunRecord,
                record_run,
                redact_command_line,
            )

            record = RunRecord(
                timestamp=int(time.time()),
                command=redact_command_line(cmd_line),
                filter_name=filter_name,
                raw_tokens=raw_tokens,
                filtered_tokens=filtered_tokens,
                saved_tokens=max(0, raw_tokens - filtered_tokens),
                exit_code=exit_code,
            )
            record_run(record)
        except Exception:  # noqa: BLE001, S110
            pass

    return ExecutionResult(
        exit_code=exit_code,
        filtered_output=filtered_output,
        raw_output=raw_output,
        raw_log_path=raw_log_path,
        filter_applied=filter_name,
        raw_token_est=raw_tokens,
        filtered_token_est=filtered_tokens,
    )
