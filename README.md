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

Buddhi AI CLI turns a codebase into what an AI coding agent actually needs:
a **code graph** (files, directories, classes, functions/methods, and their
containment/import/call relationships, via tree-sitter), a scaffolded
**Google Antigravity agent harness** grounded in that graph, and a full
**Spec-Driven Development (SDD)** lifecycle based on open standards like [AGENTS.md](https://agents.md/).

The idea: point Buddhi AI CLI at a project, and it gives Antigravity:
- A full **Spec-Driven Development (SDD)** workflow:
  1. `/specify` — Scaffold feature branch and refine `spec.md` with prioritized, testable user stories.
  2. `/plan` — Synthesize architectural design into `plan.md` via domain specialists and `AGENTS.md` compliance checks.
  3. `/tasks` — Generate a phased, story-oriented task breakdown into `tasks.md` with `[P]` parallelism markers.
  4. `/implement` — Execute tasks with prerequisite validation and live progress tracking in `tasks.md`.
  5. `/verify` — Evidence-based test execution mapping results to specification acceptance criteria (SDD convergence mode).
- A `/quick-plan` workflow for lightweight, non-SDD multi-specialist planning.
- A `/document-codebase` workflow that generates dependency-aware OKF symbol documentation.
- Specialized `/debug`, `/remember`, and `/status` workflows for systematic root-cause investigation, persistent memory capture, and harness dashboarding.
- Domain specialist agents (frontend, backend, database, testing, security, deployment, git) and `terminal-runner` for delegated command execution.

Supported languages: Python, JavaScript, TypeScript/TSX, Go, Rust, C#, Java,
Kotlin, Swift.

## Installation

Requires Python 3.10+.

```sh
pip install buddhi-ai
```

Or, if you prefer an isolated tool install:

```sh
pipx install buddhi-ai
# or
uv tool install buddhi-ai
```

This installs the `buddhi` command.

## Usage

### `buddhi init` — full setup (recommended)

```sh
buddhi init [path]
```

Scans `path` (defaults to the current directory), builds the code graph,
computes a documentation plan, scaffolds the root `AGENTS.md`, and prepares the Antigravity agent harness.
Writes:

- `AGENTS.md` — standard project instructions, dev commands, and architecture rules at the project root (created if not already present)
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
  skills, templates, memory index — see below). **Idempotent**: rerunning `init` never
  overwrites a harness file you've already edited under `.agents/`, it only
  fills in what's missing.

A `.buddhi/.gitignore` (ignoring `graphs/` and `docs/`) is created on first
run so generated artifacts don't get committed to your project's own repo.

Next step printed at the end: open the project in Antigravity, run
`/document-codebase`, and start a feature with `/specify`.

### `buddhi generate` — graph only

```sh
buddhi generate [path]
```

Scans `path` and writes just the three graph artifacts under
`.buddhi/graphs/`, without touching `.buddhi/docs-plan.json` or `.agents/`.
Useful for refreshing the graph on its own, or in contexts that don't need
the Antigravity harness.

### `buddhi docs plan` — refresh the doc plan only

```sh
buddhi docs plan [path]
```

Recomputes `.buddhi/docs-plan.json` against the current source tree without
touching `.agents/`. This is what `/document-codebase` and `/plan`
Antigravity workflows call before doing anything else, so the plan always
reflects the current source.

### `buddhi sdd` — Spec-Driven Development CLI helpers

```sh
buddhi sdd <command> [options]
```

Underlying helper commands used by the SDD workflows:
- `buddhi sdd create <description>` — Create a new feature directory under `.buddhi/specs/<branch>/`, create branch name, and instantiate `spec.md` from template.
- `buddhi sdd setup-plan` — Set up `plan.md` for the active feature branch from `plan-template.md`.
- `buddhi sdd setup-tasks` — Verify prerequisites and output task resolution context for `tasks.md`.
- `buddhi sdd check` — Consolidated prerequisite checker supporting `--require-tasks`, `--include-tasks`, `--paths-only`, and `--json`.
- `buddhi sdd resolve-template <name>` — Resolve and compose templates across `.agents/templates/` and built-in defaults.

## The Antigravity agent harness

`buddhi init` scaffolds `.agents/` with:

- **`workflows/`**
  - **`/specify`** — Initialize a new feature branch, scaffold `.buddhi/specs/<branch>/spec.md`, and iteratively refine requirements into prioritized, independently testable user stories (`P1`, `P2`...).
  - **`/plan`** — Spec-Driven Development architecture workflow: verifies `spec.md`, resolves `plan-template.md`, dispatches domain specialists in parallel, checks `AGENTS.md` compliance, and synthesizes `.buddhi/specs/<branch>/plan.md`.
  - **`/tasks`** — Break down `spec.md` and `plan.md` into actionable, phased tasks organized by user story into `tasks.md` with `[P]` parallelism markers.
  - **`/implement`** — Enforce prerequisite checks (`spec.md` + `plan.md` + `tasks.md`) and execute tasks story by story, tracking completion directly in `tasks.md`.
  - **`/verify`** — Repurposed verification workflow: runs real build/lint/test commands via `terminal-runner` and maps evidence to user story acceptance criteria (SDD convergence mode), with fallback to general verification for ad-hoc changes.
  - **`/quick-plan`** — Lightweight implementation planning for requests that do not require full SDD branching/spec overhead.
  - **`/document-codebase`** — Generate or refresh OKF symbol documentation bottom-up.
  - **`/debug`** — Systematic bug investigation producing a confirmed root cause and concrete fix plan without modifying code.
  - **`/remember`** — Capture user preferences, project conventions, and technical decisions into memory.
  - **`/status`** — Dashboard of harness state (docs staleness, active plans, memory size, git branch).
- **`templates/`** — Standard templates for specifications (`spec-template.md`), implementation plans (`plan-template.md`), task lists (`tasks-template.md`), review checklists (`checklist-template.md`), and agent configurations (`agents-template.md`).
- **`agents/`** — Read-only specialist subagents (`backend-specialist`,
  `frontend-specialist`, `database-specialist`, `testing-specialist`,
  `security-specialist`, `deployment-specialist`, `git-specialist`) dispatched
  in parallel by `/plan` and `/quick-plan`, plus `terminal-runner` for delegated shell/build/test
  execution.
- **`rules/`** — Always-on conventions: consult `.buddhi/docs/` and the code
  graph before raw source, require confirmation before destructive commands,
  read/append to the memory index for durable decisions.
- **`hooks.json`** / **`hooks/guard_destructive.py`** — A `PreToolUse`
  hook that mechanically denies destructive commands (force-push,
  `reset --hard`, `DROP`/`TRUNCATE`, disk-format commands, etc.) as a
  safety backstop.
- **`skills/`** — `okf-context` (how to read the generated docs and query SQLite code graph),
  `repoagent-doc-generation` (how to write docs), `system-design` (an
  architecture/trade-off decision framework used during planning), and custom skill slots (see
  `.agents/skills/README.md`).
- **`memory/MEMORY.md`** — A structured index into topic files under
  `.agents/memory/` (`user-preferences.md`, `project-conventions.md`,
  `tech-decisions.md`, `feedback-history.md`).

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

---

## Contributing

The sections below are for working on Buddhi AI CLI itself, not for using it.

### Setup

```sh
uv sync
```

Once dependencies are installed, run the CLI from source with `uv run`,
e.g. `uv run buddhi init [path]`, instead of the plain `buddhi` command shown
above.

### Development

```sh
uv run pytest
uv run ruff check src tests
uv run mypy src
```

### Publishing

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
