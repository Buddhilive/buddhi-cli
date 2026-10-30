from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Annotated

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
from buddhi.scripts.contrast import (
    run_contrast_check,
    run_css_mode,
    run_pair_mode,
)
from buddhi.scripts.contrast import selftest as contrast_selftest
from buddhi.scripts.receipts import (
    check_report,
)
from buddhi.scripts.receipts import (
    selftest as receipts_selftest,
)
from buddhi.scripts.verify_a11y import (
    run_checks as run_verify_a11y_checks,
)
from buddhi.scripts.verify_a11y import (
    self_test as verify_a11y_selftest,
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
    bg: str | None = typer.Option(None, "--bg", help="Background color for pair mode."),
    fg: list[str] = typer.Option(  # noqa: B008
        [], "--fg", help="Foreground color(s) for pair mode."
    ),
    profile: str = typer.Option(
        "standard",
        "--profile",
        help="Compliance profile: 'standard' (AA) or 'shield' (AAA).",
    ),
    css: str | None = typer.Option(
        None, "--css", help="CSS file path to triage color literals."
    ),
    page_bg: str = typer.Option(
        "#ffffff", "--page-bg", help="Page background for CSS alpha compositing."
    ),
    selftest: bool = typer.Option(
        False, "--selftest", help="Run self-test against the reference table."
    ),
    self_test_flag: bool = typer.Option(
        False, "--self-test", help="Run self-test (alias)."
    ),
) -> None:
    """Check WCAG 2.x contrast ratio between colors, in pairs, or triage CSS."""
    if selftest or self_test_flag:
        code, msg = contrast_selftest()
        if code == 0:
            console.print(msg)
        else:
            err_console.print(msg)
        raise typer.Exit(code=code)

    if css:
        try:
            code, msg = run_css_mode(
                Path(css).resolve(), page_bg_tok=page_bg, profile=profile
            )
            console.print(msg)
            raise typer.Exit(code=code)
        except ValueError as exc:
            err_console.print(f"error: {exc}")
            raise typer.Exit(code=2)

    if bg:
        fg_list = list(fg)
        if color_a:
            fg_list.insert(0, color_a)
        if color_b:
            fg_list.append(color_b)
        if not fg_list:
            err_console.print(
                "error: pair mode needs at least one foreground color (--fg)"
            )
            raise typer.Exit(code=2)
        try:
            code, msg = run_pair_mode(bg, fg_list, profile=profile)
            console.print(msg)
            raise typer.Exit(code=code)
        except ValueError as exc:
            err_console.print(f"error: {exc}")
            raise typer.Exit(code=2)

    if color_a is None or color_b is None:
        err_console.print(
            "usage: buddhi scripts contrast <hex1> <hex2> | --bg <bg> --fg <fg>... | --css <file> | --selftest"
        )
        raise typer.Exit(code=2)

    try:
        result = run_contrast_check(color_a, color_b, profile=profile)
    except ValueError as exc:
        err_console.print(f"error: {exc}")
        raise typer.Exit(code=2)

    console.print(result.formatted_text)
    raise typer.Exit(code=result.exit_code)


@scripts_app.command(name="verify-a11y")
def verify_a11y_cmd(
    project_dir: str = typer.Argument(
        ".", help="Project root directory (default: current directory)."
    ),
    src: str | None = typer.Option(
        None, "--src", help="Subdirectory holding the interface source."
    ),
    report_dir: str | None = typer.Option(
        None, "--report-dir", help="Directory containing A11Y governance artifacts."
    ),
    warn_only: bool = typer.Option(
        False, "--warn-only", help="Report findings without failing exit code."
    ),
    selftest: bool = typer.Option(
        False, "--selftest", help="Run built-in fixture test cases."
    ),
    self_test_flag: bool = typer.Option(
        False, "--self-test", help="Run built-in fixture test cases (alias)."
    ),
) -> None:
    """Run the A11Y.md static gate to verify artifacts, freshness, contrast math, and source anti-patterns."""
    if selftest or self_test_flag:
        code, msg = verify_a11y_selftest()
        if code == 0:
            console.print(msg, markup=False)
        else:
            err_console.print(msg, markup=False)
        raise typer.Exit(code=code)

    proj_root = Path(project_dir).resolve()
    if not proj_root.is_dir():
        err_console.print(f"error: {proj_root} is not a directory")
        raise typer.Exit(code=2)

    src_path = (proj_root / src).resolve() if src else proj_root
    rep_path = Path(report_dir).resolve() if report_dir else None

    result = run_verify_a11y_checks(
        root=proj_root,
        src=src_path,
        report_dir=rep_path,
        warn_only=warn_only,
    )
    encoding = sys.stdout.encoding or "utf-8"
    out_text = result.output_text.encode(encoding, errors="replace").decode(encoding)
    console.print(out_text, markup=False)
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
        console.print(json.dumps(data, indent=2), markup=False, highlight=False)
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


autoharness_app = typer.Typer(
    name="autoharness",
    help="AutoHarness self-learning agent skill layer management and diagnostics.",
    invoke_without_command=True,
    no_args_is_help=True,
)
scripts_app.add_typer(autoharness_app, name="autoharness")


@autoharness_app.callback(invoke_without_command=True)
def autoharness_main(
    ctx: typer.Context,
    selftest: bool = typer.Option(False, "--selftest", help="Run built-in self-tests."),
) -> None:
    """AutoHarness self-learning skill layer entrypoint."""
    if selftest:
        from buddhi.scripts.autoharness.selftest import run_selftest

        code, msg = run_selftest()
        if code == 0:
            console.print(f"[bold green]pass:[/bold green] {msg}")
        else:
            err_console.print(f"[bold red]fail:[/bold red] {msg}")
        raise typer.Exit(code=code)


@autoharness_app.command(name="stage")
def autoharness_stage_cmd(
    action: str = typer.Argument(
        ..., help="Action: create, update, patch, remove_file, delete."
    ),
    name: str = typer.Argument(..., help="Skill name (lowercase, hyphenated)."),
    layer: str = typer.Option(
        "project", "--layer", "-l", help="Layer: project or global."
    ),
    body: str | None = typer.Option(
        None, "--body", help="Full Markdown body including YAML frontmatter."
    ),
    old_string: str | None = typer.Option(
        None, "--old", help="Exact string to replace (for patch)."
    ),
    new_string: str | None = typer.Option(
        None, "--new", help="Replacement string (for patch)."
    ),
    reason: str = typer.Option(
        "", "--reason", "-r", help="Why this mutation is needed."
    ),
    evidence: str = typer.Option(
        "", "--evidence", "-e", help="Concrete failure/runbook evidence."
    ),
    absorbed_into: str | None = typer.Option(
        None, "--absorbed-into", help="Surviving umbrella skill (for delete)."
    ),
    run_id: str = typer.Option(
        "interactive", "--run-id", help="Target intent queue run ID."
    ),
) -> None:
    """Stage a skill mutation proposal into the intent queue."""
    from buddhi.scripts.autoharness.intent_queue import append_intent
    from buddhi.scripts.autoharness.models import SkillIntent

    if action not in ("create", "update", "patch", "remove_file", "delete"):
        err_console.print(f"[red]error:[/red] invalid action '{action}'.")
        raise typer.Exit(code=1)

    intent = SkillIntent(
        action=action,  # type: ignore[arg-type]
        name=name,
        layer=layer if layer in ("project", "global") else "project",  # type: ignore[arg-type]
        body=body,
        old_string=old_string,
        new_string=new_string,
        reason=reason,
        evidence=evidence,
        absorbed_into=absorbed_into,
    )
    append_intent(intent, run_id=run_id)
    console.print(
        f"[green]done[/green] staged intent '[bold]{action} {name}[/bold]' in queue [cyan]{run_id}[/cyan]."
    )


@autoharness_app.command(name="promote")
def autoharness_promote_cmd(
    layer: str = typer.Option(
        "project", "--layer", "-l", help="Layer: project or global."
    ),
    run_id: str = typer.Option(
        "interactive", "--run-id", help="Target intent queue run ID."
    ),
    json_mode: bool = typer.Option(
        False, "--json", help="Output run account in JSON format."
    ),
) -> None:
    """Drain queued intents, validate through 6 gates, and land approved skills atomically."""
    from buddhi.scripts.autoharness.promoter import drain_and_promote

    account = drain_and_promote(layer=layer, run_id=run_id)
    if json_mode:
        data = {
            "run_id": account.run_id,
            "timestamp": account.timestamp,
            "landed": account.landed,
            "rejected": account.rejected,
            "spawn_error": account.spawn_error,
        }
        console.print(json.dumps(data, indent=2), markup=False, highlight=False)
    else:
        console.print(
            f"[bold cyan]AutoHarness Promotion Run '{account.run_id}'[/bold cyan] ({account.timestamp})"
        )
        if account.landed:
            console.print(
                f"[bold green]Landed ({len(account.landed)}):[/bold green] {', '.join(account.landed)}"
            )
        else:
            console.print("[dim]Landed: none[/dim]")

        if account.rejected:
            err_console.print(
                f"[bold red]Rejected ({len(account.rejected)}):[/bold red]"
            )
            for r in account.rejected:
                err_console.print(
                    f"  - [bold]{r.get('name')}[/bold] ({r.get('gate', 'unknown')}): {r.get('reason')}"
                )
        else:
            console.print("[dim]Rejected: none[/dim]")


@autoharness_app.command(name="validate")
def autoharness_validate_cmd(
    skill_path: Annotated[
        Path, typer.Argument(help="Path to skill directory or SKILL.md file.")
    ],
) -> None:
    """Validate a skill against the 6 deterministic AutoHarness admission gates."""
    from buddhi.scripts.autoharness.models import SkillIntent
    from buddhi.scripts.autoharness.sidecar import is_agent_created
    from buddhi.scripts.autoharness.validate import validate_skill_candidate

    target_dir = skill_path if skill_path.is_dir() else skill_path.parent
    skill_file = target_dir / "SKILL.md"
    if not skill_file.is_file():
        err_console.print(f"[red]error:[/red] cannot find SKILL.md at {target_dir}")
        raise typer.Exit(code=1)

    body = skill_file.read_text(encoding="utf-8")
    intent = SkillIntent(
        action="update",
        name=target_dir.name,
        layer="project",
        body=body,
        reason="Manual validation",
        evidence="Manual validation",
    )
    agents_dir = target_dir.parent.parent
    val_res = validate_skill_candidate(
        intent=intent,
        assembled_body=body,
        target_is_agent_created=is_agent_created(target_dir),
        target_exists=True,
        layer_root=agents_dir,
    )

    if val_res.valid:
        console.print(
            f"[bold green]pass:[/bold green] skill '{target_dir.name}' passes all 6 admission gates."
        )
        raise typer.Exit(code=0)
    else:
        err_console.print(
            f"[bold red]fail:[/bold red] skill '{target_dir.name}' has {len(val_res.findings)} gate violation(s):"
        )
        for f in val_res.findings:
            err_console.print(f"  - [{f.gate}] {f.code}: {f.message}")
        raise typer.Exit(code=1)


@autoharness_app.command(name="check-links")
def autoharness_check_links_cmd(
    root: Annotated[
        Path | None,
        typer.Argument(help="Root directory to scan for markdown links."),
    ] = None,
) -> None:
    """Scan markdown files for broken relative links (skipping .archive/)."""
    from buddhi.scripts.autoharness.check_doc_links import check_markdown_links

    scan_root = root if root is not None else Path(".")
    broken = check_markdown_links(scan_root.resolve())
    if not broken:
        console.print(
            "[bold green]pass:[/bold green] all relative markdown links are valid."
        )
        raise typer.Exit(code=0)
    else:
        err_console.print(
            f"[bold red]fail:[/bold red] found {len(broken)} broken relative markdown link(s):"
        )
        for b in broken:
            err_console.print(f"  {b['source_file']}:{b['line']} -> {b['target']}")
        raise typer.Exit(code=1)


@autoharness_app.command(name="capture")
def autoharness_capture_cmd(
    transcript: Annotated[Path, typer.Argument(help="Path to transcript.jsonl file.")],
    offset: Annotated[
        int, typer.Option("--offset", help="Byte offset to start slicing.")
    ] = 0,
    out_dir: Annotated[
        Path | None,
        typer.Option("--out-dir", "-o", help="Output directory for episode bundle."),
    ] = None,
) -> None:
    """Slice and redact session transcript into a bounded episode bundle."""
    from buddhi.scripts.autoharness.capture import (
        build_prior_digest,
        slice_transcript_window,
    )

    if not transcript.is_file():
        err_console.print(f"[red]error:[/red] transcript not found at {transcript}")
        raise typer.Exit(code=1)

    window, new_offset = slice_transcript_window(transcript, offset=offset)
    digest = build_prior_digest(transcript, end_offset=offset)

    target_out_dir = out_dir if out_dir is not None else Path(".")
    target_out_dir.mkdir(parents=True, exist_ok=True)
    (target_out_dir / "episode.md").write_text(window, encoding="utf-8")
    (target_out_dir / "digest.md").write_text(digest, encoding="utf-8")

    console.print(
        f"[green]done[/green] sliced episode ({len(window)} bytes, new offset {new_offset}) into {target_out_dir}"
    )


@autoharness_app.command(name="curate")
def autoharness_curate_cmd(
    layer: Annotated[
        str, typer.Option("--layer", "-l", help="Layer: project or global.")
    ] = "project",
    out_dir: Annotated[
        Path | None,
        typer.Option("--out-dir", "-o", help="Output directory for snapshot tarball."),
    ] = None,
) -> None:
    """Create a rotating pre-curation .tar.gz snapshot of active skills."""
    import tarfile
    import time

    from buddhi.scripts.autoharness.config import get_snapshot_keep
    from buddhi.scripts.autoharness.layer import (
        resolve_autoharness_dir,
        resolve_skills_dir,
    )

    skills_dir = resolve_skills_dir(layer)
    if not skills_dir.is_dir():
        err_console.print(
            f"[red]error:[/red] skills directory not found at {skills_dir}"
        )
        raise typer.Exit(code=1)

    autoharness_dir = resolve_autoharness_dir(layer)
    snapshots_dir = out_dir or (autoharness_dir / "snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    timestamp = int(time.time())
    tar_path = snapshots_dir / f"snapshot-{timestamp}.tar.gz"

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(skills_dir, arcname="skills")

    console.print(f"[green]done[/green] created snapshot [cyan]{tar_path}[/cyan]")

    # Rotate old snapshots keeping SNAPSHOT_KEEP
    keep_limit = get_snapshot_keep()
    existing = sorted(
        snapshots_dir.glob("snapshot-*.tar.gz"), key=lambda p: p.stat().st_mtime
    )
    if len(existing) > keep_limit:
        for old_tar in existing[:-keep_limit]:
            try:
                old_tar.unlink()
            except OSError:
                pass


# ============================================================================
# RTK (Token-saving command output filter) CLI
# ============================================================================

rtk_app = typer.Typer(
    name="rtk",
    help="Token-saving command output filter and proxy.",
    invoke_without_command=True,
    no_args_is_help=True,
)
scripts_app.add_typer(rtk_app, name="rtk")


@rtk_app.command(
    name="run",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def rtk_run_cmd(
    ctx: typer.Context,
    raw: bool = typer.Option(
        False, "--raw", help="Bypass filtering and print raw output."
    ),
    generic: bool = typer.Option(
        False, "--generic", help="Force generic fallback filter."
    ),
) -> None:
    """Execute a command, compress output to save LLM tokens, and preserve exit code."""
    from buddhi.scripts.rtk.runner import run_command_filtered

    cmd_args = ctx.args
    if not cmd_args:
        err_console.print(
            "[red]error:[/red] no command specified to execute. Use: buddhi scripts rtk run -- <command>"
        )
        raise typer.Exit(code=1)

    result = run_command_filtered(
        cmd_args=cmd_args,
        force_generic=generic,
    )

    if raw:
        output = result.raw_output
    else:
        output = result.filtered_output

    if output:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
        sys.stdout.flush()

    if result.exit_code != 0 and result.raw_log_path:
        typer.echo(f"[rtk: full raw output saved to {result.raw_log_path}]", err=True)

    raise typer.Exit(code=result.exit_code)


@rtk_app.command(
    name="rewrite",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def rtk_rewrite_cmd(
    ctx: typer.Context,
    json_mode: bool = typer.Option(
        False, "--json", help="Output rewrite decision as JSON."
    ),
) -> None:
    """Evaluate whether a command would be rewritten by the RTK hook."""
    from buddhi.scripts.rtk.rewrite import evaluate_rewrite

    cmd_args = ctx.args
    if not cmd_args:
        err_console.print("[red]error:[/red] no command specified to evaluate.")
        raise typer.Exit(code=1)

    cmd_str = " ".join(cmd_args)
    decision = evaluate_rewrite(cmd_str)

    if json_mode:
        import json

        data = {
            "action": decision.action,
            "reason": decision.reason,
            "original": decision.original_command,
            "rewritten": decision.rewritten_command,
        }
        console.print(json.dumps(data, indent=2), markup=False, highlight=False)
    else:
        if decision.action == "rewrite":
            console.print(decision.rewritten_command)
        else:
            console.print(f"[dim]no rewrite ({decision.reason}): {cmd_str}[/dim]")

    if decision.action != "rewrite":
        raise typer.Exit(code=1)


@rtk_app.command(name="gain")
def rtk_gain_cmd(
    json_mode: bool = typer.Option(
        False, "--json", help="Output token savings summary as JSON."
    ),
) -> None:
    """Display estimated token savings achieved through RTK output filtering."""
    from rich.table import Table

    from buddhi.scripts.rtk.tracking import aggregate_savings

    summary = aggregate_savings()

    if json_mode:
        import json

        data = {
            "total_runs": summary.total_runs,
            "total_raw_tokens": summary.total_raw_tokens,
            "total_filtered_tokens": summary.total_filtered_tokens,
            "total_saved_tokens": summary.total_saved_tokens,
            "savings_percentage": summary.savings_percentage,
            "by_command": summary.by_command,
        }
        console.print(json.dumps(data, indent=2), markup=False, highlight=False)
        return

    if summary.total_runs == 0:
        console.print(
            "[dim]No RTK runs recorded yet. Run commands with 'buddhi scripts rtk run -- <cmd>'[/dim]"
        )
        return

    table = Table(title="RTK Token Savings Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="bold green")

    table.add_row("Total Commands Filtered", str(summary.total_runs))
    table.add_row("Raw Tokens (Est.)", f"{summary.total_raw_tokens:,}")
    table.add_row("Tokens After Filtering (Est.)", f"{summary.total_filtered_tokens:,}")
    table.add_row("Tokens Saved", f"{summary.total_saved_tokens:,}")
    table.add_row("Overall Reduction", f"{summary.savings_percentage}%")

    console.print(table)

    if summary.by_command:
        breakdown_table = Table(title="Savings by Command")
        breakdown_table.add_column("Command / Filter", style="cyan")
        breakdown_table.add_column("Runs", justify="right")
        breakdown_table.add_column("Raw Tokens", justify="right")
        breakdown_table.add_column("Filtered", justify="right")
        breakdown_table.add_column("Saved", style="bold green", justify="right")
        breakdown_table.add_column("Reduction", justify="right")

        for cmd, stats in summary.by_command.items():
            raw_t = stats["raw"]
            saved_t = stats["saved"]
            pct = round((saved_t / raw_t * 100.0), 1) if raw_t > 0 else 0.0
            breakdown_table.add_row(
                cmd,
                str(stats["runs"]),
                f"{raw_t:,}",
                f"{stats['filtered']:,}",
                f"{saved_t:,}",
                f"{pct}%",
            )

        console.print(breakdown_table)


@rtk_app.command(name="trust")
def rtk_trust_cmd(
    filter_path: Annotated[
        Path | None,
        typer.Argument(
            help="Path to project filter file to trust. Omit to trust all in .buddhi/rtk/filters/."
        ),
    ] = None,
) -> None:
    """Approve and pin the SHA-256 hash of project-local filter files."""
    from buddhi.scripts.rtk.trust import DEFAULT_PROJECT_FILTERS_DIR, trust_filter_file

    target_files: list[Path] = []
    if filter_path is not None:
        if not filter_path.is_file():
            err_console.print(f"[red]error:[/red] file not found: {filter_path}")
            raise typer.Exit(code=1)
        target_files.append(filter_path)
    else:
        if DEFAULT_PROJECT_FILTERS_DIR.is_dir():
            target_files.extend(sorted(DEFAULT_PROJECT_FILTERS_DIR.glob("*.json")))

    if not target_files:
        console.print("[dim]No project filter files found to trust.[/dim]")
        return

    for p in target_files:
        h = trust_filter_file(p)
        console.print(f"[green]trusted:[/green] {p.name} (sha256: {h[:12]}...)")


filters_app = typer.Typer(
    name="filters",
    help="Inspect and test RTK command output filters.",
    invoke_without_command=True,
    no_args_is_help=True,
)
rtk_app.add_typer(filters_app, name="filters")


@filters_app.command(name="list")
def rtk_filters_list_cmd(
    json_mode: bool = typer.Option(
        False, "--json", help="Output filter catalog as JSON."
    ),
) -> None:
    """List all available builtin and project-local RTK filters."""
    from rich.table import Table

    from buddhi.scripts.rtk.filters import load_builtin_filters
    from buddhi.scripts.rtk.trust import DEFAULT_PROJECT_FILTERS_DIR, is_filter_trusted

    builtin = load_builtin_filters()
    project_files = (
        sorted(DEFAULT_PROJECT_FILTERS_DIR.glob("*.json"))
        if DEFAULT_PROJECT_FILTERS_DIR.is_dir()
        else []
    )

    if json_mode:
        import json

        data = {
            "builtin": [f.to_dict() for f in builtin],
            "project": [
                {
                    "file": str(p),
                    "name": p.stem,
                    "trusted": is_filter_trusted(p),
                }
                for p in project_files
            ],
        }
        console.print(json.dumps(data, indent=2), markup=False, highlight=False)
        return

    table = Table(
        title=f"RTK Filters ({len(builtin)} Builtin, {len(project_files)} Project)"
    )
    table.add_column("Type", style="dim")
    table.add_column("Name", style="bold cyan")
    table.add_column("Command Match", style="yellow")
    table.add_column("Description")
    table.add_column("Status / License", style="green")

    for f in builtin:
        table.add_row(
            "builtin", f.name, f.match_command[:30], f.description[:40], f.license
        )

    for p in project_files:
        trusted = is_filter_trusted(p)
        status_style = "[green]trusted[/green]" if trusted else "[red]untrusted[/red]"
        table.add_row(
            "project", p.name, "(custom)", "Project-local filter", status_style
        )

    console.print(table)


@filters_app.command(name="test")
def rtk_filters_test_cmd(
    filter_name: Annotated[str, typer.Argument(help="Name of the filter to test.")],
) -> None:
    """Run embedded test cases for a specific RTK filter."""
    from buddhi.scripts.rtk.engine import apply_filter
    from buddhi.scripts.rtk.filters import load_builtin_filters

    filters = load_builtin_filters()
    target = next((f for f in filters if f.name == filter_name), None)

    if target is None:
        err_console.print(f"[red]error:[/red] filter '{filter_name}' not found.")
        raise typer.Exit(code=1)

    if not target.tests:
        console.print(f"[dim]Filter '{filter_name}' has no embedded test cases.[/dim]")
        return

    console.print(
        f"[bold cyan]Running {len(target.tests)} test(s) for filter '{filter_name}':[/bold cyan]"
    )
    failed = 0
    for idx, t in enumerate(target.tests, 1):
        actual = apply_filter(t.input, target)
        norm_actual = actual.strip().replace("\r\n", "\n")
        norm_exp = t.expected.strip().replace("\r\n", "\n")
        if norm_actual == norm_exp:
            console.print(f"  [green]PASS[/green] ({idx}) {t.name}")
        else:
            console.print(f"  [red]FAIL[/red] ({idx}) {t.name}")
            console.print(f"    Expected: {norm_exp!r}")
            console.print(f"    Got:      {norm_actual!r}")
            failed += 1

    if failed > 0:
        raise typer.Exit(code=1)
    console.print(f"[bold green]All {len(target.tests)} test(s) passed.[/bold green]")
