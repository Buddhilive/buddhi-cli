from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.scripts.verify_a11y import self_test

runner = CliRunner()


def test_verify_a11y_selftest() -> None:
    code, msg = self_test()
    assert code == 0, msg
    assert "self-test: PASS" in msg


def test_verify_a11y_cli_clean_project(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "index.html").write_text(
        '<label for="q">Search</label><input id="q" placeholder="Search"><button>Go</button>',
        encoding="utf-8",
    )
    report_content = """# Report
- **Compliance Status:** ⚠️ CONDITIONAL
- **Verification Independence:** fresh-context — who verified: subagent audit
- **Static gate (`verify-a11y.py`):** PASS — run on: 2026-10-27
- **Standard version:** 2.5.0
- [x] **Text & UI Contrast:** measured
| body | #000000 | #ffffff | 21.00:1 | 4.5:1 | ✅ |
## 3. Behavior and Task Return
- Scenarios run: guide-forms (1/1) · guide-buttons (1/1)
"""
    (tmp_path / "REPORT.md").write_text(report_content, encoding="utf-8")

    result = runner.invoke(
        app, ["scripts", "verify-a11y", str(tmp_path), "--src", "src"]
    )
    assert result.exit_code == 0
    assert "PASS" in result.output


def test_verify_a11y_cli_finds_antipattern(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "bad.jsx").write_text(
        "<div onClick={handler}>Click</div>", encoding="utf-8"
    )
    (tmp_path / "REPORT.md").write_text(
        "# Report\n- **Compliance Status:** PASS\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["scripts", "verify-a11y", str(tmp_path)])
    assert result.exit_code == 1
    assert "clickable-div" in result.output

    # Warn only should exit with 0
    res_warn = runner.invoke(
        app, ["scripts", "verify-a11y", str(tmp_path), "--warn-only"]
    )
    assert res_warn.exit_code == 0
    assert "clickable-div" in res_warn.output
