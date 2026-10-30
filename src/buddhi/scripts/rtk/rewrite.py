"""Command rewrite classifier and decision logic for RTK.

Determines whether an arbitrary shell command can and should be rewritten to run
through `buddhi scripts rtk run -- <command>`.
"""

from __future__ import annotations

import os
import re
import shlex
from dataclasses import dataclass
from typing import Literal

from buddhi.scripts.rtk.filters import find_matching_filter, load_builtin_filters

ActionType = Literal["rewrite", "skip", "allow"]

COMPOUND_REGEX = re.compile(r"(?:\||&&|\|\||;|>>|>|<|<<|\$\(|\`)")
ALREADY_WRAPPED_REGEX = re.compile(r"^(?:buddhi\s+scripts\s+rtk\s+run|rtk\s+)\b")

DEFAULT_REWRITE_COMMANDS = {
    "git": {"status", "diff", "log", "branch", "show"},
    "pytest": None,  # All subcommands/flags
    "ruff": {"check", "format"},
    "mypy": None,
    "cargo": {"build", "check", "test", "clippy", "run"},
    "npm": {"test", "run", "install", "build"},
    "pnpm": {"test", "run", "install", "build"},
    "yarn": {"test", "run", "install", "build"},
    "docker": {"build", "run", "ps", "images"},
}


@dataclass
class RewriteDecision:
    action: ActionType
    reason: str
    original_command: str
    rewritten_command: str


def is_compound_or_redirect(command: str) -> bool:
    """Check if the command includes pipes, redirections, or sequence operators."""
    return bool(COMPOUND_REGEX.search(command))


def is_already_wrapped(command: str) -> bool:
    """Check if the command is already invoked through rtk."""
    return bool(ALREADY_WRAPPED_REGEX.search(command.strip()))


def is_rewrite_candidate(command: str) -> bool:
    """Check whether a command is a candidate for output filtering."""
    stripped = command.strip()

    # Check prefix wrappers like 'uv run <cmd>' or 'poetry run <cmd>'
    m = re.match(r"^(?:uv\s+run|poetry\s+run)\s+(.*)$", stripped)
    inner = m.group(1).strip() if m else stripped

    try:
        parts = shlex.split(inner, posix=False)
    except Exception:  # noqa: BLE001
        parts = inner.split()

    if not parts:
        return False

    prog = os.path.basename(parts[0]).lower()
    if prog.endswith((".exe", ".cmd", ".bat")):
        prog = prog.rsplit(".", 1)[0]

    # Check against known default rewrite commands
    if prog in DEFAULT_REWRITE_COMMANDS:
        allowed_subs = DEFAULT_REWRITE_COMMANDS[prog]
        if allowed_subs is None:
            return True
        if len(parts) > 1 and parts[1] in allowed_subs:
            return True

    # Check against any active builtin filter
    filters = load_builtin_filters()
    return find_matching_filter(stripped, filters) is not None


def evaluate_rewrite(command: str) -> RewriteDecision:
    """Evaluate whether to rewrite the command for token savings."""
    stripped = command.strip()

    if not stripped:
        return RewriteDecision(
            action="skip",
            reason="empty_command",
            original_command=command,
            rewritten_command=command,
        )

    # Disable switch via env var
    if (
        os.environ.get("BUDDHI_RTK_DISABLE_REWRITE") == "1"
        or os.environ.get("BUDDHI_RTK_ACTIVE") == "1"
    ):
        return RewriteDecision(
            action="skip",
            reason="disabled_by_env",
            original_command=command,
            rewritten_command=command,
        )

    if is_already_wrapped(stripped):
        return RewriteDecision(
            action="skip",
            reason="already_wrapped",
            original_command=command,
            rewritten_command=command,
        )

    if is_compound_or_redirect(stripped):
        return RewriteDecision(
            action="skip",
            reason="compound_or_pipe",
            original_command=command,
            rewritten_command=command,
        )

    if not is_rewrite_candidate(stripped):
        return RewriteDecision(
            action="skip",
            reason="no_rewrite_candidate",
            original_command=command,
            rewritten_command=command,
        )

    rewritten = f"buddhi scripts rtk run -- {stripped}"
    return RewriteDecision(
        action="rewrite",
        reason="token_filter_candidate",
        original_command=command,
        rewritten_command=rewritten,
    )
