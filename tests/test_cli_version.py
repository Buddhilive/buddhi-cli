import re

from typer.testing import CliRunner

from buddhi import __version__
from buddhi.cli import app

runner = CliRunner()


def test_version_string_format() -> None:
    assert re.match(r"^\d+\.\d+\.\d+", __version__)


def test_cli_version_flag_long() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "BuddhiAI CLI" in result.output
    assert __version__ in result.output


def test_cli_version_flag_short() -> None:
    result = runner.invoke(app, ["-V"])
    assert result.exit_code == 0
    assert "BuddhiAI CLI" in result.output
    assert __version__ in result.output


def test_cli_version_eager_flag() -> None:
    # When passed with a command like 'generate', eager version flag should print version and exit 0
    result = runner.invoke(app, ["--version", "generate"])
    assert result.exit_code == 0
    assert "BuddhiAI CLI" in result.output
    assert __version__ in result.output
