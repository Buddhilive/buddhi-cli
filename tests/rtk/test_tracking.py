from __future__ import annotations

from pathlib import Path

from buddhi.scripts.rtk.tracking import (
    RunRecord,
    aggregate_savings,
    record_run,
    redact_command_line,
)


def test_redact_command_line() -> None:
    # Retains program name and safe subcommands, redacts arguments like passwords/tokens/flags
    redacted = redact_command_line("git status")
    assert redacted == "git status"

    redacted_secret = redact_command_line(
        "curl -H 'Authorization: Bearer mysecret' https://api.com"
    )
    assert "mysecret" not in redacted_secret
    assert "curl" in redacted_secret


def test_record_and_aggregate_savings(tmp_path: Path) -> None:
    ledger_path = tmp_path / "runs.jsonl"

    rec1 = RunRecord(
        timestamp=1000,
        command="git status",
        filter_name="git-status",
        raw_tokens=200,
        filtered_tokens=50,
        saved_tokens=150,
        exit_code=0,
    )
    rec2 = RunRecord(
        timestamp=1001,
        command="pytest",
        filter_name="pytest",
        raw_tokens=1000,
        filtered_tokens=200,
        saved_tokens=800,
        exit_code=0,
    )

    record_run(rec1, ledger_path=ledger_path)
    record_run(rec2, ledger_path=ledger_path)

    summary = aggregate_savings(ledger_path=ledger_path)
    assert summary.total_runs == 2
    assert summary.total_raw_tokens == 1200
    assert summary.total_filtered_tokens == 250
    assert summary.total_saved_tokens == 950
    assert summary.savings_percentage > 70.0
