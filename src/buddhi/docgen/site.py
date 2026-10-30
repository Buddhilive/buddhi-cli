"""Pelican static site compilation, search index emission, and live documentation server."""

from __future__ import annotations

import json
import shutil
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from typing import Any

from pelican import Pelican  # type: ignore[import-untyped]
from pelican.server import (  # type: ignore[import-untyped]
    ComplexHTTPRequestHandler,
    RootedHTTPServer,
)
from pelican.settings import read_settings  # type: ignore[import-untyped]

from buddhi.docgen.generator import generate_docs_bundle
from buddhi.docgen.reader import OKFMarkdownReader
from buddhi.graph.model import CodeGraph
from buddhi.memory.frontmatter import split_frontmatter


def get_theme_dir() -> Path:
    """Return the bundled Pelican documentation theme directory."""
    return Path(__file__).parent / "theme"


def get_pelican_settings(
    docs_dir: Path,
    output_dir: Path,
    sitename: str = "Buddhi Documentation",
    theme_dir: Path | None = None,
) -> dict[str, Any]:
    """Construct programmatically resolved Pelican settings for OKF documentation."""
    theme = (theme_dir or get_theme_dir()).resolve()
    base_settings = read_settings(
        path=None,
        override={
            "PATH": str(docs_dir.resolve()),
            "OUTPUT_PATH": str(output_dir.resolve()),
            "THEME": str(theme),
            "THEME_STATIC_DIR": "theme",
            "THEME_STATIC_PATHS": ["static"],
            "READERS": {"md": OKFMarkdownReader, "markdown": OKFMarkdownReader},
            "PAGE_PATHS": [""],
            "ARTICLE_PATHS": [],
            "STATIC_PATHS": [],
            "PATH_METADATA": r"(?P<path_no_ext>.*)\..*",
            "PAGE_SAVE_AS": "{path_no_ext}.html",
            "PAGE_URL": "{path_no_ext}.html",
            "DIRECT_TEMPLATES": [],
            "SITENAME": sitename,
            "SITEURL": "",
            "RELATIVE_URLS": True,
            "CACHE_CONTENT": False,
            "LOAD_CONTENT_CACHE": False,
            "DELETE_OUTPUT_DIRECTORY": False,
            "FEED_ALL_ATOM": None,
            "CATEGORY_FEED_ATOM": None,
            "AUTHOR_SAVE_AS": "",
            "CATEGORY_SAVE_AS": "",
            "TAG_SAVE_AS": "",
            "ARCHIVES_SAVE_AS": "",
            "AUTHORS_SAVE_AS": "",
            "CATEGORIES_SAVE_AS": "",
            "TAGS_SAVE_AS": "",
        },
    )
    return dict(base_settings)


def generate_search_index(docs_dir: Path, output_dir: Path) -> Path:
    """Scan docs_dir markdown files and emit search-index.json into output_dir."""
    entries: list[dict[str, Any]] = []

    if docs_dir.is_dir():
        for md_file in sorted(docs_dir.rglob("*.md")):
            try:
                text = md_file.read_text(encoding="utf-8")
                data, _ = split_frontmatter(text)
                rel_path = md_file.relative_to(docs_dir)
                html_url = rel_path.with_suffix(".html").as_posix()
                entries.append(
                    {
                        "title": data.get("title") or md_file.stem,
                        "kind": data.get("type") or data.get("kind", "concept"),
                        "summary": data.get("description") or data.get("summary", ""),
                        "url": html_url,
                        "tags": data.get("tags") or [],
                        "status": data.get("status", "stable"),
                        "community": data.get("community_id"),
                    }
                )
            except OSError:
                continue

    output_dir.mkdir(parents=True, exist_ok=True)
    index_file = output_dir / "search-index.json"
    index_file.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return index_file


def copy_interactive_graph(root: Path, output_dir: Path) -> None:
    """Copy interactive Cytoscape graph visualization into site output, or provide fallback placeholder."""
    graph_html = root / ".buddhi" / "graphs" / "tree-graph.html"
    target_dir = output_dir / "graphs"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / "tree-graph.html"

    if graph_html.is_file():
        try:
            shutil.copy2(graph_html, target_file)
            return
        except OSError:
            pass

    if not target_file.is_file():
        fallback_content = (
            '<!DOCTYPE html>\n<html lang="en">\n<head>\n'
            '  <meta charset="utf-8">\n'
            "  <title>Interactive Code Graph</title>\n"
            '  <link rel="stylesheet" href="../theme/css/theme.css">\n'
            '</head>\n<body class="site-body" style="padding: 2rem; max-width: 800px; margin: 0 auto;">\n'
            "  <h1>Interactive Code Graph</h1>\n"
            "  <p>The interactive Cytoscape code graph has not been generated yet for this project.</p>\n"
            "  <p>Run <code>buddhi generate --tree</code> or <code>buddhi docs build</code> to generate the code graph.</p>\n"
            '  <p><a href="../index.html">&larr; Return to Documentation Portal</a></p>\n'
            "</body>\n</html>\n"
        )
        try:
            target_file.write_text(fallback_content, encoding="utf-8")
        except OSError:
            pass


class BuddhiHTTPRequestHandler(ComplexHTTPRequestHandler):
    """Custom request handler with cache-control headers and clean favicon handling."""

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def do_GET(self) -> None:
        if self.path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        super().do_GET()


def compile_site(
    root: Path,
    output_dir: Path | None = None,
    theme_dir: Path | None = None,
    graph: CodeGraph | None = None,
    verbose: bool = False,
) -> Path:
    """Compile OKF documentation under .buddhi/docs/ into static HTML via Pelican."""
    docs_dir = root / ".buddhi" / "docs"
    out = (output_dir or root / ".buddhi" / "site").resolve()
    docs_dir.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    # 0. Synthesize graph-grounded OKF markdown bundle if database exists
    generate_docs_bundle(root, graph=graph)

    # 1. Read / prepare settings
    sitename = f"{root.name} Documentation"
    settings = get_pelican_settings(
        docs_dir=docs_dir,
        output_dir=out,
        sitename=sitename,
        theme_dir=theme_dir,
    )

    # 2. Run Pelican
    pelican = Pelican(settings=settings)
    pelican.run()

    # 3. Emit search index
    generate_search_index(docs_dir, out)

    # 4. Copy interactive code graph
    copy_interactive_graph(root, out)

    return out


def is_port_available(host: str, port: int) -> bool:
    """Check whether a host and port can be bound for listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False


class LiveReloader:
    """Simple background directory watcher that re-compiles documentation on changes."""

    def __init__(self, root: Path, output_dir: Path, interval: float = 1.0) -> None:
        self.root = root
        self.docs_dir = root / ".buddhi" / "docs"
        self.output_dir = output_dir
        self.interval = interval
        self.running = False
        self._last_snapshot: dict[str, float] = {}

    def _snapshot(self) -> dict[str, float]:
        snap: dict[str, float] = {}
        if self.docs_dir.is_dir():
            for p in self.docs_dir.rglob("*.md"):
                try:
                    snap[str(p)] = p.stat().st_mtime
                except OSError:
                    pass
        return snap

    def start(self) -> None:
        self._last_snapshot = self._snapshot()
        self.running = True

        def _loop() -> None:
            while self.running:
                time.sleep(self.interval)
                current = self._snapshot()
                if current != self._last_snapshot:
                    self._last_snapshot = current
                    try:
                        compile_site(self.root, self.output_dir)
                    except Exception as exc:  # noqa: BLE001
                        print(
                            f"error during live reload rebuild: {exc}", file=sys.stderr
                        )

        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def stop(self) -> None:
        self.running = False


def serve_docs(
    root: Path,
    host: str = "127.0.0.1",
    port: int = 8000,
    reload: bool = True,
    open_browser: bool = True,
    output_dir: Path | None = None,
    theme_dir: Path | None = None,
    graph: CodeGraph | None = None,
    verbose: bool = False,
) -> None:
    """Compile and serve documentation locally with live reload."""
    out = (output_dir or root / ".buddhi" / "site").resolve()

    # Compile initial site
    compile_site(
        root, output_dir=out, theme_dir=theme_dir, graph=graph, verbose=verbose
    )

    if not is_port_available(host, port):
        raise OSError(
            f"Port {port} on {host} is already in use. Please specify another port with --port."
        )

    reloader = None
    if reload:
        reloader = LiveReloader(root, out)
        reloader.start()

    server_address = (host, port)
    httpd = RootedHTTPServer(str(out), server_address, BuddhiHTTPRequestHandler)

    url = f"http://{host}:{port}/"
    print(f"Serving documentation at {url}")
    print("Press Ctrl+C to stop the server.")

    if open_browser:
        webbrowser.open(url)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping documentation server.")
    finally:
        if reloader:
            reloader.stop()
        httpd.server_close()
