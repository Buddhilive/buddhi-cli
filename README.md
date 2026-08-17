# buddhi-cli

A CLI that uses tree-sitter to build a code graph (files, directories, classes,
functions/methods, and their containment/import/call relationships) for a
project, and persists it as JSON, a SQLite database, and an interactive HTML
visualization.

Supported languages: Python, JavaScript, TypeScript/TSX, Go, Rust, C#, Java,
Kotlin, Swift.

## Usage

```sh
uv sync
uv run buddhi generate --tree [path]
```

This scans `path` (defaults to the current directory) and writes three
artifacts to `.buddhi/graphs/` at the project root:

- `tree-graph.json` — the graph in Cytoscape.js elements format
- `tree-graph.db` — a SQLite database (`nodes`/`edges` tables, indexed for
  recursive CTE traversal — ancestor/descendant lookups, call-graph walks)
- `tree-graph.html` — an interactive Cytoscape.js visualization (loads
  Cytoscape.js from a CDN; open the file in a browser with internet access)

A `.buddhi/.gitignore` containing `graphs/` is created on first run so the
generated artifacts don't get committed to your project's own repository.

## Notes on accuracy

Import and call resolution is best-effort, not a full semantic analysis:
same-project relative imports and same-file/`self.`/`this.` calls are
resolved to real nodes; everything else (external packages, ambiguous
cross-file calls, ...) becomes an `external` placeholder node so the graph
stays informative without producing false edges.

## Development

```sh
uv run pytest
uv run ruff check src tests
uv run mypy src
```
