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

## Publishing

Releases to PyPI are handled by the [`publish.yml`](.github/workflows/publish.yml)
GitHub Actions workflow. It builds the package with `uv build` and publishes it
using [PyPI trusted publishing](https://docs.pypi.org/trusted-publishers/) (OIDC),
so no API token is stored in the repository.

The workflow triggers on any pushed tag matching `v*` (e.g. `v0.1.0`). To cut a
release:

1. Bump `version` in [`pyproject.toml`](pyproject.toml).
2. Commit the change and tag it to match, e.g.:
   ```sh
   git commit -am "Bump version to 0.1.1"
   git tag v0.1.1
   git push origin main v0.1.1
   ```
3. The tag push triggers the workflow, which builds and publishes the package
   to PyPI automatically.

This requires a trusted publisher to be configured once on PyPI for the
`buddhi` project, pointing at this repository, the `publish.yml` workflow
file, and the `pypi` environment.
