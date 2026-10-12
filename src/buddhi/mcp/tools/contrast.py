from __future__ import annotations

from buddhi.scripts.contrast import run_contrast_check


def execute_check_contrast(color_a: str, color_b: str) -> str:
    """Check WCAG 2.x contrast ratio between two colors."""
    try:
        res = run_contrast_check(color_a, color_b)
        return res.formatted_text
    except Exception as exc:  # noqa: BLE001
        return f"Error checking contrast: {exc}"
