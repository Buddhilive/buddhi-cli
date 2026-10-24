"""RTK (Token-saving command output filter) package for buddhi-cli.

Portions adapted from rtk-ai/rtk (Apache-2.0).
"""

from __future__ import annotations

from buddhi.scripts.rtk.engine import apply_filter
from buddhi.scripts.rtk.filters import (
    FilterSpec,
    find_matching_filter,
    load_builtin_filters,
)
from buddhi.scripts.rtk.generic import apply_generic_filter, strip_ansi
from buddhi.scripts.rtk.runner import ExecutionResult, run_command_filtered

__all__ = [
    "ExecutionResult",
    "FilterSpec",
    "apply_filter",
    "apply_generic_filter",
    "find_matching_filter",
    "load_builtin_filters",
    "run_command_filtered",
    "strip_ansi",
]
