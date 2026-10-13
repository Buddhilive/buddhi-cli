from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.scripts.receipts import selftest

runner = CliRunner()


def test_receipts_selftest():
    code, msg = selftest()
    assert code == 0
    assert "OK" in msg


def test_cli_selftest():
    result = runner.invoke(app, ["scripts", "receipts", "--selftest"])
    assert result.exit_code == 0
    assert "selftest: receipts OK" in result.stdout


def test_supported_claim_passes(tmp_path: Path):
    report_file = tmp_path / "critique.md"
    report_file.write_text(
        """# Visual Critique
Measured contrast ratio is 4.5.
```bash
$ buddhi scripts contrast #000000 #ffffff
contrast ratio: 4.5
```
Verified cleanly.
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scripts", "receipts", str(report_file)])
    assert result.exit_code == 0
    assert "all claims and artifacts verified" in result.stdout


def test_unsupported_claim_fails(tmp_path: Path):
    report_file = tmp_path / "critique.md"
    report_file.write_text(
        """# Visual Critique
Measured contrast ratio is 99.9.
No receipt here.
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scripts", "receipts", str(report_file)])
    assert result.exit_code == 1
    assert "finding" in result.stderr or "finding" in result.stdout


def test_missing_artifact_fails(tmp_path: Path):
    report_file = tmp_path / "critique.md"
    report_file.write_text(
        """# Visual Critique
Check crop image at missing_crop.png.
""",
        encoding="utf-8",
    )
    result = runner.invoke(app, ["scripts", "receipts", str(report_file)])
    assert result.exit_code == 1
    assert "missing artifact" in result.stderr or "missing artifact" in result.stdout
