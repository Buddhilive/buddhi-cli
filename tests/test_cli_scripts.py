from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app

runner = CliRunner()


def test_scripts_no_args_shows_help() -> None:
    result = runner.invoke(app, ["scripts"])
    assert result.exit_code == 0 or result.exit_code == 2
    assert "contrast" in result.output
    assert "antislop-mode" in result.output


def test_contrast_pass() -> None:
    result = runner.invoke(app, ["scripts", "contrast", "#FFFFFF", "#000000"])
    assert result.exit_code == 0
    assert "ratio: 21.00:1" in result.output
    assert "normal text (4.5:1): PASS" in result.output
    assert "large text  (3.0:1): PASS" in result.output


def test_contrast_fail() -> None:
    result = runner.invoke(app, ["scripts", "contrast", "#FFFFFF", "#777777"])
    assert result.exit_code == 1
    assert "normal text (4.5:1): FAIL" in result.output
    assert "large text  (3.0:1): PASS" in result.output


def test_contrast_invalid_args() -> None:
    result = runner.invoke(app, ["scripts", "contrast", "not-a-color"])
    assert result.exit_code == 2

    result2 = runner.invoke(app, ["scripts", "contrast", "bad", "bad2"])
    assert result2.exit_code == 2
    assert "error:" in result2.output


def test_contrast_selftest() -> None:
    result = runner.invoke(app, ["scripts", "contrast", "--selftest"])
    assert result.exit_code == 0
    assert "reference pairs OK" in result.output


def test_antislop_mode_cli(tmp_path: Path, monkeypatch) -> None:
    settings_file = tmp_path / "antislop" / "settings.json"
    monkeypatch.setattr("buddhi.scripts.antislop_mode.settings_path", settings_file)

    res = runner.invoke(app, ["scripts", "antislop-mode"])
    assert res.exit_code == 0
    assert "antislop global mode: ask (default)" in res.output

    res_set = runner.invoke(app, ["scripts", "antislop-mode", "after"])
    assert res_set.exit_code == 0
    assert "antislop global mode: after" in res_set.output

    res_get = runner.invoke(app, ["scripts", "antislop-mode"])
    assert res_get.exit_code == 0
    assert "antislop global mode: after" in res_get.output
