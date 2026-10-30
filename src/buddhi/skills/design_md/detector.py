"""Fact and design token detector for DESIGN.md."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from buddhi.skills.design_md.models import DesignFacts, DesignTokens

_EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "target",
    ".buddhi",
    "__pycache__",
}

_CSS_EXTS = {".css", ".scss", ".sass", ".postcss", ".less"}


def _default_neutral_tokens() -> DesignTokens:
    return DesignTokens(
        colors={
            "background": "#ffffff",
            "surface": "#f8fafc",
            "surface-elevated": "#ffffff",
            "text": "#0f172a",
            "text-muted": "#64748b",
            "primary": "#1e293b",
            "primary-foreground": "#ffffff",
            "secondary": "#f1f5f9",
            "secondary-foreground": "#0f172a",
            "accent": "#2563eb",
            "accent-foreground": "#ffffff",
            "border": "#e2e8f0",
            "destructive": "#dc2626",
            "destructive-foreground": "#ffffff",
        },
        typography={
            "fonts": {
                "sans": "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                "mono": "'JetBrains Mono', 'Fira Code', ui-monospace, monospace",
                "serif": "'Newsreader', 'Georgia', serif",
            },
            "scale": {
                "xs": {"size": "0.75rem", "line-height": "1rem"},
                "sm": {"size": "0.875rem", "line-height": "1.25rem"},
                "base": {"size": "1rem", "line-height": "1.5rem"},
                "lg": {"size": "1.125rem", "line-height": "1.75rem"},
                "xl": {"size": "1.25rem", "line-height": "1.75rem"},
                "2xl": {"size": "1.5rem", "line-height": "2rem"},
            },
            "reading-width": "65ch",
        },
        spacing={
            "base": "4px",
            "scale": {
                "1": "4px",
                "2": "8px",
                "3": "12px",
                "4": "16px",
                "6": "24px",
                "8": "32px",
            },
        },
        rounded={
            "none": "0px",
            "sm": "2px",
            "md": "6px",
            "lg": "12px",
            "full": "9999px",
        },
        elevation={
            "none": "none",
            "sm": "0 1px 2px 0 rgb(0 0 0 / 0.05)",
            "md": "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
            "lg": "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
        },
    )


def _scan_css_variables(file_path: Path, tokens: DesignTokens) -> None:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    # Match CSS custom properties: --prefix-name: value;
    var_re = re.compile(r"--([a-zA-Z0-9_-]+)\s*:\s*([^;]+);")
    for match in var_re.finditer(content):
        prop, val = match.group(1).lower().strip(), match.group(2).strip()
        # Clean quotes
        val_clean = val.strip("\"'")

        if prop.startswith(("color-", "color_")):
            name = prop.replace("color-", "").replace("color_", "")
            tokens.colors[name] = val_clean
        elif prop.startswith(("font-", "font_")):
            name = prop.replace("font-", "").replace("font_", "")
            if not isinstance(tokens.typography.get("fonts"), dict):
                tokens.typography["fonts"] = {}
            tokens.typography["fonts"][name] = val_clean
        elif prop.startswith(("radius-", "radius_", "rounded-")):
            name = (
                prop.replace("radius-", "")
                .replace("radius_", "")
                .replace("rounded-", "")
            )
            tokens.rounded[name] = val_clean
        elif prop.startswith(("spacing-", "space-")):
            name = prop.replace("spacing-", "").replace("space-", "")
            tokens.spacing[name] = val_clean
        elif prop.startswith(("shadow-", "elevation-")):
            name = prop.replace("shadow-", "").replace("elevation-", "")
            tokens.elevation[name] = val_clean


def _scan_tailwind_config(file_path: Path, tokens: DesignTokens) -> None:
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return

    # Extract hex colors: key: "#hex" or 'key': '#hex'
    color_re = re.compile(
        r"['\"]?([a-zA-Z0-9_-]+)['\"]?\s*:\s*['\"](#[0-9a-fA-F]{3,8})['\"]"
    )
    for match in color_re.finditer(content):
        k, v = match.group(1).lower(), match.group(2)
        if k not in {"inherit", "current", "transparent"}:
            tokens.colors[k] = v

    # Extract borderRadius: key: "value"
    radius_block_re = re.compile(r"(?:borderRadius|rounded)\s*:\s*\{([^}]+)\}")
    rad_match = radius_block_re.search(content)
    if rad_match:
        val_re = re.compile(r"['\"]?([a-zA-Z0-9_-]+)['\"]?\s*:\s*['\"]([^'\"]+)['\"]")
        for match in val_re.finditer(rad_match.group(1)):
            tokens.rounded[match.group(1)] = match.group(2)


def _scan_token_json(file_path: Path, tokens: DesignTokens) -> None:
    try:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return

    def _walk(obj: Any, prefix: str = "") -> None:
        if isinstance(obj, dict):
            # Check for DTCG format: {"$value": ...} or {"value": ...}
            if "$value" in obj or "value" in obj:
                val = str(obj.get("$value") or obj.get("value"))
                p_lower = prefix.lower()
                if "color" in p_lower:
                    key = p_lower.split(".")[-1]
                    tokens.colors[key] = val
                elif "radius" in p_lower:
                    key = p_lower.split(".")[-1]
                    tokens.rounded[key] = val
                elif "font" in p_lower:
                    key = p_lower.split(".")[-1]
                    if not isinstance(tokens.typography.get("fonts"), dict):
                        tokens.typography["fonts"] = {}
                    tokens.typography["fonts"][key] = val
                return

            for k, v in obj.items():
                _walk(v, f"{prefix}.{k}" if prefix else k)

    _walk(data)


def detect_design_facts(root: Path | None = None) -> DesignFacts:
    """Analyze a repository and extract design tokens and facts."""
    base = Path(root or Path.cwd()).resolve()
    name = base.name

    tokens = _default_neutral_tokens()
    has_ui_surface = False
    framework: str | None = None
    source_files: list[str] = []

    # 1. Look for package.json indicators
    pkg_json = base / "package.json"
    if pkg_json.is_file():
        try:
            pkg = json.loads(pkg_json.read_text(encoding="utf-8", errors="ignore"))
            deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
            if "tailwindcss" in deps:
                framework = "tailwind"
                has_ui_surface = True
            elif any(k in deps for k in ("react", "vue", "svelte", "next", "nuxt")):
                framework = "component-library"
                has_ui_surface = True
        except (json.JSONDecodeError, OSError):
            pass

    # 2. Look for Tailwind configuration files
    for tw_name in (
        "tailwind.config.js",
        "tailwind.config.ts",
        "tailwind.config.mjs",
        "tailwind.config.cjs",
    ):
        tw_path = base / tw_name
        if tw_path.is_file():
            has_ui_surface = True
            framework = "tailwind"
            source_files.append(tw_name)
            _scan_tailwind_config(tw_path, tokens)

    # 3. Look for token JSON files
    for tok_name in (
        "tokens.json",
        "design-tokens.json",
        "theme.json",
        "tokens/tokens.json",
    ):
        tok_path = base / tok_name
        if tok_path.is_file():
            has_ui_surface = True
            framework = framework or "dtcg"
            source_files.append(tok_name)
            _scan_token_json(tok_path, tokens)

    # 4. Search for CSS / SCSS stylesheets (limit walk depth/count)
    file_count = 0
    for path in base.rglob("*"):
        if file_count > 500:
            break
        if any(part in _EXCLUDED_DIRS for part in path.parts):
            continue
        if path.is_file():
            file_count += 1
            if path.suffix.lower() in _CSS_EXTS:
                has_ui_surface = True
                framework = framework or "css"
                try:
                    rel_p = str(path.relative_to(base))
                    source_files.append(rel_p)
                except ValueError:
                    source_files.append(str(path))
                _scan_css_variables(path, tokens)

    return DesignFacts(
        name=name,
        aesthetic="",
        has_ui_surface=has_ui_surface,
        framework=framework,
        source_files=source_files[:10],
        tokens=tokens,
    )
