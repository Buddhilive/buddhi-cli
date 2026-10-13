from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import typer
from rich.console import Console

from buddhi.scripts.antislop_mode import configure_mode
from buddhi.scripts.check_file_size import (
    check_all_files,
    check_staged_files,
)
from buddhi.scripts.check_file_size import (
    selftest as check_file_size_selftest,
)
from buddhi.scripts.contrast import run_contrast_check
from buddhi.scripts.contrast import selftest as contrast_selftest
from buddhi.scripts.receipts import (
    check_report,
)
from buddhi.scripts.receipts import (
    selftest as receipts_selftest,
)
from buddhi.scripts.visual_parity_diff import (
    run_visual_parity_diff,
)
from buddhi.scripts.visual_parity_diff import (
    selftest as visual_parity_diff_selftest,
)

console = Console()
err_console = Console(stderr=True)

scripts_app = typer.Typer(
    name="scripts",
    help="Utility scripts and tools.",
    invoke_without_command=False,
    no_args_is_help=True,
)


@scripts_app.command(name="contrast")
def contrast(
    color_a: str | None = typer.Argument(
        None, help="First color as hex or named color (black/white)."
    ),
    color_b: str | None = typer.Argument(
        None, help="Second color as hex or named color (black/white)."
    ),
    selftest: bool = typer.Option(
        False, "--selftest", help="Run self-test against the reference table."
    ),
) -> None:
    """Check WCAG 2.x contrast ratio between two colors."""
    if selftest:
        code, msg = contrast_selftest()
        if code == 0:
            console.print(msg)
        else:
            err_console.print(msg)
        raise typer.Exit(code=code)

    if color_a is None or color_b is None:
        err_console.print("usage: buddhi scripts contrast <hex1> <hex2> | --selftest")
        raise typer.Exit(code=2)

    try:
        result = run_contrast_check(color_a, color_b)
    except ValueError as exc:
        err_console.print(f"error: {exc}")
        raise typer.Exit(code=2)

    console.print(result.formatted_text)
    raise typer.Exit(code=result.exit_code)


@scripts_app.command(name="antislop-mode")
def antislop_mode(
    mode: str | None = typer.Argument(
        None, help="Set global antislop mode: 'during', 'after', or 'ask'."
    ),
) -> None:
    """View or configure the global antislop usage mode."""
    try:
        output = configure_mode(mode)
    except ValueError as exc:
        err_console.print(f"error: {exc}")
        raise typer.Exit(code=1)

    console.print(output)


@scripts_app.command(name="check-file-size")
def check_file_size_cmd(
    paths: list[str] = typer.Argument(None, help="Staged file paths to verify."),  # noqa: B008
    all_files: bool = typer.Option(
        False, "--all", help="Scan all tracked source files in git index."
    ),
    max_tokens: int = typer.Option(
        8000, "--max-tokens", help="Maximum tokens allowed per source file."
    ),
    selftest: bool = typer.Option(False, "--selftest", help="Run self-test."),
) -> None:
    """Check and ratchet source file sizes against token budget (bytes // 4)."""
    if selftest:
        code, msg = check_file_size_selftest()
        if code == 0:
            console.print(msg)
        else:
            err_console.print(msg)
        raise typer.Exit(code=code)

    if not all_files and not paths:
        err_console.print(
            "usage: buddhi scripts check-file-size --all [--max-tokens N] | <path>... | --selftest"
        )
        raise typer.Exit(code=2)

    if all_files:
        code, lines = check_all_files(max_tokens=max_tokens)
    else:
        code, lines = check_staged_files(paths, max_tokens=max_tokens)

    for line in lines:
        if code == 0:
            console.print(line)
        else:
            err_console.print(line)

    raise typer.Exit(code=code)


@scripts_app.command(name="visual-parity-diff")
def visual_parity_diff_cmd(
    candidate_dir: str | None = typer.Option(
        None, "--candidate-dir", help="Directory of candidate PNG captures."
    ),
    reference_dir: str | None = typer.Option(
        None, "--reference-dir", help="Directory of reference PNG captures."
    ),
    out_dir: str | None = typer.Option(
        None, "--out-dir", help="Output directory for diff artifacts and JSON."
    ),
    crops_json: str | None = typer.Option(
        None, "--crops-json", help="Path to crop coordinates JSON."
    ),
    report_order: str | None = typer.Option(
        None, "--report-order", help="Comma-separated image stems for ordering."
    ),
    selftest: bool = typer.Option(False, "--selftest", help="Run self-test."),
) -> None:
    """Run visual parity diffing or solo scene-metrics telemetry."""
    if selftest:
        code, msg = visual_parity_diff_selftest()
        if code == 0:
            console.print(msg)
        else:
            err_console.print(msg)
        raise typer.Exit(code=code)

    cand = candidate_dir or os.environ.get("CANDIDATE_DIR")
    ref = reference_dir or os.environ.get("REFERENCE_DIR")
    out = out_dir or os.environ.get("OUT_DIR") or "visual-diff"
    crops = crops_json or os.environ.get("CROPS_JSON")
    order_str = report_order or os.environ.get("REPORT_ORDER") or ""

    if not cand:
        err_console.print(
            "error: --candidate-dir or CANDIDATE_DIR environment variable is required."
        )
        raise typer.Exit(code=2)

    cand_path = Path(cand).resolve()
    if not cand_path.is_dir():
        err_console.print(f"error: candidate directory does not exist: {cand_path}")
        raise typer.Exit(code=2)

    ref_path = Path(ref).resolve() if ref else None
    if ref_path and not ref_path.is_dir():
        err_console.print(f"error: reference directory does not exist: {ref_path}")
        raise typer.Exit(code=2)

    order_list = (
        [s.strip() for s in order_str.split(",") if s.strip()] if order_str else None
    )
    crops_path = Path(crops).resolve() if crops else None

    code, report = run_visual_parity_diff(
        candidate_dir=cand_path,
        reference_dir=ref_path,
        out_dir=Path(out).resolve(),
        report_order=order_list,
        crops_json=crops_path,
    )
    if code != 0:
        err_console.print(f"error: {report.get('error', 'visual diff failed')}")
        raise typer.Exit(code=code)

    console.print(json.dumps(report, indent=2))
    raise typer.Exit(code=0)


@scripts_app.command(name="receipts")
def receipts_cmd(
    reports: list[str] = typer.Argument(  # noqa: B008
        None, help="Markdown report files to verify (or '-' for stdin)."
    ),
    json_mode: bool = typer.Option(False, "--json", help="Output findings as JSON."),
    label_mode: bool = typer.Option(
        False, "--label", help="Output annotated markdown with inline comments."
    ),
    window: int = typer.Option(4, "--window", help="Receipt line window."),
    base_dir: str | None = typer.Option(
        None, "--base", help="Base directory for relative artifact paths."
    ),
    selftest: bool = typer.Option(False, "--selftest", help="Run self-test."),
) -> None:
    """Verify numeric claims and SHA-256 artifacts in visual critique reports."""
    if selftest:
        code, msg = receipts_selftest()
        if code == 0:
            console.print(msg)
        else:
            err_console.print(msg)
        raise typer.Exit(code=code)

    if not reports:
        err_console.print(
            "usage: buddhi scripts receipts [--json|--label] [--window N] [--base DIR] <report.md>... | --selftest"
        )
        raise typer.Exit(code=2)

    base = Path(base_dir).resolve() if base_dir else None
    all_passed = True
    all_findings = []

    for r in reports:
        if r == "-":
            content = sys.stdin.read()
            report_path_str = "<stdin>"
            curr_base = base or Path.cwd()
        else:
            p = Path(r).resolve()
            if not p.is_file():
                err_console.print(f"receipts: cannot read {p}")
                raise typer.Exit(code=2)
            content = p.read_text(encoding="utf-8")
            report_path_str = str(p)
            curr_base = base or p.parent

        passed, findings, labeled_lines = check_report(
            content,
            filepath=report_path_str,
            base_dir=curr_base,
            window=window,
        )
        if not passed:
            all_passed = False
        all_findings.extend(findings)

        if label_mode:
            console.print("\n".join(labeled_lines))

    if json_mode:
        data = {
            "passed": all_passed,
            "findingCount": len(all_findings),
            "findings": [
                {
                    "file": f.file,
                    "line": f.line,
                    "column": f.column,
                    "claim": f.claim,
                    "reason": f.reason,
                }
                for f in all_findings
            ],
        }
        console.print(json.dumps(data, indent=2))
    elif not label_mode:
        if all_passed:
            console.print(
                f"receipts: all claims and artifacts verified ({len(reports)} report(s))."
            )
        else:
            err_console.print(f"receipts: {len(all_findings)} finding(s):")
            for f in all_findings:
                err_console.print(f"  {f.file}:{f.line}:{f.column} - {f.reason}")

    exit_code = 0 if all_passed else 1
    raise typer.Exit(code=exit_code)
