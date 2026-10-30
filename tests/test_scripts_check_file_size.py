from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.scripts.check_file_size import (
    format_tokens,
    is_source_file,
    selftest,
)

runner = CliRunner()


def test_is_source_file():
    assert is_source_file("foo.py")
    assert is_source_file("src/lib.rs")
    assert is_source_file("app.ts")
    assert not is_source_file("README.md")
    assert not is_source_file("data.json")
    assert not is_source_file("icon.svg")


def test_format_tokens():
    assert format_tokens(400) == "~100 tokens"
    assert format_tokens(32000) == "~8,000 tokens"


def test_selftest():
    code, msg = selftest()
    assert code == 0
    assert "OK" in msg


def test_cli_selftest():
    result = runner.invoke(app, ["scripts", "check-file-size", "--selftest"])
    assert result.exit_code == 0
    assert "selftest: check-file-size OK" in result.stdout


def test_cli_no_args_shows_usage():
    result = runner.invoke(app, ["scripts", "check-file-size"])
    assert result.exit_code == 2
    assert (
        "usage: buddhi scripts check-file-size" in result.stderr
        or "usage: buddhi scripts check-file-size" in result.stdout
    )
