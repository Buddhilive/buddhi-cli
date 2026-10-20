"""Configuration, environment variable parsing, and directory resolution for AutoHarness."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Environment variable keys
ENV_DISABLE_GLOBAL = "AUTOHARNESS_DISABLE_GLOBAL"
ENV_REFLECT_EVERY_N = "AUTOHARNESS_REFLECT_EVERY_N"
ENV_CONSOLIDATE_EVERY_N = "AUTOHARNESS_CONSOLIDATE_EVERY_N"
ENV_SKILL_BODY_MAX_LINES = "AUTOHARNESS_SKILL_BODY_MAX_LINES"
ENV_SKILL_DESC_MAX_CHARS = "AUTOHARNESS_SKILL_DESC_MAX_CHARS"
ENV_INDEX_DESC_MAX_CHARS = "AUTOHARNESS_INDEX_DESC_MAX_CHARS"
ENV_SNAPSHOT_KEEP = "AUTOHARNESS_SNAPSHOT_KEEP"
ENV_CHILD_SESSION = "AUTOHARNESS_CHILD_SESSION"
ENV_RUN_ID = "AUTOHARNESS_RUN_ID"
ENV_PROJECT_ROOT = "AUTOHARNESS_PROJECT_ROOT"
ENV_GLOBAL_ROOT = "AUTOHARNESS_GLOBAL_ROOT"

# Defaults
DEFAULT_REFLECT_EVERY_N = 50
DEFAULT_CONSOLIDATE_EVERY_N = 250
DEFAULT_SKILL_BODY_MAX_LINES = 25
DEFAULT_SKILL_DESC_MAX_CHARS = 1024
DEFAULT_INDEX_DESC_MAX_CHARS = 60
DEFAULT_SNAPSHOT_KEEP = 5

STAGE_MAX_BODY_BYTES = 100_000
STAGE_MAX_FILES = 8
STAGE_MAX_FILE_BYTES = 64_000
STAGE_MAX_FILES_TOTAL_BYTES = 256_000

MATURITY_THRESHOLD = {"project": 100, "global": 300}
CAPACITY = {"project": 50, "global": 20}


def get_disable_global() -> bool:
    return os.environ.get(ENV_DISABLE_GLOBAL, "0").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def get_reflect_every_n() -> int:
    try:
        return int(os.environ.get(ENV_REFLECT_EVERY_N, str(DEFAULT_REFLECT_EVERY_N)))
    except ValueError:
        return DEFAULT_REFLECT_EVERY_N


def get_consolidate_every_n() -> int:
    try:
        return int(
            os.environ.get(ENV_CONSOLIDATE_EVERY_N, str(DEFAULT_CONSOLIDATE_EVERY_N))
        )
    except ValueError:
        return DEFAULT_CONSOLIDATE_EVERY_N


def get_skill_body_max_lines() -> int:
    try:
        return int(
            os.environ.get(ENV_SKILL_BODY_MAX_LINES, str(DEFAULT_SKILL_BODY_MAX_LINES))
        )
    except ValueError:
        return DEFAULT_SKILL_BODY_MAX_LINES


def get_snapshot_keep() -> int:
    try:
        return int(os.environ.get(ENV_SNAPSHOT_KEEP, str(DEFAULT_SNAPSHOT_KEEP)))
    except ValueError:
        return DEFAULT_SNAPSHOT_KEEP


def resolve_project_root(cwd: Path | None = None) -> Path:
    """Resolve project repository root, supporting linked git worktrees."""
    if ENV_PROJECT_ROOT in os.environ:
        override = Path(os.environ[ENV_PROJECT_ROOT]).resolve()
        if override.exists():
            return override

    start = (cwd or Path.cwd()).resolve()

    # Walk up to find git root
    curr = start
    while curr != curr.parent:
        git_target = curr / ".git"
        if git_target.is_file():
            # Linked git worktree pointer: 'gitdir: /path/to/.git/worktrees/<name>'
            try:
                line = git_target.read_text(encoding="utf-8").strip()
                if line.startswith("gitdir:"):
                    # Check git-common-dir via rev-parse if possible
                    try:
                        res = subprocess.run(
                            ["git", "rev-parse", "--show-toplevel"],
                            cwd=curr,
                            capture_output=True,
                            text=True,
                            check=False,
                            timeout=2,
                        )
                        if res.returncode == 0 and res.stdout.strip():
                            return Path(res.stdout.strip()).resolve()
                    except (subprocess.SubprocessError, OSError):
                        pass
                    return curr
            except OSError:
                pass
            return curr
        if (
            git_target.is_dir()
            or (curr / ".agents").is_dir()
            or (curr / ".buddhi").is_dir()
        ):
            return curr
        curr = curr.parent

    return start


def resolve_global_root() -> Path:
    """Resolve machine-global Antigravity configuration directory."""
    if ENV_GLOBAL_ROOT in os.environ:
        return Path(os.environ[ENV_GLOBAL_ROOT]).resolve()
    return (Path.home() / ".gemini" / "config").resolve()
