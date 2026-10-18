from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from buddhi.scripts.verify_a11y.antipatterns import (
    apply_registers,
    check_aria_soup,
    check_half_climbed,
    check_orphaned_aria,
    check_placeholder_labels,
    check_source_antipatterns,
)
from buddhi.scripts.verify_a11y.artifacts import (
    check_exceptions,
    check_gitignore,
    check_report_freshness,
    check_report_gate,
    check_report_independence,
    check_report_standard_version,
    check_report_status,
    resolve_artifacts,
)
from buddhi.scripts.verify_a11y.coverage import (
    check_contrast_evidence,
    check_guide_coverage,
)
from buddhi.scripts.verify_a11y.models import (
    GateFinding,
    VerifyA11yResult,
)
from buddhi.scripts.verify_a11y.selftest import run_selftest


def run_checks(
    root: Path,
    src: Path | None = None,
    report_dir: Path | None = None,
    warn_only: bool = False,
) -> VerifyA11yResult:
    findings: list[GateFinding] = []
    src_dir = src or root

    resolved = resolve_artifacts(root, report_dir)
    gate_declared: str | None = None

    if not resolved.report_path:
        findings.append(
            GateFinding(
                "ERROR",
                "artifacts",
                "REPORT.md not found. Release Evidence (A11Y.md §2) requires it before any delivery to an end user — generate it from templates/REPORT.md.",
            )
        )
    else:
        report = resolved.report_path
        check_report_freshness(root, report, src_dir, findings)
        check_report_status(report, findings)
        check_report_independence(report, findings)
        gate_declared = check_report_gate(report, findings)
        check_report_standard_version(report, findings)
        check_contrast_evidence(
            root, report, src_dir, resolved.decisions_path, findings
        )
        check_guide_coverage(root, report, src_dir, findings)

    check_exceptions(resolved.exceptions_path, findings)
    check_gitignore(root, findings)
    check_source_antipatterns(root, src_dir, findings)
    check_placeholder_labels(root, src_dir, findings)
    check_half_climbed(root, src_dir, findings)
    check_aria_soup(root, src_dir, findings)
    check_orphaned_aria(root, src_dir, findings)
    apply_registers(
        root,
        src_dir,
        resolved.exceptions_path,
        resolved.decisions_path,
        findings,
    )

    if gate_declared is not None:
        errors_found = sum(1 for f in findings if f.level == "ERROR")
        if re.search(r"NOT RUN|N[ÃA]O RODOU", gate_declared, re.IGNORECASE):
            findings.append(
                GateFinding(
                    "WARN",
                    "gate-declared",
                    "REPORT.md declares the static gate NOT RUN, but it is running now — record this run's outcome instead.",
                )
            )
        elif re.search(r"\bPASS\b", gate_declared, re.IGNORECASE) and errors_found:
            findings.append(
                GateFinding(
                    "ERROR",
                    "gate-declared",
                    f"REPORT.md declares the static gate PASS, but this run found {errors_found} error(s). Record the real outcome.",
                )
            )

    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]
    registered = [f for f in findings if f.level == "REGISTERED"]

    also = f", {len(registered)} registered" if registered else ""
    verdict = "FAIL" if errors else "PASS"
    today_iso = dt.datetime.now(dt.timezone.utc).date().isoformat()
    summary_line = (
        f"Record in REPORT.md → Static gate (verify-a11y.py): {verdict} "
        f"({len(errors)} error(s), {len(warnings)} warning(s){also}) — run on: {today_iso}"
    )

    out_lines = []
    for f in errors + warnings + registered:
        marker = {"ERROR": "✗", "WARN": "!"}.get(f.level, "·")
        out_lines.append(f"{marker} [{f.check}] {f.message}")

    out_lines.append("")
    if errors:
        out_lines.append(
            f"FAIL — {len(errors)} error(s), {len(warnings)} warning(s){also}."
        )
    elif warnings or registered:
        out_lines.append(f"PASS with {len(warnings)} warning(s){also}.")
    else:
        out_lines.append("PASS — nothing statically detectable is wrong.")
    out_lines.append(
        "This is not a conformance claim: the human checkpoints in REPORT.md are what establish it."
    )
    out_lines.append(summary_line)

    exit_code = 0 if (not errors or warn_only) else 1

    return VerifyA11yResult(
        exit_code=exit_code,
        summary_line=summary_line,
        errors=errors,
        warnings=warnings,
        registered=registered,
        findings=findings,
        output_text="\n".join(out_lines),
    )


def self_test() -> tuple[int, str]:
    return run_selftest(run_checks)
