"""Regex secrets & PII redaction engine with Luhn credit-card verification."""

from __future__ import annotations

import re

# Redaction rule patterns
SECRET_PATTERNS = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "github_token",
        re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{36,}|github_pat_[A-Za-z0-9_]{82})\b"),
    ),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    (
        "private_key_block",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
        ),
    ),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9\-._~+/]+=*")),
    (
        "api_key_assignment",
        re.compile(
            r"""(?i)\b(?:api_key|apikey|secret_key|client_secret)\s*[:=]\s*['"][A-Za-z0-9_\-]{16,}['"]"""
        ),
    ),
]

PII_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    (
        "us_phone",
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    ),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
]


def passes_luhn(card_str: str) -> bool:
    """Check Luhn checksum for 13 to 16 digit card numbers."""
    digits = [int(c) for c in card_str if c.isdigit()]
    if len(digits) < 13 or len(digits) > 16:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = d * 2
            checksum += doubled - 9 if doubled > 9 else doubled
        else:
            checksum += d
    return checksum % 10 == 0


def secret_hits(text: str) -> list[str]:
    """Scan text and return names of any secret rules hit (used for admission gating)."""
    hits: list[str] = []
    for name, pattern in SECRET_PATTERNS:
        if pattern.search(text):
            hits.append(name)
    return hits


def redact_text(text: str) -> str:
    """Single-pass non-overlapping redaction replacing secret and PII hits with tagged tokens."""
    matches: list[tuple[int, int, str]] = []

    # Collect secret matches
    for name, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            matches.append((m.start(), m.end(), f"[REDACTED:secret:{name}]"))

    # Collect PII matches
    for name, pattern in PII_PATTERNS:
        for m in pattern.finditer(text):
            if name == "credit_card":
                raw = text[m.start() : m.end()]
                if not passes_luhn(raw):
                    continue
            matches.append((m.start(), m.end(), f"[REDACTED:pii:{name}]"))

    if not matches:
        return text

    # Sort matches by start position, earliest start first, longest match first
    matches.sort(key=lambda x: (x[0], -(x[1] - x[0])))

    # Filter out overlapping matches
    filtered: list[tuple[int, int, str]] = []
    last_end = 0
    for start, end, repl in matches:
        if start >= last_end:
            filtered.append((start, end, repl))
            last_end = end

    # Build redacted output string
    result: list[str] = []
    curr = 0
    for start, end, repl in filtered:
        result.append(text[curr:start])
        result.append(repl)
        curr = end
    result.append(text[curr:])
    return "".join(result)
