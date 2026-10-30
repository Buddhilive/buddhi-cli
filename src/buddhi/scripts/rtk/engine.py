"""Declarative filtering engine for RTK.

Applies strip, keep, replace, match_output, duplicate collapse, head/tail limits, and empty fallback
while guaranteeing that failure/error lines are never dropped. Fail-open on unexpected errors.
"""

from __future__ import annotations

import logging

from buddhi.scripts.rtk.filters import FilterSpec
from buddhi.scripts.rtk.generic import (
    collapse_blank_lines,
    collapse_duplicate_lines,
    strip_ansi,
)

logger = logging.getLogger(__name__)


def apply_filter(
    raw_output: str,
    spec: FilterSpec,
) -> str:
    """Filter raw command output according to a FilterSpec.

    Guarantees:
    - Obeys explicit strip/keep/replace/match_output rules.
    - Preserves error/failure lines.
    - If filtering results in an exception, returns raw_output (fail-open).
    """
    if not raw_output or not raw_output.strip():
        if spec.on_empty:
            return spec.on_empty
        return ""

    try:
        text = raw_output
        if spec.strip_ansi:
            text = strip_ansi(text)

        # Check match_output rules (short-circuit on success / fixed status)
        for rule in spec.match_output:
            if rule.matches(text):
                return rule.message

        # Apply regex replacement rules
        for replace_rule in spec.replace_rules:
            text = replace_rule.apply(text)

        lines = text.splitlines()

        # Filter lines by strip / keep rules
        filtered_lines: list[str] = []
        for line in lines:
            if spec.is_error_line(line) or spec.is_keep_line(line):
                filtered_lines.append(line)
            elif spec.is_strip_line(line):
                continue
            elif spec.keep_lines_matching and not spec.strip_lines_matching:
                # In keep-only mode, non-keep and non-error lines are omitted
                continue
            else:
                filtered_lines.append(line)

        # Truncate lines at max character limit if specified
        if spec.truncate_lines_at is not None and spec.truncate_lines_at > 0:
            limit = spec.truncate_lines_at
            truncated: list[str] = []
            for line in filtered_lines:
                if len(line) > limit:
                    truncated.append(line[:limit] + "...")
                else:
                    truncated.append(line)
            filtered_lines = truncated

        # Collapse blank lines
        filtered_lines = collapse_blank_lines(filtered_lines)

        # Dedup if requested
        if spec.dedup:
            filtered_lines = collapse_duplicate_lines(filtered_lines)

        # Check if output is empty
        if not filtered_lines or all(not l.strip() for l in filtered_lines):
            if spec.on_empty:
                return spec.on_empty
            return ""

        # Check max lines / head / tail truncation
        max_lines = spec.max_lines
        if max_lines is not None and len(filtered_lines) > max_lines:
            head_count = (
                spec.head_lines if spec.head_lines is not None else max_lines // 2
            )
            tail_count = (
                spec.tail_lines if spec.tail_lines is not None else max_lines // 2
            )

            head = filtered_lines[:head_count]
            tail = filtered_lines[-tail_count:] if tail_count > 0 else []

            middle = (
                filtered_lines[head_count:-tail_count]
                if tail_count > 0
                else filtered_lines[head_count:]
            )
            omitted_count = len(middle)

            # Preserve any error lines that fell in the omitted middle
            salvaged_errors: list[str] = []
            for line in middle:
                if spec.is_error_line(line):
                    salvaged_errors.append(line)

            parts: list[str] = list(head)
            notice = f"\n[... {omitted_count} lines omitted ...]\n"
            if salvaged_errors:
                notice += f"[... {len(salvaged_errors)} error/failure line(s) salvaged from omitted section: ...]\n"
                notice += "\n".join(salvaged_errors) + "\n"

            parts.append(notice.strip())
            parts.extend(tail)
            return "\n".join(parts).strip()

        return "\n".join(filtered_lines).strip()

    except Exception as err:  # noqa: BLE001
        logger.warning(
            "Error filtering output with filter %s: %s; falling back to raw output",
            spec.name,
            err,
        )
        return raw_output.strip()
