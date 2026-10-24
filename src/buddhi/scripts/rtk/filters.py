"""JSON filter schema, loading, validation, and registry for RTK.

Portions adapted from rtk-ai/rtk (Apache-2.0).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BUILTIN_FILTERS_DIR = Path(__file__).parent / "builtin_filters"
DEFAULT_ERROR_PATTERNS = [
    r"(?i)\b(fatal|panic|exception|traceback|syntaxerror)\b",
    r"(?i)(?:^|:\s*)error:\s*",
    r"(?i)\berror:\s+",
    r"(?i)^ERROR\b",
    r"(?i)\bAssertionError\b",
    r"(?i)FAILED\s+.*::",
    r"^\s*File\s+\".*\",\s+line\s+\d+",
    r"^E\s{3,}.*",
    r"^>\s{3,}.*",
]


@dataclass
class ReplaceRule:
    pattern: str
    replacement: str
    _compiled: re.Pattern[str] | None = field(default=None, repr=False)

    def apply(self, text: str) -> str:
        if self._compiled is None:
            self._compiled = re.compile(self.pattern)
        return self._compiled.sub(self.replacement, text)


@dataclass
class MatchOutputRule:
    pattern: str
    message: str
    unless: str | None = None
    _compiled_pat: re.Pattern[str] | None = field(default=None, repr=False)
    _compiled_unless: re.Pattern[str] | None = field(default=None, repr=False)

    def matches(self, text: str) -> bool:
        if self._compiled_pat is None:
            self._compiled_pat = re.compile(self.pattern)
        if self.unless and self._compiled_unless is None:
            self._compiled_unless = re.compile(self.unless)

        if self._compiled_unless and self._compiled_unless.search(text):
            return False
        return bool(self._compiled_pat.search(text))


@dataclass
class FilterTestCase:
    name: str
    input: str
    expected: str


@dataclass
class FilterSpec:
    name: str
    description: str = ""
    match_command: str = ""
    strip_ansi: bool = True
    strip_lines_matching: list[str] = field(default_factory=list)
    keep_lines_matching: list[str] = field(default_factory=list)
    error_patterns: list[str] = field(
        default_factory=lambda: list(DEFAULT_ERROR_PATTERNS)
    )
    replace_rules: list[ReplaceRule] = field(default_factory=list)
    match_output: list[MatchOutputRule] = field(default_factory=list)
    max_lines: int | None = None
    head_lines: int | None = None
    tail_lines: int | None = None
    truncate_lines_at: int | None = None
    dedup: bool = False
    on_empty: str | None = None
    tests: list[FilterTestCase] = field(default_factory=list)
    source: str = ""
    license: str = "Apache-2.0"
    modified: bool = True

    _compiled_match: re.Pattern[str] | None = field(default=None, repr=False)
    _compiled_strip: list[re.Pattern[str]] = field(default_factory=list, repr=False)
    _compiled_keep: list[re.Pattern[str]] = field(default_factory=list, repr=False)
    _compiled_errors: list[re.Pattern[str]] = field(default_factory=list, repr=False)

    def __post_init__(self) -> None:
        if self.match_command:
            try:
                self._compiled_match = re.compile(self.match_command)
            except re.error as err:
                logger.warning(
                    "Invalid match_command regex %r in filter %s: %s",
                    self.match_command,
                    self.name,
                    err,
                )

        self._compiled_strip = []
        for pat in self.strip_lines_matching:
            try:
                self._compiled_strip.append(re.compile(pat))
            except re.error as err:
                logger.warning(
                    "Invalid strip regex %r in filter %s: %s", pat, self.name, err
                )

        self._compiled_keep = []
        for pat in self.keep_lines_matching:
            try:
                self._compiled_keep.append(re.compile(pat))
            except re.error as err:
                logger.warning(
                    "Invalid keep regex %r in filter %s: %s", pat, self.name, err
                )

        self._compiled_errors = []
        for pat in self.error_patterns:
            try:
                self._compiled_errors.append(re.compile(pat))
            except re.error as err:
                logger.warning(
                    "Invalid error regex %r in filter %s: %s", pat, self.name, err
                )

    def matches(self, command: str) -> bool:
        """Check if command line matches this filter."""
        if not self._compiled_match:
            return False
        return bool(self._compiled_match.search(command.strip()))

    def is_error_line(self, line: str) -> bool:
        """Return True if line matches any failure/error signature."""
        for pattern in self._compiled_errors:
            if pattern.search(line):
                return True
        return False

    def is_keep_line(self, line: str) -> bool:
        """Return True if line matches an explicit keep rule."""
        for pattern in self._compiled_keep:
            if pattern.search(line):
                return True
        return False

    def is_strip_line(self, line: str) -> bool:
        """Return True if line matches any strip pattern and is NOT an explicit keep line."""
        if self.is_keep_line(line):
            return False
        for pattern in self._compiled_strip:
            if pattern.search(line):
                return True
        return False

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "name": self.name,
            "description": self.description,
            "match_command": self.match_command,
            "strip_ansi": self.strip_ansi,
            "strip_lines_matching": self.strip_lines_matching,
            "keep_lines_matching": self.keep_lines_matching,
            "error_patterns": self.error_patterns,
            "replace": [
                {"pattern": r.pattern, "replacement": r.replacement}
                for r in self.replace_rules
            ],
            "match_output": [
                {"pattern": m.pattern, "message": m.message, "unless": m.unless}
                for m in self.match_output
            ],
            "max_lines": self.max_lines,
            "head_lines": self.head_lines,
            "tail_lines": self.tail_lines,
            "truncate_lines_at": self.truncate_lines_at,
            "dedup": self.dedup,
            "on_empty": self.on_empty,
            "source": self.source,
            "license": self.license,
            "modified": self.modified,
            "tests": [
                {"name": t.name, "input": t.input, "expected": t.expected}
                for t in self.tests
            ],
        }
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FilterSpec:
        replace_raw = data.get("replace", [])
        replace_rules = [
            ReplaceRule(pattern=r["pattern"], replacement=r.get("replacement", ""))
            for r in replace_raw
            if isinstance(r, dict) and "pattern" in r
        ]

        match_output_raw = data.get("match_output", [])
        match_output_rules = [
            MatchOutputRule(
                pattern=m["pattern"],
                message=m.get("message", ""),
                unless=m.get("unless"),
            )
            for m in match_output_raw
            if isinstance(m, dict) and "pattern" in m and "message" in m
        ]

        tests_raw = data.get("tests", [])
        tests = [
            FilterTestCase(
                name=t.get("name", ""),
                input=t.get("input", ""),
                expected=t.get("expected", ""),
            )
            for t in tests_raw
            if isinstance(t, dict)
        ]

        error_pats = data.get("error_patterns")
        if error_pats is None:
            error_patterns = list(DEFAULT_ERROR_PATTERNS)
        else:
            error_patterns = list(error_pats)

        return cls(
            name=data.get("name", "unnamed"),
            description=data.get("description", ""),
            match_command=data.get("match_command", ""),
            strip_ansi=data.get("strip_ansi", True),
            strip_lines_matching=list(data.get("strip_lines_matching", [])),
            keep_lines_matching=list(data.get("keep_lines_matching", [])),
            error_patterns=error_patterns,
            replace_rules=replace_rules,
            match_output=match_output_rules,
            max_lines=data.get("max_lines"),
            head_lines=data.get("head_lines"),
            tail_lines=data.get("tail_lines"),
            truncate_lines_at=data.get("truncate_lines_at"),
            dedup=data.get("dedup", False),
            on_empty=data.get("on_empty"),
            tests=tests,
            source=data.get("source", ""),
            license=data.get("license", "Apache-2.0"),
            modified=data.get("modified", True),
        )


def load_filter_from_file(path: Path) -> FilterSpec:
    """Load a FilterSpec from a JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return FilterSpec.from_dict(data)


def load_builtin_filters(filters_dir: Path | None = None) -> list[FilterSpec]:
    """Load all builtin JSON filters from package directory."""
    target_dir = filters_dir or BUILTIN_FILTERS_DIR
    if not target_dir.is_dir():
        return []

    filters: list[FilterSpec] = []
    for p in sorted(target_dir.glob("*.json")):
        try:
            filters.append(load_filter_from_file(p))
        except Exception as err:  # noqa: BLE001
            logger.warning("Failed to load builtin filter from %s: %s", p, err)

    return filters


def find_matching_filter(command: str, filters: list[FilterSpec]) -> FilterSpec | None:
    """Find the first matching filter for a given command."""
    for f in filters:
        if f.matches(command):
            return f
    return None
