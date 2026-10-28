import io
from pathlib import Path

from rich.console import Console

from buddhi.ui.banner import ASCII_ART_BANNER, render_banner
from buddhi.ui.formatters import print_init_summary, print_status


def test_ascii_banner_constant_is_valid() -> None:
    assert "BuddhiAI CLI" in ASCII_ART_BANNER or "___" in ASCII_ART_BANNER
    for line in ASCII_ART_BANNER.splitlines():
        # Ensure 7-bit ASCII characters only
        assert all(ord(c) < 128 for c in line)


def test_render_banner_wide_terminal() -> None:
    buf = io.StringIO()
    console = Console(file=buf, width=100, force_terminal=True, color_system="standard")
    render_banner(console, version="1.0.0")
    output = buf.getvalue()

    assert "BuddhiAI CLI" in output
    assert "1.0.0" in output


def test_render_banner_narrow_terminal_fallback() -> None:
    buf = io.StringIO()
    console = Console(file=buf, width=50, force_terminal=True, color_system="standard")
    render_banner(console, version="1.0.0")
    output = buf.getvalue()

    # On narrow terminal, ASCII art should be collapsed into a compact header
    assert "BuddhiAI CLI" in output
    assert "1.0.0" in output
    # Multi-line ASCII art should NOT be present in narrow view
    assert " | __ )" not in output


def test_formatters_print_status() -> None:
    buf = io.StringIO()
    console = Console(file=buf, width=80)
    print_status("Operation complete", status="ok", console=console)
    output = buf.getvalue()
    assert "Operation complete" in output


def test_formatters_print_init_summary() -> None:
    buf = io.StringIO()
    console = Console(file=buf, width=80)
    print_init_summary(
        root=Path("/project"),
        graph_nodes=100,
        graph_edges=200,
        graph_communities=5,
        docs_total=50,
        docs_stale=10,
        harness_added=8,
        harness_existing=2,
        artifacts=[Path("/project/.buddhi/graphs/tree-graph.json")],
        migration_notices=["migrated workflow"],
        console=console,
    )
    output = buf.getvalue()
    assert "Code Graph" in output
    assert "100 nodes" in output
    assert "Documentation Plan" in output
    assert "Agent Harness" in output
    assert "Next Steps" in output
    assert "migrated workflow" in output
