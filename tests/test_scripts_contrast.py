import pytest

from buddhi.scripts.contrast import (
    contrast_ratio,
    parse_color,
    parse_hex,
    run_contrast_check,
    selftest,
)


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


def test_selftest_passes() -> None:
    code, msg = selftest()
    assert code == 0
    assert "reference pairs OK" in msg
