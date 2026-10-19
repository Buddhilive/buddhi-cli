from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from buddhi.scripts.verify_a11y import run_checks


def execute_verify_a11y(
    project_dir: str = ".",
    src: str | None = None,
    report_dir: str | None = None,
    warn_only: bool = False,
    as_json: bool = False,
) -> str:
    """Run the A11Y.md static gate to verify artifacts, freshness, contrast math, and source anti-patterns."""
    try:
        root_path = Path(project_dir).resolve()
        if not root_path.is_dir():
            return f"Error: project directory not found: {project_dir}"

        src_path = (root_path / src).resolve() if src else root_path
        rep_path = Path(report_dir).resolve() if report_dir else None

        result = run_checks(
            root=root_path,
            src=src_path,
            report_dir=rep_path,
            warn_only=warn_only,
        )

        if as_json:
            payload: dict[str, Any] = {
                "exit_code": result.exit_code,
                "summary": result.summary_line,
                "errors": [
                    {
                        "check": f.check,
                        "level": f.level,
                        "message": f.message,
                        "subject": f.subject,
                    }
                    for f in result.errors
                ],
                "warnings": [
                    {
                        "check": f.check,
                        "level": f.level,
                        "message": f.message,
                        "subject": f.subject,
                    }
                    for f in result.warnings
                ],
                "registered": [
                    {
                        "check": f.check,
                        "level": f.level,
                        "message": f.message,
                        "subject": f.subject,
                    }
                    for f in result.registered
                ],
            }
            return json.dumps(payload, indent=2)

        return result.output_text
    except Exception as exc:  # noqa: BLE001
        return f"Error verifying accessibility: {exc}"
