"""Transcript window slicing, prior-context digestion, and redaction for reflection."""

from __future__ import annotations

import json
from pathlib import Path

from buddhi.scripts.autoharness.redact import redact_text

MAX_WINDOW_BYTES = 200_000
MAX_RECORD_BYTES = 4_000
MAX_DIGEST_BYTES = 20_000
DIGEST_EXCHANGES = 20


def slice_transcript_window(
    transcript_path: Path,
    offset: int = 0,
) -> tuple[str, int]:
    """Seek to byte offset in transcript.jsonl, clip lines, and redact secrets/PII."""
    if not transcript_path.is_file():
        return "", offset

    collected_records: list[str] = []
    total_bytes = 0

    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        f.seek(offset)
        new_offset = f.tell()

        for line in f:
            new_offset = f.tell()
            line_str = line.strip()
            if not line_str:
                continue

            # Clip individual line length
            clipped = line_str[:MAX_RECORD_BYTES]
            collected_records.append(clipped)
            total_bytes += len(clipped)

            if total_bytes >= MAX_WINDOW_BYTES:
                break

    raw_text = "\n".join(collected_records)
    redacted_text = redact_text(raw_text)
    return redacted_text, new_offset


def build_prior_digest(transcript_path: Path, end_offset: int) -> str:
    """Read prior records before end_offset and build a concise summary of user/agent steps."""
    if not transcript_path.is_file() or end_offset <= 0:
        return ""

    exchanges: list[str] = []
    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        curr_offset = 0
        for line in f:
            if curr_offset >= end_offset:
                break
            curr_offset = f.tell()
            line_str = line.strip()
            if not line_str:
                continue

            try:
                rec = json.loads(line_str)
                role = rec.get("source", rec.get("role", "system"))
                content = str(rec.get("content", ""))[:150]
                if content:
                    exchanges.append(f"[{role}]: {content}")
            except json.JSONDecodeError:
                pass

    recent = exchanges[-DIGEST_EXCHANGES:]
    raw_digest = "\n".join(recent)[:MAX_DIGEST_BYTES]
    return redact_text(raw_digest)
