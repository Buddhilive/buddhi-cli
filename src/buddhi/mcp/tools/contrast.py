from __future__ import annotations

from pathlib import Path
from typing import Any

from buddhi.scripts.contrast import (
    run_contrast_check,
    run_css_mode,
    run_pair_mode,
)


def execute_check_contrast(
    color_a: str | None = None,
    color_b: str | None = None,
    bg: str | None = None,
    fg: Any = None,
    profile: str = "standard",
    css_path: str | None = None,
    page_bg: str = "#ffffff",
) -> str:
    """Check contrast ratio between colors or across stylesheets."""
    try:
        if css_path:
            p = Path(css_path)
            if not p.is_file():
                return f"Error: CSS file not found: {css_path}"
            _code, msg = run_css_mode(p, page_bg_tok=page_bg, profile=profile)
            return msg

        if bg:
            fg_list: list[str] = []
            if isinstance(fg, list):
                fg_list.extend(str(item) for item in fg)
            elif isinstance(fg, str):
                fg_list.append(fg)
            if color_a:
                fg_list.insert(0, color_a)
            if color_b:
                fg_list.append(color_b)
            if not fg_list:
                return "Error: pair mode needs at least one foreground color (fg)"
            _code, msg = run_pair_mode(bg, fg_list, profile=profile)
            return msg

        if color_a is not None and color_b is not None:
            res = run_contrast_check(color_a, color_b, profile=profile)
            return res.formatted_text

        return "Error: supply either (color_a, color_b), (bg, fg), or css_path"
    except Exception as exc:  # noqa: BLE001
        return f"Error checking contrast: {exc}"
