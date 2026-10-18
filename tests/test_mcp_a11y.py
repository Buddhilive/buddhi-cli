from __future__ import annotations

import json
from pathlib import Path

from buddhi.mcp.tools.a11y import execute_verify_a11y
from buddhi.mcp.tools.contrast import execute_check_contrast


def test_mcp_execute_check_contrast_pair() -> None:
    res = execute_check_contrast(color_a="#000000", color_b="#ffffff")
    assert "21.00:1" in res

    # Multi-pair mode
    res_multi = execute_check_contrast(bg="#ffffff", fg=["#000000", "#767676"])
    assert "background: #ffffff" in res_multi
    assert "REPORT.md:" in res_multi


def test_mcp_execute_check_contrast_css(tmp_path: Path) -> None:
    css_file = tmp_path / "test.css"
    css_file.write_text(
        "body { color: #000000; background: #ffffff; }", encoding="utf-8"
    )
    res = execute_check_contrast(css_path=str(css_file))
    assert "TRIAGE" in res
    assert "distinct colors" in res


def test_mcp_execute_verify_a11y_json(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "bad.jsx").write_text(
        "<div onClick={handler}>Click</div>", encoding="utf-8"
    )

    # Missing REPORT.md
    res_raw = execute_verify_a11y(project_dir=str(tmp_path), as_json=True)
    data = json.loads(res_raw)
    assert data["exit_code"] == 1
    assert any(err["check"] == "artifacts" for err in data["errors"])
