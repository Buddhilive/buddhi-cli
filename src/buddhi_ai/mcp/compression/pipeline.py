"""
buddhi_shell compression pipeline orchestrator.

Routes raw shell output through the 4-phase processing chain:
  Phase 1 → Noise eradication (ANSI, progress bars, CJK normalization)
  Phase 2 → Domain-specific abstraction (Git, Linter, Traceback)
  Phase 3 → Structural deduplication (Rabin-Karp rolling hash)
  Phase 4 → Compact response protocol (delta format, identifier mapping, token budget)

A ``--raw`` flag bypasses all phases and applies only the token budget hard-cap.
"""

from __future__ import annotations

from buddhi_ai.mcp.compression import phase1_noise, phase2_abstractors, phase3_dedup, phase4_compact


def process(
    raw_output: str,
    budget: int = 8000,
    raw_mode: bool = False,
) -> str:
    """Process *raw_output* through the compression pipeline.

    Args:
        raw_output: The combined stdout+stderr text from the subprocess.
        budget: Maximum token count for the final output. 0 = unbounded.
        raw_mode: If True, skip Phases 1-3 and only apply the token budget cap.

    Returns:
        The compressed (or raw-capped) shell output string.
    """
    if raw_mode:
        # --raw override: bypass all compression, only enforce token ceiling
        return phase4_compact.enforce_budget(raw_output, budget)

    # Phase 1 — Smart Filtering
    text = phase1_noise.apply(raw_output)

    # Phase 2 — Domain-Specific Pattern Matching
    text = phase2_abstractors.apply(text)

    # Phase 3 — Deduplication (only if Phase 2 didn't collapse to a summary line)
    # If the output is a single-line summary (e.g. "[Git: ...]"), skip Phase 3.
    if "\n" in text:
        text = phase3_dedup.apply(text)

    # Phase 4 — Compact Response Protocol + Token Budget Enforcement
    text = phase4_compact.apply(text, budget=budget)

    return text
