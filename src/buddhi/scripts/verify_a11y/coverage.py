from __future__ import annotations

import re
from pathlib import Path

from buddhi.scripts.verify_a11y.artifacts import (
    body_of,
    read,
    scannable,
    source_files,
    status_claims_pass,
)
from buddhi.scripts.verify_a11y.models import (
    PROFILE_FLOORS,
    GateFinding,
)

Q = r"[\"'`]"
ROLE_OF = (
    r"(?:(?<![\w.-]):?role\s*=\s*(?:\{\s*)?(?:\"'|"
    + Q
    + r")"
    + r"|(?<![\w-])role\s*:\s*"
    + Q
    + r"|setAttribute\(\s*"
    + Q
    + r"role"
    + Q
    + r"\s*,\s*"
    + Q
    + r"|\.role\s*=\s*"
    + Q
    + r")"
)
END = r"(?![\w-])"


def tag(name: str) -> str:
    return r"(?:<" + name + END + r"|createElement\(\s*" + Q + name + Q + r"\s*[,)])"


IN_TAG = r"<[a-z][\w.-]*(?:\"[^\"]*\"|'[^']*'|[^>\"'])*?\s"

GUIDE_SIGNATURES = {
    "guide-buttons": (tag("button"), ROLE_OF + r"button" + END),
    "guide-navigation": (
        tag("nav"),
        tag("main"),
        ROLE_OF + r"(?:navigation|main)" + END,
    ),
    "guide-forms": (
        tag("form"),
        tag("textarea"),
        tag("input")
        + r"(?![^>]*\btype\s*=\s*[\"'](?:hidden|checkbox|radio|range|submit|button|reset|image|color)[\"'])",
    ),
    "guide-form-controls": (
        tag("select"),
        r"\btype\s*=\s*[\"'](?:checkbox|radio|range)[\"']",
        ROLE_OF + r"(?:switch|checkbox|radiogroup|radio|slider)" + END,
    ),
    "guide-modals": (
        tag("dialog"),
        ROLE_OF + r"(?:alertdialog|dialog)" + END,
        r"\baria-modal\b",
    ),
    "guide-tabs-accordion": (
        ROLE_OF + r"(?:tablist|tabpanel|tab)" + END,
        tag("details"),
    ),
    "guide-tables": (tag("table"), ROLE_OF + r"(?:table|grid|treegrid)" + END),
    "guide-toasts-notifications": (
        ROLE_OF + r"(?:status|alert)" + END,
        r"\baria-live\b",
    ),
    "guide-tooltips-popovers": (
        ROLE_OF + r"tooltip" + END,
        IN_TAG + r"popover(?:target)?(?=\s*=|[\s>/])",
    ),
    "guide-loading-skeleton": (r"\baria-busy\b",),
    "guide-autocomplete": (
        ROLE_OF + r"combobox" + END,
        r"\baria-autocomplete\b",
        tag("datalist"),
    ),
    "guide-carousels-sliders": (
        r"\baria-roledescription\s*=\s*[\"'](?:carousel|slide)[\"']",
    ),
    "guide-datepicker": (r"\btype\s*=\s*[\"'](?:date|datetime-local|month|week)[\"']",),
    "guide-drag-drop": (
        IN_TAG + r"draggable(?:\s*=\s*(?:[\"']true[\"']|\{true\}))?(?=[\s>/])",
    ),
    "guide-infinite-scroll": (ROLE_OF + r"feed" + END,),
    "guide-media": (
        tag("video"),
        tag("audio"),
        tag("iframe") + r"[^>]*\b(?:youtube(?:-nocookie)?\.com|player\.vimeo\.com)/",
    ),
    "guide-treeview": (ROLE_OF + r"tree" + END,),
}


def hex_rgb(token: str) -> tuple[int, int, int]:
    h = token.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def luminance(rgb: tuple[int, int, int]) -> float:
    def chan(c: float) -> float:
        c /= 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (chan(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg: str, bg: str) -> float:
    l1, l2 = sorted((luminance(hex_rgb(fg)), luminance(hex_rgb(bg))), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


def normalize_hex(token: str) -> str:
    h = token.lstrip("#").lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return h


def check_contrast_evidence(
    root: Path,
    report: Path,
    src: Path,
    decisions_path: Path | None,
    findings: list[GateFinding],
) -> None:
    body = body_of(report)
    texts = [body] + (
        [body_of(decisions_path)] if decisions_path and decisions_path.is_file() else []
    )

    profile = (
        "shield"
        if re.search(r"\bShield\b|\bAAA\b", body)
        else "launchpad"
        if re.search(r"\bLaunchpad\b", body)
        else "standard"
    )
    floor_default = PROFILE_FLOORS[profile]

    hex_re = re.compile(r"(?<![\w#])#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b")
    ratio_re = re.compile(r"(\d+(?:[.,]\d+)?)\s*:\s*1\b")
    rows = 0
    source_hex: set[str] | None = None

    for text in texts:
        for raw in text.splitlines():
            if not raw.lstrip().startswith("|"):
                continue
            line = raw.replace("**", "")
            colors = hex_re.findall(line)
            ratios = [float(r.replace(",", ".")) for r in ratio_re.findall(line)]
            if len(colors) < 2 or not ratios:
                continue
            rows += 1
            fg, bg = colors[0], colors[1]
            declared = ratios[0]
            floor = ratios[1] if len(ratios) > 1 else floor_default
            computed = contrast(fg, bg)
            label = f"{fg} on {bg}"
            if abs(computed - declared) > 0.1:
                findings.append(
                    GateFinding(
                        "ERROR",
                        "contrast-evidence",
                        f"REPORT.md records {label} as {declared:g}:1; the WCAG formula gives {computed:.2f}:1. Measured evidence must match the arithmetic (A11Y.md §3) — recompute with tools/contrast-check.py.",
                    )
                )
                continue
            marked_pass = bool(re.search(r"✅|\bPASS\b|\bOK\b", line, re.IGNORECASE))
            if computed < floor - 0.005 and marked_pass:
                findings.append(
                    GateFinding(
                        "ERROR",
                        "contrast-evidence",
                        f"REPORT.md marks {label} ({computed:.2f}:1) as passing, below the {floor:g}:1 floor it is measured against.",
                    )
                )
            elif computed < floor - 0.005:
                findings.append(
                    GateFinding(
                        "WARN",
                        "contrast-evidence",
                        f"{label} is {computed:.2f}:1, below the {floor:g}:1 floor — recorded honestly; fix it or open an EXCEPTIONS.md entry.",
                    )
                )
            if source_hex is None:
                source_hex = set()
                for path in source_files(root, src):
                    text_src = read(path) or ""
                    source_hex.update(
                        normalize_hex(h) for h in hex_re.findall(text_src)
                    )
            if source_hex:
                for color in (fg, bg):
                    if normalize_hex(color) not in source_hex:
                        findings.append(
                            GateFinding(
                                "WARN",
                                "contrast-evidence",
                                f"{color} (from the pair {label}) does not appear in the source. If tokens are computed at runtime (hsl(), color-mix()) this is expected; otherwise the pair measured a color the project does not use.",
                            )
                        )

    checkpoint_checked = re.search(
        r"^\s*-\s*\[x\][^\n]*(contrast|contraste)", body, re.IGNORECASE | re.MULTILINE
    )
    if rows == 0 and checkpoint_checked:
        findings.append(
            GateFinding(
                "ERROR",
                "contrast-evidence",
                'The contrast checkpoint is marked verified but no measured pair is recorded. Record each pair as foreground, background and ratio (#hex · #hex · N:1) in the REPORT.md pair table — "looks sufficient" is fabricated evidence (A11Y.md §3).',
            )
        )


def check_guide_coverage(
    root: Path, report: Path, src: Path, findings: list[GateFinding]
) -> None:
    body = body_of(report)
    section = re.search(
        r"^#{2,3}\s*3\.[^\n]*\n(.*?)(?=^##\s|\Z)", body, re.MULTILINE | re.DOTALL
    )
    named = section.group(1).lower() if section else ""
    claims_pass = status_claims_pass(body)

    for path in sorted(source_files(root, src)):
        suffix = path.suffix.lower()
        if suffix in (".css", ".scss"):
            continue
        text = scannable(path)
        if not text:
            continue
        flags = re.IGNORECASE if suffix in (".html", ".htm") else 0
        for guide, patterns in GUIDE_SIGNATURES.items():
            if guide in named:
                continue
            for pattern in patterns:
                m = re.search(pattern, text, flags)
                if m:
                    try:
                        rel = path.relative_to(root)
                    except ValueError:
                        rel = path
                    line = text.count("\n", 0, m.start()) + 1
                    where = f"{rel}:{line}"
                    if claims_pass:
                        findings.append(
                            GateFinding(
                                "ERROR",
                                "guide-coverage",
                                f"REPORT.md claims PASS but does not cover `{guide}` in §3, while {where} contains its component ({m.group(0)[:40]!r}). Run that guide's scenarios before claiming PASS (A11Y.md §7).",
                            )
                        )
                    else:
                        findings.append(
                            GateFinding(
                                "WARN",
                                "guide-coverage",
                                f"{where} matches `{guide}`, but REPORT.md §3 does not name it. If the interface contains that component, run its scenarios (A11Y.md §7).",
                            )
                        )
                    break
