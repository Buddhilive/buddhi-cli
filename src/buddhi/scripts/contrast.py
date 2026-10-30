from __future__ import annotations

import itertools
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

REFERENCE_HEADER = (
    "| Pairing (text on background) | Ratio | Normal text (4.5) | Large text (3.0) |"
)
NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
}
FLOORS = {
    "standard": {"text": 4.5, "large": 3.0, "ui": 3.0},
    "shield": {"text": 7.0, "large": 4.5, "ui": 3.0},
}
COLOR_RE = re.compile(
    r"#(?:[0-9a-fA-F]{8}|[0-9a-fA-F]{6}|[0-9a-fA-F]{3,4})\b"
    r"|rgba?\([^)]+\)"
    r"|hsla?\([^)]+\)"
    r"|\b(?:white|black)\b",
    re.IGNORECASE,
)


@dataclass
class ContrastResult:
    ratio: float
    normal_pass: bool
    large_pass: bool
    exit_code: int
    formatted_text: str


def _clamp(x: float, lo: float = 0.0, hi: float = 255.0) -> float:
    return max(lo, min(hi, x))


def parse_color_extended(
    token: str,
) -> tuple[int, int, int, float] | None:
    t = token.strip().lower()
    if t in NAMED_COLORS:
        r, g, b = NAMED_COLORS[t]
        return (r, g, b, 1.0)
    if t.startswith("#"):
        h = t[1:]
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) == 6:
            h += "ff"
        if len(h) != 8:
            return None
        try:
            r, g, b, a = (
                int(h[0:2], 16),
                int(h[2:4], 16),
                int(h[4:6], 16),
                int(h[6:8], 16) / 255.0,
            )
            return (r, g, b, a)
        except ValueError:
            return None
    m = re.match(r"(rgba?|hsla?)\(([^)]+)\)", t)
    if not m:
        return None
    fn, body = m.group(1), m.group(2)
    parts = [p.strip() for p in re.split(r"[,/]", body) if p.strip()]
    if len(parts) < 3:
        return None
    try:
        if fn.startswith("rgb"):
            vals = []
            for p in parts[:3]:
                vals.append(float(p[:-1]) * 2.55 if p.endswith("%") else float(p))
            a = (
                float(parts[3][:-1]) / 100
                if len(parts) > 3 and parts[3].endswith("%")
                else float(parts[3])
                if len(parts) > 3
                else 1.0
            )
            return (
                round(_clamp(vals[0])),
                round(_clamp(vals[1])),
                round(_clamp(vals[2])),
                a,
            )
        # hsl
        h_str = re.sub(r"deg$", "", parts[0])
        h_val = float(h_str) % 360
        s = float(parts[1].rstrip("%")) / 100
        l = float(parts[2].rstrip("%")) / 100
        a = (
            float(parts[3][:-1]) / 100
            if len(parts) > 3 and parts[3].endswith("%")
            else float(parts[3])
            if len(parts) > 3
            else 1.0
        )
        c = (1 - abs(2 * l - 1)) * s
        x = c * (1 - abs((h_val / 60) % 2 - 1))
        mm = l - c / 2
        if h_val < 60:
            r1, g1, b1 = (c, x, 0.0)
        elif h_val < 120:
            r1, g1, b1 = (x, c, 0.0)
        elif h_val < 180:
            r1, g1, b1 = (0.0, c, x)
        elif h_val < 240:
            r1, g1, b1 = (0.0, x, c)
        elif h_val < 300:
            r1, g1, b1 = (x, 0.0, c)
        else:
            r1, g1, b1 = (c, 0.0, x)
        return (
            round((r1 + mm) * 255),
            round((g1 + mm) * 255),
            round((b1 + mm) * 255),
            a,
        )
    except (ValueError, ZeroDivisionError):
        return None


def composite(
    fg: tuple[int, int, int, float], bg: tuple[int, int, int]
) -> tuple[int, int, int]:
    a = fg[3]
    return (
        round(fg[0] * a + bg[0] * (1 - a)),
        round(fg[1] * a + bg[1] * (1 - a)),
        round(fg[2] * a + bg[2] * (1 - a)),
    )


def fmt_hex(rgb: tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def parse_hex(value: str) -> tuple[int, int, int]:
    clean = value.strip().lstrip("#")
    if len(clean) == 3:
        clean = "".join(ch * 2 for ch in clean)
    if not re.fullmatch(r"[0-9A-Fa-f]{6}", clean):
        raise ValueError(f"expected a hex color like #FFFFFF, got {value!r}")
    return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))


def parse_color(value: str) -> tuple[int, int, int]:
    val = value.strip().lower()
    if val in NAMED_COLORS:
        return NAMED_COLORS[val]
    parsed = parse_color_extended(val)
    if parsed is not None:
        return (parsed[0], parsed[1], parsed[2])
    return parse_hex(value)


def parse_pairing(
    pairing: str,
) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    colors = []
    for token in re.split(r"\s+on\s+", pairing):
        token = token.strip()
        match = re.search(r"#[0-9A-Fa-f]{3,6}", token)
        if match:
            colors.append(parse_hex(match.group(0)))
        elif token.lower() in NAMED_COLORS:
            colors.append(NAMED_COLORS[token.lower()])
        else:
            raise ValueError(f"cannot parse {token!r} from pairing {pairing!r}")
    if len(colors) != 2:
        raise ValueError(f"expected two colors in pairing {pairing!r}")
    return (colors[0], colors[1])


def linearize(channel: int) -> float:
    c = channel / 255.0
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = (linearize(ch) for ch in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(
    color_a: tuple[int, int, int], color_b: tuple[int, int, int]
) -> float:
    lum_a, lum_b = luminance(color_a), luminance(color_b)
    lighter, darker = max(lum_a, lum_b), min(lum_a, lum_b)
    return (lighter + 0.05) / (darker + 0.05)


def run_contrast_check(
    color_a_str: str, color_b_str: str, profile: str = "standard"
) -> ContrastResult:
    col_a = parse_color(color_a_str)
    col_b = parse_color(color_b_str)
    ratio = contrast_ratio(col_a, col_b)

    floors = FLOORS.get(profile.lower(), FLOORS["standard"])
    normal_pass = ratio >= floors["text"]
    large_pass = ratio >= floors["large"]
    exit_code = 0 if normal_pass and large_pass else 1

    formatted_text = (
        f"ratio: {ratio:.2f}:1\n"
        f"normal text ({floors['text']}:1): {'PASS' if normal_pass else 'FAIL'}\n"
        f"large text  ({floors['large']}:1): {'PASS' if large_pass else 'FAIL'}"
    )
    return ContrastResult(
        ratio=ratio,
        normal_pass=normal_pass,
        large_pass=large_pass,
        exit_code=exit_code,
        formatted_text=formatted_text,
    )


def run_pair_mode(
    bg_tok: str, fg_toks: list[str], profile: str = "standard"
) -> tuple[int, str]:
    floors = FLOORS.get(profile.lower(), FLOORS["standard"])
    bg_raw = parse_color_extended(bg_tok)
    if bg_raw is None:
        raise ValueError(f"cannot parse background {bg_tok!r}")
    bg_rgb = composite(bg_raw, (255, 255, 255))

    lines = [f"profile: {profile} | background: {fmt_hex(bg_rgb)}"]
    failures = 0
    for tok in fg_toks:
        fg_raw = parse_color_extended(tok)
        if fg_raw is None:
            lines.append(f"  {tok}: UNPARSEABLE")
            failures += 1
            continue
        fg_rgb = composite(fg_raw, bg_rgb)
        r = contrast_ratio(fg_rgb, bg_rgb)
        verdicts = " | ".join(
            f"{use} {'PASS' if r >= floor else 'FAIL'} (>={floor}:1)"
            for use, floor in floors.items()
        )
        lines.append(f"  {fmt_hex(fg_rgb)} ({tok}): {r:.2f}:1 - {verdicts}")
        lines.append(
            f"    -> REPORT.md: | [use] | {fmt_hex(fg_rgb)} | {fmt_hex(bg_rgb)} | {r:.2f}:1 | "
            f"{floors['text']}:1 | {'PASS' if r >= floors['text'] else 'FAIL'} |"
        )
        if r < floors["text"]:
            failures += 1
    return (1 if failures else 0, "\n".join(lines))


def run_css_mode(
    css_path: Path, page_bg_tok: str = "#ffffff", profile: str = "standard"
) -> tuple[int, str]:
    floors = FLOORS.get(profile.lower(), FLOORS["standard"])
    page_bg_raw = parse_color_extended(page_bg_tok)
    if page_bg_raw is None:
        raise ValueError(f"cannot parse --page-bg {page_bg_tok!r}")
    page_bg_rgb = composite(page_bg_raw, (255, 255, 255))

    try:
        css = css_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        raise ValueError(f"cannot read CSS file: {e}") from e

    seen: dict[str, str] = {}
    for tok in COLOR_RE.findall(css):
        c = parse_color_extended(tok)
        if c is not None:
            seen.setdefault(fmt_hex(composite(c, page_bg_rgb)), tok)
    colors = list(seen.items())

    lines = [
        (
            f"TRIAGE (not a verdict): {len(colors)} distinct colors in {css_path}; "
            f"pairs below the {profile} text floor ({floors['text']}:1) flagged."
        )
    ]
    flagged = 0
    for (hex1, _tok1), (hex2, _tok2) in itertools.combinations(colors, 2):
        r = contrast_ratio(parse_color(hex1), parse_color(hex2))
        if r < floors["text"]:
            flagged += 1
            band = (
                "below UI floor (3:1)"
                if r < floors["ui"]
                else "text fails, large/UI may pass"
            )
            lines.append(f"  {hex1} × {hex2}: {r:.2f}:1 — {band}")
    total_pairs = len(colors) * (len(colors) - 1) // 2 if len(colors) > 1 else 0
    lines.append(
        f"{flagged} pair(s) flagged out of {total_pairs}. "
        "A flagged pair only matters if the two colors actually meet in the page — verify intent, then fix or record."
    )
    return (0, "\n".join(lines))


def _get_skill_doc_text() -> str | None:
    try:
        ref_file = (
            resources.files("buddhi.templates.agents")
            / "skills"
            / "antislop-human"
            / "SKILL.md"
        )
        return ref_file.read_text(encoding="utf-8")
    except Exception:  # noqa: BLE001
        here = Path(__file__).resolve().parent
        for candidate in [
            here.parent
            / "templates"
            / "agents"
            / "skills"
            / "antislop-human"
            / "SKILL.md",
            Path.cwd()
            / "src"
            / "buddhi"
            / "templates"
            / "agents"
            / "skills"
            / "antislop-human"
            / "SKILL.md",
            Path.cwd() / ".agents" / "skills" / "antislop-human" / "SKILL.md",
        ]:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
    return None


def parse_reference_rows(text: str) -> list[dict[str, str | float]]:
    rows: list[dict[str, str | float]] = []
    in_table = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith(REFERENCE_HEADER):
            in_table = True
            continue
        if not in_table:
            continue
        if not line.startswith("|"):
            break
        if line.startswith("|---"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) != 4:
            continue
        pairing, ratio_str, normal, large = cells
        rows.append(
            {
                "pairing": pairing,
                "ratio": float(ratio_str),
                "normal": normal,
                "large": large,
            }
        )
    return rows


def selftest() -> tuple[int, str]:
    text = _get_skill_doc_text()
    if text is None:
        return (
            2,
            "selftest: antislop-human/SKILL.md reference doc not found; cannot check table",
        )

    try:
        rows = parse_reference_rows(text)
    except Exception as exc:  # noqa: BLE001
        return 1, f"selftest: could not read table from SKILL.md: {exc}"

    if not rows:
        return 1, "selftest: no reference rows found in SKILL.md"

    failures = []
    for row in rows:
        pairing_str = str(row["pairing"])
        color_a, color_b = parse_pairing(pairing_str)
        raw = contrast_ratio(color_a, color_b)
        computed = round(raw, 2)
        expected_normal = "Pass" if raw >= 4.5 else "Fail"
        expected_large = "Pass" if raw >= 3.0 else "Fail"

        if f"{computed:.2f}" != f"{float(row['ratio']):.2f}":
            failures.append(
                f"selftest: {pairing_str}: table says {row['ratio']}, formula says {computed:.2f}"
            )
        if row["normal"] != expected_normal:
            failures.append(
                f"selftest: {pairing_str}: normal text marked {row['normal']}, should be {expected_normal}"
            )
        if row["large"] != expected_large:
            failures.append(
                f"selftest: {pairing_str}: large text marked {row['large']}, should be {expected_large}"
            )

    upstream_cases = [
        ("#767676", "#5a5a5a", False),
        ("#121212", "#f2f2f2", True),
        ("#ffffff", "#747474", True),
        ("#ffffff", "#777777", False),
        ("hsl(14, 60%, 72%)", "#121212", True),
        ("rgba(0,0,0,0.5)", "white", False),
    ]
    for bg_tok, fg_tok, should_pass in upstream_cases:
        bg_ext = parse_color_extended(bg_tok)
        fg_ext = parse_color_extended(fg_tok)
        if bg_ext is None or fg_ext is None:
            failures.append(
                f"selftest: could not parse upstream case {bg_tok} vs {fg_tok}"
            )
            continue
        bg_rgb = composite(bg_ext, (255, 255, 255))
        fg_rgb = composite(fg_ext, bg_rgb)
        r = contrast_ratio(fg_rgb, bg_rgb)
        if (r >= 4.5) != should_pass:
            failures.append(
                f"selftest upstream: {bg_tok} vs {fg_tok}: {r:.2f}:1 -> {'pass' if r >= 4.5 else 'fail'} (expected {'pass' if should_pass else 'fail'})"
            )

    if failures:
        return 1, "\n".join(failures)
    return (
        0,
        f"selftest: {len(rows)} reference pairs and {len(upstream_cases)} upstream cases OK",
    )
