from __future__ import annotations

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


@dataclass
class ContrastResult:
    ratio: float
    normal_pass: bool
    large_pass: bool
    exit_code: int
    formatted_text: str


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
    return parse_hex(value)


def parse_pairing(pairing: str) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """Turn 'White on #333333' or '#555555 on black' into two RGB tuples."""
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
    if c <= 0.03928:
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


def run_contrast_check(color_a_str: str, color_b_str: str) -> ContrastResult:
    col_a = parse_color(color_a_str)
    col_b = parse_color(color_b_str)
    ratio = contrast_ratio(col_a, col_b)

    normal_pass = ratio >= 4.5
    large_pass = ratio >= 3.0
    exit_code = 0 if normal_pass and large_pass else 1

    formatted_text = (
        f"ratio: {ratio:.2f}:1\n"
        f"normal text (4.5:1): {'PASS' if normal_pass else 'FAIL'}\n"
        f"large text  (3.0:1): {'PASS' if large_pass else 'FAIL'}"
    )
    return ContrastResult(
        ratio=ratio,
        normal_pass=normal_pass,
        large_pass=large_pass,
        exit_code=exit_code,
        formatted_text=formatted_text,
    )


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
        # Fallback to local file discovery if templates package not packaged
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

    if failures:
        return 1, "\n".join(failures)
    return 0, f"selftest: {len(rows)} reference pairs OK"
