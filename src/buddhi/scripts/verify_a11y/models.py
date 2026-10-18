from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

ARTIFACTS = ("REPORT.md", "EXCEPTIONS.md", "A11Y-DECISIONS.md")
SOURCE_SUFFIXES = {
    ".html",
    ".htm",
    ".jsx",
    ".tsx",
    ".js",
    ".ts",
    ".vue",
    ".svelte",
    ".css",
    ".scss",
    ".astro",
}
SCRIPT_SUFFIXES = {".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro"}
MARKUP_SUFFIXES = {".html", ".htm", ".vue", ".svelte", ".astro"}
SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".next",
    "out",
    "vendor",
    "__pycache__",
    ".venv",
}

PROFILE_FLOORS = {"shield": 7.0, "standard": 4.5, "launchpad": 4.5}

SOURCE_CHECKS = (
    "clickable-div",
    "placeholder-label",
    "half-climbed-aria",
    "aria-soup",
    "nullified-alt",
    "orphaned-aria",
    "overlay",
    "positive-tabindex",
    "outline-none",
    "redundant-alert",
    "media-autoplay",
)
CHOICE_CHECKS = ("aria-soup", "redundant-alert", "outline-none", "orphaned-aria")


@dataclass
class GateFinding:
    level: str  # "ERROR", "WARN", "REGISTERED"
    check: str
    message: str
    subject: str = ""


@dataclass
class VerifyA11yResult:
    exit_code: int
    summary_line: str
    errors: list[GateFinding] = field(default_factory=list)
    warnings: list[GateFinding] = field(default_factory=list)
    registered: list[GateFinding] = field(default_factory=list)
    findings: list[GateFinding] = field(default_factory=list)
    output_text: str = ""


@dataclass
class ResolvedArtifacts:
    report_path: Path | None
    exceptions_path: Path | None
    decisions_path: Path | None

