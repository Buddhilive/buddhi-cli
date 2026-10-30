from __future__ import annotations

import sys

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_rtk_run_basic_command() -> None:
    result = runner.invoke(
        app,
        [
            "scripts",
            "rtk",
            "run",
            "--",
            sys.executable,
            "-c",
            "print('hello from cli')",
        ],
    )
    assert result.exit_code == 0
    assert "hello from cli" in result.output


def test_rtk_run_no_args() -> None:
    result = runner.invoke(app, ["scripts", "rtk", "run"])
    assert result.exit_code != 0
    assert "no command specified" in (result.output + (result.stderr or "")).lower()


def test_rtk_run_failure_shows_raw_log_notice() -> None:
    result = runner.invoke(
        app,
        [
            "scripts",
            "rtk",
            "run",
            "--",
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('failed!'); sys.exit(2)",
        ],
    )
    assert result.exit_code == 2
    combined = (result.stdout or "") + (result.stderr or "")
    assert "failed!" in combined
    assert "full raw output saved" in combined.lower()


def test_rtk_rewrite_cli() -> None:
    res = runner.invoke(app, ["scripts", "rtk", "rewrite", "git", "status"])
    assert res.exit_code == 0
    assert "buddhi scripts rtk run -- git status" in res.output

    res_skip = runner.invoke(app, ["scripts", "rtk", "rewrite", "mkdir", "xyz"])
    assert res_skip.exit_code != 0
    assert "no rewrite" in res_skip.output


def test_rtk_gain_cli() -> None:
    res = runner.invoke(app, ["scripts", "rtk", "gain", "--json"])
    assert res.exit_code == 0
    assert "total_runs" in res.output


def test_rtk_filters_list_cli() -> None:
    res = runner.invoke(app, ["scripts", "rtk", "filters", "list", "--json"])
    assert res.exit_code == 0
    assert "builtin" in res.output
    assert "git-status" in res.output


def test_rtk_filters_test_cli() -> None:
    res = runner.invoke(app, ["scripts", "rtk", "filters", "test", "git-status"])
    assert res.exit_code == 0
    assert "All" in res.output and "passed" in res.output
