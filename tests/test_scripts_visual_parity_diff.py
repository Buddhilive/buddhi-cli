from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.scripts.visual_parity_diff import (
    decode_png,
    encode_png_rgba,
    run_visual_parity_diff,
    selftest,
)

runner = CliRunner()


def test_png_roundtrip():
    width, height = 2, 2
    raw = bytearray(
        [
            255,
            0,
            0,
            255,  # Red
            0,
            255,
            0,
            255,  # Green
            0,
            0,
            255,
            255,  # Blue
            255,
            255,
            255,
            255,  # White
        ]
    )
    encoded = encode_png_rgba(width, height, raw)
    decoded = decode_png(encoded)
    assert decoded.width == width
    assert decoded.height == height
    assert decoded.data == raw


def test_selftest():
    code, msg = selftest()
    assert code == 0
    assert "OK" in msg


def test_cli_selftest():
    result = runner.invoke(app, ["scripts", "visual-parity-diff", "--selftest"])
    assert result.exit_code == 0
    assert "selftest: visual-parity-diff OK" in result.stdout


def test_solo_and_pair_diff_runs(tmp_path: Path):
    # Create two 4x4 images
    ref_dir = tmp_path / "reference"
    cand_dir = tmp_path / "candidate"
    ref_dir.mkdir()
    cand_dir.mkdir()

    raw1 = bytearray([128, 128, 128, 255] * 16)
    raw2 = bytearray([130, 130, 130, 255] * 16)

    (ref_dir / "shot.png").write_bytes(encode_png_rgba(4, 4, raw1))
    (cand_dir / "shot.png").write_bytes(encode_png_rgba(4, 4, raw2))

    # Test solo mode
    out_dir = tmp_path / "diff_out"
    code, solo_report = run_visual_parity_diff(candidate_dir=cand_dir, out_dir=out_dir)
    assert code == 0
    assert solo_report["imageCount"] == 1
    assert (out_dir / "scene-metrics.json").is_file()

    # Test pair mode
    code, pair_report = run_visual_parity_diff(
        candidate_dir=cand_dir, reference_dir=ref_dir, out_dir=out_dir
    )
    assert code == 0
    assert pair_report["pairCount"] == 1
    assert (out_dir / "visual-parity-diff.json").is_file()
    assert (out_dir / "shot-side-by-side.png").is_file()
