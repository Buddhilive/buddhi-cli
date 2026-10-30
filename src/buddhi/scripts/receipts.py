"""Cryptographic and numeric claim verifier for visual critique reports.

Ported from receipts.mjs in @dzhng/skills (MIT License).
Verifies that:
1. Every numeric measurement claim in prose is backed by an executed command receipt block within N lines.
2. Every referenced artifact file exists on disk and matches its stated SHA-256 hash.
"""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

MEASUREMENT_UNITS = [
    "px",
    "pixel",
    "pixels",
    "pt",
    "dp",
    "em",
    "rem",
    "luminance",
    "luma",
    "brightness",
    "lightness",
    "value",
    "intensity",
    "contrast",
    "ratio",
    "delta",
    "diff",
    "difference",
    "variance",
    "stddev",
    "mean",
    "median",
    "average",
    "avg",
    "rmse",
    "mae",
    "psnr",
    "ssim",
    "entropy",
    "density",
    "coverage",
    "share",
    "opacity",
    "alpha",
    "rgb",
    "rgba",
    "hsl",
    "hex",
    "channel",
    "saturation",
    "hue",
    "degrees",
    "deg",
    "offset",
    "width",
    "height",
    "area",
    "count",
]

MEASUREMENT_VERBS = [
    "measure",
    "measured",
    "measures",
    "measurement",
    "computed",
    "calculated",
    "sampled",
    "scored",
    "reads",
    "read",
    "registers",
    "quantif",
]

NUMBER_RE = re.compile(r"(?<![\w.$#-])(\d+(?:\.\d+)?)\s*(%|px|pt|dp|em|rem)?(?![\w-])")
HEX_RE = re.compile(r"(?<![\w])(0x[0-9a-f]{2,8}|#[0-9a-f]{3,8})(?![\w])", re.IGNORECASE)
ARTIFACT_RE = re.compile(
    r"(?<![\w@/-])((?:\.{1,2}/|~/|/)?[\w.-]+(?:/[\w.-]+)*\.(?:png|jpe?g|gif|webp|bmp|tiff?|pdf|csv|tsv|json|ndjson|txt|npy))(?![\w])",
    re.IGNORECASE,
)
SHA256_RE = re.compile(r"\b(?:sha-?256[\s:=]*)?([0-9a-f]{64})\b", re.IGNORECASE)

TOOLS = {
    "node",
    "python",
    "python3",
    "buddhi",
    "magick",
    "convert",
    "ffmpeg",
    "ffprobe",
    "identify",
    "compare",
    "sips",
    "exiftool",
    "jq",
    "awk",
    "sed",
    "grep",
    "rg",
    "cat",
    "head",
    "tail",
    "ls",
    "wc",
    "printf",
    "echo",
    "uv",
    "uvx",
    "npx",
    "pnpm",
    "deno",
    "bun",
    "bash",
    "sh",
    "zsh",
    "sha256sum",
    "shasum",
    "stat",
    "file",
    "du",
    "find",
    "sort",
    "uniq",
    "cut",
    "tr",
    "xxd",
    "od",
}


@dataclass
class ReceiptRun:
    start_line: int
    end_line: int
    command: str
    output_lines: list[str] = field(default_factory=list)
    numbers: set[str] = field(default_factory=set)
    hexes: set[str] = field(default_factory=set)


@dataclass
class ClaimHit:
    line_idx: int
    value: str
    text: str
    column: int
    is_hex: bool = False


@dataclass
class Finding:
    file: str
    line: int
    column: int
    claim: str
    reason: str


def looks_like_argument(token: str) -> bool:
    if token.startswith("-"):
        return True
    if "/" in token or "\\" in token:
        return True
    if re.search(r"\.\w{1,6}$", token):
        return True
    if "=" in token:
        return True
    if token.startswith(("'", '"')) or "%[" in token or "{" in token:
        return True
    if re.match(r"^\w+:$", token):
        return True
    return bool(token.startswith(("$", "@", "#")))


def is_invocation(line: str) -> bool:
    stripped = re.sub(r"^\s*[$>]\s+", "", line).strip()
    if not stripped:
        return False
    tokens = stripped.split()
    head = os.path.basename(tokens[0])
    runnable = (
        head in TOOLS
        or tokens[0].startswith(("./", "../", "/"))
        or bool(re.match(r"^\w[\w.-]*\.(?:mjs|js|py|sh)$", head))
    )
    if not runnable:
        return False
    return any(looks_like_argument(t) for t in tokens[1:])


def parse_receipt_lines(lines: list[str]) -> list[bool]:
    """Flag which lines belong to a fenced block, indented code, or shell transcript."""
    in_receipt = [False] * len(lines)
    fence: str | None = None
    transcript = False

    for i, line in enumerate(lines):
        fence_match = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence_match:
            if fence is None:
                fence = fence_match.group(1)[:3]
                in_receipt[i] = True
                continue
            if fence_match.group(1).startswith(fence):
                fence = None
                in_receipt[i] = True
                continue
        if fence is not None:
            in_receipt[i] = True
            continue

        if re.match(r"^\s{4,}\S", line) and not re.match(r"^\s*[-*+]\s", line):
            in_receipt[i] = True
            continue

        if re.match(r"^\s*\$\s+\S", line):
            in_receipt[i] = True
            transcript = True
            continue
        if transcript:
            if not line.strip():
                transcript = False
            else:
                in_receipt[i] = True

    return in_receipt


def extract_receipt_runs(lines: list[str]) -> list[ReceiptRun]:
    """Group contiguous receipt lines into runs and collect command and outputs."""
    in_receipt = parse_receipt_lines(lines)
    runs: list[ReceiptRun] = []
    i = 0
    n = len(lines)

    while i < n:
        if not in_receipt[i]:
            i += 1
            continue
        start = i
        while i < n and in_receipt[i]:
            i += 1
        end = i

        block_lines = lines[start:end]
        inv_idx = -1
        for idx, bline in enumerate(block_lines):
            if is_invocation(bline):
                inv_idx = idx
                break

        if inv_idx != -1 and inv_idx + 1 < len(block_lines):
            cmd = block_lines[inv_idx].strip()
            out_lines = [l for l in block_lines[inv_idx + 1 :] if not is_invocation(l)]
            if out_lines:
                run = ReceiptRun(
                    start_line=start, end_line=end, command=cmd, output_lines=out_lines
                )
                for ol in out_lines:
                    for m in NUMBER_RE.finditer(ol):
                        run.numbers.add(m.group(1))
                    for m in HEX_RE.finditer(ol):
                        run.hexes.add(m.group(1).lower())
                runs.append(run)

    return runs


def claims_in(line: str, line_idx: int, previous: str = "") -> list[ClaimHit]:
    lower = line.lower()
    carried = previous.lower()[-60:]
    hits: list[ClaimHit] = []

    for match in NUMBER_RE.finditer(line):
        value, suffix = match.groups()
        start = match.start()
        before = f"{carried} " if start < 40 else ""
        before += lower[max(0, start - 40) : start]
        after = lower[start + len(match.group(0)) : start + len(match.group(0)) + 24]
        context = f"{before} {after}"

        unit_attached = suffix == "%" or bool(suffix)
        unit_nearby = any(
            re.search(rf"\b{re.escape(u)}\b", context) for u in MEASUREMENT_UNITS
        )
        verb_nearby = any(v in before for v in MEASUREMENT_VERBS)

        if not unit_attached and not unit_nearby and not verb_nearby:
            continue
        hits.append(
            ClaimHit(
                line_idx=line_idx,
                value=value,
                text=match.group(0).strip(),
                column=start + 1,
                is_hex=False,
            )
        )

    for match in HEX_RE.finditer(line):
        hits.append(
            ClaimHit(
                line_idx=line_idx,
                value=match.group(1).lower(),
                text=match.group(1),
                column=match.start() + 1,
                is_hex=True,
            )
        )

    return hits


def check_report(
    text: str,
    filepath: str = "<stdin>",
    base_dir: Path | None = None,
    window: int = 4,
) -> tuple[bool, list[Finding], list[str]]:
    """Validate report text and return (passed, findings, labeled_lines)."""
    lines = text.splitlines()
    in_receipt = parse_receipt_lines(lines)
    runs = extract_receipt_runs(lines)
    findings: list[Finding] = []
    base = base_dir or Path.cwd()

    # 1. Measurement claims check
    labeled_lines: list[str] = []
    prev_line = ""

    for i, line in enumerate(lines):
        unsupported_on_line: list[str] = []
        if not in_receipt[i]:
            hits = claims_in(line, i, prev_line)
            for hit in hits:
                # Find covering receipt run within window
                covered = False
                for r in runs:
                    if r.start_line - window - 1 <= i <= r.end_line + window + 1:
                        if hit.is_hex and hit.value in r.hexes:
                            covered = True
                            break
                        if not hit.is_hex and hit.value in r.numbers:
                            covered = True
                            break
                if not covered:
                    findings.append(
                        Finding(
                            file=filepath,
                            line=i + 1,
                            column=hit.column,
                            claim=hit.text,
                            reason=f"unsupported quantity '{hit.text}' (no matching receipt within {window} lines)",
                        )
                    )
                    unsupported_on_line.append(hit.text)
            prev_line = line
        else:
            prev_line = ""

        if unsupported_on_line:
            label = f" <!-- UNSUPPORTED: {', '.join(unsupported_on_line)} -->"
            labeled_lines.append(line + label)
        else:
            labeled_lines.append(line)

    # 2. Artifact and SHA256 check
    for i, line in enumerate(lines):
        if in_receipt[i]:
            continue
        artifacts = list(ARTIFACT_RE.finditer(line))
        hashes = list(SHA256_RE.finditer(line))

        if artifacts and hashes and len(artifacts) != len(hashes):
            findings.append(
                Finding(
                    file=filepath,
                    line=i + 1,
                    column=1,
                    claim=line.strip(),
                    reason=f"ambiguous pairing: {len(artifacts)} artifact(s) and {len(hashes)} hash(es) on same line",
                )
            )

        for match in artifacts:
            rel_path = match.group(1)
            target = base / rel_path if not os.path.isabs(rel_path) else Path(rel_path)
            if not target.is_file():
                findings.append(
                    Finding(
                        file=filepath,
                        line=i + 1,
                        column=match.start() + 1,
                        claim=rel_path,
                        reason=f"missing artifact: file does not exist at {target}",
                    )
                )

        if artifacts and hashes and len(artifacts) == len(hashes):
            for art_m, hash_m in zip(artifacts, hashes):
                rel_path = art_m.group(1)
                expected_hash = hash_m.group(1).lower()
                target = (
                    base / rel_path if not os.path.isabs(rel_path) else Path(rel_path)
                )
                if target.is_file():
                    actual_hash = (
                        hashlib.sha256(target.read_bytes()).hexdigest().lower()
                    )
                    if actual_hash != expected_hash:
                        findings.append(
                            Finding(
                                file=filepath,
                                line=i + 1,
                                column=art_m.start() + 1,
                                claim=rel_path,
                                reason=f"hash mismatch for {rel_path}: expected {expected_hash}, got {actual_hash}",
                            )
                        )

    passed = len(findings) == 0
    return passed, findings, labeled_lines


def selftest() -> tuple[int, str]:
    """Run internal test cases."""
    doc = """
# Report
The test produced 42px offset.
```bash
$ python script.py --check
output: 42
```
Now verified.
"""
    passed, findings, _ = check_report(doc, filepath="test.md", window=4)
    assert passed, f"Expected pass, got findings: {findings}"
    return 0, "selftest: receipts OK"
