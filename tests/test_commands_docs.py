from __future__ import annotations

import re
from pathlib import Path

from typer.testing import CliRunner

from buddhi.cli import app
from buddhi.docgen.site import is_port_available
from buddhi.scripts.contrast import run_contrast_check

runner = CliRunner()


def test_docs_build_generates_site_and_search_index(tmp_path: Path) -> None:
    # Setup dummy project with a python file and docs dir
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "calc.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8"
    )

    docs_dir = tmp_path / ".buddhi" / "docs"
    docs_dir.mkdir(parents=True)
    (docs_dir / "index.md").write_text(
        "---\ntype: Concept\ntitle: Home\ndescription: Welcome\n---\n# Home\nHello world.\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["docs", "build", str(tmp_path), "--no-graph-refresh"])
    assert result.exit_code == 0
    assert "compiled documentation site" in result.output

    site_dir = tmp_path / ".buddhi" / "site"
    assert (site_dir / "index.html").is_file()
    assert (site_dir / "search-index.json").is_file()

    html = (site_dir / "index.html").read_text(encoding="utf-8")
    assert "Home" in html
    assert "Hello world." in html


def test_docs_plan_command_executes_successfully(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def run() -> None:\n    pass\n", encoding="utf-8")

    result = runner.invoke(app, ["docs", "plan", str(tmp_path)])
    assert result.exit_code == 0
    assert "planned docs for" in result.output
    assert (tmp_path / ".buddhi" / "docs-plan.json").is_file()


def test_is_port_available() -> None:
    # A standard high port should typically be testable
    avail = is_port_available("127.0.0.1", 62345)
    assert isinstance(avail, bool)


def test_theme_a11y_and_contrast_gates() -> None:
    """Validate theme color contrast floors and landmark accessibility (T017)."""
    # 1. Text contrast floors (WCAG 2.2 AA Standard Profile >= 4.5:1)
    light_res = run_contrast_check("#0f172a", "#ffffff")
    assert light_res.normal_pass is True
    assert light_res.ratio >= 4.5

    dark_res = run_contrast_check("#f1f5f9", "#0b0f19")
    assert dark_res.normal_pass is True
    assert dark_res.ratio >= 4.5

    # 2. Template landmark verification
    theme_dir = Path("src/buddhi/docgen/theme/templates")
    base_html = (theme_dir / "base.html").read_text(encoding="utf-8")
    assert (
        '<a href="#main-content" class="skip-link">Skip to main content</a>'
        in base_html
    )
    assert "<header" in base_html
    assert "<nav" in base_html
    assert '<main id="main-content"' in base_html
    assert "<footer" in base_html


def test_compiled_site_link_integrity_crawler(tmp_path: Path) -> None:
    """Crawler asserting 100% of internal links resolve to valid destinations (SC-002, T018)."""
    docs_dir = tmp_path / ".buddhi" / "docs"
    docs_dir.mkdir(parents=True)
    guides_dir = docs_dir / "guides"
    guides_dir.mkdir()

    (docs_dir / "index.md").write_text(
        "---\ntype: Concept\ntitle: Home\n---\n# Home\nSee [Report](architecture-report.md) and [Guide](guides/core.md).\n",
        encoding="utf-8",
    )
    (docs_dir / "architecture-report.md").write_text(
        "---\ntype: Concept\ntitle: Report\n---\n# Report\nBack to [Home](index.md).\n",
        encoding="utf-8",
    )
    (guides_dir / "core.md").write_text(
        "---\ntype: Concept\ntitle: Core Guide\n---\n# Core\nBack to [Home](../index.md).\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["docs", "build", str(tmp_path), "--no-graph-refresh"])
    assert result.exit_code == 0

    site_dir = tmp_path / ".buddhi" / "site"
    html_files = list(site_dir.rglob("*.html"))
    assert len(html_files) >= 3

    # Crawl all href attributes
    href_re = re.compile(r'href=["\']([^"\']+)["\']')
    broken_links: list[str] = []

    for html_file in html_files:
        content = html_file.read_text(encoding="utf-8")
        for href in href_re.findall(content):
            # Skip external links, fragments, mailto
            if href.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
                continue

            # Strip query params and fragment
            clean_target = href.split("?")[0].split("#")[0]
            if not clean_target:
                continue

            target_path = (html_file.parent / clean_target).resolve()
            if not target_path.exists():
                broken_links.append(
                    f"{html_file.relative_to(site_dir)} -> {href} (missing: {target_path})"
                )

    assert len(broken_links) == 0, f"Found broken internal links: {broken_links}"
