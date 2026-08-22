# Buddhi AI CLI

<p align="center">
  <a href="https://pypi.org/project/buddhi-ai/">
    <img src="https://img.shields.io/pypi/v/buddhi-ai?style=flat-square&logo=pypi" alt="PyPI Version" />
  </a>
  <a href="https://pypi.org/project/buddhi-ai/">
    <img src="https://img.shields.io/pypi/dm/buddhi-ai?style=flat-square" alt="PyPI Downloads" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/Buddhilive/buddhi-cli?style=flat-square" alt="License" />
  </a>
</p>

Buddhi AI CLI turns a codebase into two things an AI coding agent actually needs:
a **code graph** (files, directories, classes, functions/methods, and their
containment/import/call relationships, via tree-sitter) and a scaffolded
**Google Antigravity agent harness** that's grounded in that graph instead of
generic advice.

The idea: point Buddhi AI CLI at a project, and it gives Antigravity a `/plan`
workflow with domain specialist agents (frontend, backend, database, testing,
security, deployment, git) plus a `/document-codebase` workflow that
generates real per-symbol documentation — both reading from Buddhi AI CLI's graph
and docs instead of re-deriving understanding from raw source every time.

Supported languages: Python, JavaScript, TypeScript/TSX, Go, Rust, C#, Java,
Kotlin, Swift.

## Install

```sh
uv sync
```

## Usage

### `buddhi init` — full setup (recommended)

```sh
uv run buddhi init [path]
```

Scans `path` (defaults to the current directory), builds the code graph,
computes a documentation plan, and scaffolds the Antigravity agent harness.
Writes:

- `.buddhi/graphs/tree-graph.json` — the graph in Cytoscape.js elements format
- `.buddhi/graphs/tree-graph.db` — a SQLite database (`nodes`/`edges` tables,
  indexed for recursive CTE traversal — ancestor/descendant lookups,
  call-graph walks)
- `.buddhi/graphs/tree-graph.html` — an interactive Cytoscape.js
  visualization (loads Cytoscape.js from a CDN; open in a browser with
  internet access)
- `.buddhi/docs-plan.json` — a bottom-up, staleness-aware plan of what needs
  documenting
- `.agents/` — the Antigravity agent harness (agents, workflows, rules,
  skills, memory index — see below). **Idempotent**: rerunning `init` never
  overwrites a harness file you've already edited under `.agents/`, it only
  fills in what's missing.

A `.buddhi/.gitignore` (ignoring `graphs/` and `docs/`) is created on first
run so generated artifacts don't get committed to your project's own repo.

Next step printed at the end: open the project in Antigravity and run
`/document-codebase`, then `/plan`.

### `buddhi generate` — graph only

```sh
uv run buddhi generate [path]
```

Scans `path` and writes just the three graph artifacts under
`.buddhi/graphs/`, without touching `.buddhi/docs-plan.json` or `.agents/`.
Useful for refreshing the graph on its own, or in contexts that don't need
the Antigravity harness.

### `buddhi docs plan` — refresh the doc plan only

```sh
uv run buddhi docs plan [path]
```

Recomputes `.buddhi/docs-plan.json` against the current source tree without
touching `.agents/`. This is what the `/document-codebase` and `/plan`
Antigravity workflows call before doing anything else, so the plan always
reflects the current source.

## The Antigravity agent harness

`buddhi init` scaffolds `.agents/` with:

- **`workflows/`** — `/document-codebase` (generate or refresh docs) and
  `/plan` (turn a request into an implementation plan grounded in the real
  codebase, without writing any code)
- **`agents/`** — read-only specialist subagents (`backend-specialist`,
  `frontend-specialist`, `database-specialist`, `testing-specialist`,
  `security-specialist`, `deployment-specialist`, `git-specialist`) dispatched
  in parallel by `/plan`, plus `terminal-runner` for delegated shell/build/test
  execution
- **`rules/`** — always-on conventions: consult `.buddhi/docs/` and the code
  graph before raw source, require confirmation before destructive commands,
  read/append to the memory index for durable decisions
- **`skills/`** — `okf-context` (how to read the generated docs),
  `repoagent-doc-generation` (how to write them), and a slot for
  tech-stack-specific skills you drop in yourself (see
  `.agents/skills/README.md`)
- **`memory/MEMORY.md`** — a durable, append-only index of project
  conventions and decisions discovered across `/plan` runs

### Documentation format

Generated docs under `.buddhi/docs/` follow the
[Open Knowledge Format](https://okf.org/) (OKF): one concept file per
module/class/function, each carrying frontmatter that names its source file
and line range, a content hash for staleness detection, and a status. The
bottom-up generation order — document a symbol only after everything it
depends on is already documented — is inspired by the
[RepoAgent](https://arxiv.org/abs/2402.16667) paper's approach to
whole-repository, dependency-aware documentation.

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
`buddhi-ai` project, pointing at this repository, the `publish.yml` workflow
file, and the `pypi` environment.
