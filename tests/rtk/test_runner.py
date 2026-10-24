from __future__ import annotations

import sys
from pathlib import Path

from buddhi.scripts.rtk.runner import run_command_filtered


def test_runner_preserves_exit_code_zero(tmp_path: Path) -> None:
    # Run a simple python one-liner that exits 0
    cmd = [sys.executable, "-c", "print('hello from runner')"]
    result = run_command_filtered(cmd, raw_dir=tmp_path)
    assert result.exit_code == 0
    assert "hello from runner" in result.filtered_output


def test_runner_preserves_nonzero_exit_code_and_creates_tee_log(tmp_path: Path) -> None:
    # Run a python one-liner that exits with 42 and prints to stderr
    cmd = [
        sys.executable,
        "-c",
        "import sys; sys.stdout.write('some info\\n'); sys.stderr.write('CRITICAL error!\\n'); sys.exit(42)",
    ]
    result = run_command_filtered(cmd, raw_dir=tmp_path)
    assert result.exit_code == 42
    assert "CRITICAL error!" in result.filtered_output
    assert result.raw_log_path is not None
    assert Path(result.raw_log_path).exists()

    content = Path(result.raw_log_path).read_text(encoding="utf-8")
    assert "CRITICAL error!" in content


def test_runner_fail_open_on_invalid_command(tmp_path: Path) -> None:
    # Run a command that does not exist
    cmd = ["non_existent_command_12345_xyz"]
    result = run_command_filtered(cmd, raw_dir=tmp_path)
    assert result.exit_code != 0
    out_lower = result.filtered_output.lower()
    assert (
        "not found" in out_lower
        or "error" in out_lower
        or "not recognized" in out_lower
    )
