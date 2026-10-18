from pathlib import Path

import pytest
from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.scripts.contrast import (
    composite,
    contrast_ratio,
    parse_color,
    parse_color_extended,
    parse_hex,
    run_contrast_check,
    run_css_mode,
    run_pair_mode,
    selftest,
)

runner = CliRunner()


def test_parse_hex_valid() -> None:
    assert parse_hex("#FFFFFF") == (255, 255, 255)
    assert parse_hex("FFFFFF") == (255, 255, 255)
    assert parse_hex("#000") == (0, 0, 0)
    assert parse_hex("000") == (0, 0, 0)
    assert parse_hex("#123456") == (0x12, 0x34, 0x56)


def test_parse_hex_invalid() -> None:
    with pytest.raises(ValueError, match="expected a hex color"):
        parse_hex("invalid")
    with pytest.raises(ValueError, match="expected a hex color"):
        parse_hex("#12")
    with pytest.raises(ValueError, match="expected a hex color"):
        parse_hex("#12345678")


def test_parse_color_named() -> None:
    assert parse_color("black") == (0, 0, 0)
    assert parse_color("white") == (255, 255, 255)
    assert parse_color("#FFF") == (255, 255, 255)


def test_contrast_ratio_extremes() -> None:
    black = (0, 0, 0)
    white = (255, 255, 255)
    assert round(contrast_ratio(white, black), 2) == 21.0
    assert round(contrast_ratio(white, white), 2) == 1.0


def test_contrast_check_results() -> None:
    result = run_contrast_check("#FFFFFF", "#777777")
    assert round(result.ratio, 2) == 4.48
    assert result.normal_pass is False
    assert result.large_pass is True
    assert result.exit_code == 1

    result_pass = run_contrast_check("#000000", "#FFFFFF")
    assert round(result_pass.ratio, 2) == 21.0
    assert result_pass.normal_pass is True
    assert result_pass.large_pass is True
    assert result_pass.exit_code == 0


def test_contrast_check_profiles() -> None:
    # 4.5:1 passes standard text, fails shield text (floor: 7.0:1)
    res_std = run_contrast_check("#000000", "#767676", profile="standard")
    assert res_std.normal_pass is True
    assert res_std.exit_code == 0

    res_shield = run_contrast_check("#000000", "#767676", profile="shield")
    assert res_shield.normal_pass is False
    assert res_shield.exit_code == 1


def test_alpha_compositing() -> None:
    c = parse_color_extended("rgba(0, 0, 0, 0.5)")
    assert c is not None
    # 50% black over pure white produces mid-gray (128, 128, 128)
    blended = composite(c, (255, 255, 255))
    assert blended == (128, 128, 128)


def test_run_pair_mode() -> None:
    code, msg = run_pair_mode("#ffffff", ["#000000", "#767676"])
    assert code == 0
    assert "background: #ffffff" in msg
    assert "#000000" in msg
    assert "REPORT.md:" in msg

    # Failing pair
    code_fail, msg_fail = run_pair_mode("#ffffff", ["#eeeeee"])
    assert code_fail == 1
    assert "FAIL" in msg_fail


def test_run_css_mode(tmp_path: Path) -> None:
    css_file = tmp_path / "styles.css"
    css_file.write_text(
        """
        :root {
            --bg: #ffffff;
            --fg: #000000;
            --muted: #eeeeee;
        }
        body {
            background-color: var(--bg);
            color: var(--fg);
        }
        """,
        encoding="utf-8",
    )
    _code, msg = run_css_mode(css_file, page_bg_tok="#ffffff")
    assert "TRIAGE" in msg
    assert "distinct colors" in msg


def test_selftest_passes() -> None:
    code, msg = selftest()
    assert code == 0
    assert "reference pairs" in msg
    assert "OK" in msg


def test_cli_contrast_commands(tmp_path: Path) -> None:
    # 1. Positional pair backward compatibility
    res_pos = runner.invoke(app, ["scripts", "contrast", "#000000", "#ffffff"])
    assert res_pos.exit_code == 0
    assert "21.00:1" in res_pos.output

    # 2. Multi-pair mode with --bg and --fg
    res_pair = runner.invoke(
        app,
        [
            "scripts",
            "contrast",
            "--bg",
            "#ffffff",
            "--fg",
            "#000000",
            "--fg",
            "#111111",
        ],
    )
    assert res_pair.exit_code == 0
    assert "background: #ffffff" in res_pair.output

    # 3. Selftest flag
    res_self = runner.invoke(app, ["scripts", "contrast", "--selftest"])
    assert res_self.exit_code == 0
    assert "reference pairs" in res_self.output
