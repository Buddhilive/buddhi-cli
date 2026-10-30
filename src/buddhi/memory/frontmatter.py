"""Safe YAML frontmatter serializer and parser for OKF memory concepts."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FRONTMATTER_SPLIT_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?(.*)\Z", re.DOTALL)

# OKF Attested Computation fields to strictly reject/strip
_FORBIDDEN_OKF_FIELDS = {"runtime", "parameters", "executor", "attester"}


def split_frontmatter(content: str) -> tuple[dict[str, Any], str]:
    """Splits YAML frontmatter from markdown body.

    Returns (metadata_dict, body_str). If no frontmatter delimiter is present,
    returns ({}, content).
    """
    match = _FRONTMATTER_SPLIT_RE.match(content)
    if not match:
        return {}, content.strip()

    raw_yaml, body = match.group(1), match.group(2)
    try:
        data = yaml.safe_load(raw_yaml) or {}
    except (yaml.YAMLError, OSError, ValueError):
        data = {}

    if not isinstance(data, dict):
        data = {}

    # Reject forbidden Attested Computation fields
    for forbidden in _FORBIDDEN_OKF_FIELDS:
        data.pop(forbidden, None)

    return data, body.strip()


def dump_frontmatter(metadata: dict[str, Any], body: str = "") -> str:
    """Serializes metadata dict into leading --- YAML --- block followed by markdown body."""
    clean_meta = dict(metadata)
    for forbidden in _FORBIDDEN_OKF_FIELDS:
        clean_meta.pop(forbidden, None)

    yaml_str = yaml.safe_dump(
        clean_meta,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    ).strip()

    body_clean = body.strip()
    if body_clean:
        return f"---\n{yaml_str}\n---\n\n{body_clean}\n"
    return f"---\n{yaml_str}\n---\n"
