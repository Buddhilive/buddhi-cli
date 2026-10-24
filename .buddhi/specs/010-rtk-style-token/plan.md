# Implementation Plan: Token-Saving Command Output Filter (`buddhi scripts rtk`)

**Branch**: `010-rtk-style-token` (note: `buddhi sdd setup-plan` reported git branch `develop`; the spec directory is authoritative) | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/.buddhi/specs/010-rtk-style-token/spec.md`

## Summary

Add a `buddhi scripts rtk` command group that runs a command, filters its output with declarative JSON filters (concepts and ported data from rtk's Apache-2.0 `src/filters/*.toml`, converted to JSON), preserves the exit code, never drops errors, and fails open. A fail-open `PreToolUse` hook rewrites supported shell commands to the wrapped form. A rule, a skill, and updates to `terminal-runner`, `verify`, `implement` make SDD evidence compressed but auditable (raw log path kept). Pure stdlib; no new dependency.

## Technical Context

**Language/Version**: Python >=3.10 (matches `requires-python`)

**Primary Dependencies**: stdlib only (`re`, `json`, `subprocess`, `shlex`, `hashlib`). `typer`/`rich` already used by `commands/scripts.py`. **Decision**: filters stored as JSON, so no `tomli` is needed for 3.10.

**Storage**: Files only. `.buddhi/rtk/filters/*.json` (project filters), `.buddhi/rtk/trust.json` (hash pins), `.buddhi/rtk/runs.jsonl` (savings log), `.buddhi/rtk/raw/<ts>-<name>.log` (tee-on-failure, capped and pruned). Atomic writes via existing autoharness helpers where reusable.

**Testing**: pytest (`uv run pytest`), fixtures under `tests/rtk/fixtures/`; ruff and mypy per AGENTS.md.

**Target Platform**: Windows, macOS, Linux; Antigravity CLI/IDE/2.0.

**Project Type**: CLI plus harness customizations (hook, rule, skill, subagent edits).

**Performance Goals**: Hook adds <200 ms. Filtering is linear time with streaming read.

**Constraints**: Fail-open everywhere. Hook always exits 0. Bounded memory (cap raw capture, e.g. 8 MB, spill note). No network or telemetry. Args redacted in logs.

**Scale/Scope**: ~60 ported filters, one generic fallback, one hook, one rule, one skill.

### Antigravity configuration findings (docs search; antigravity.google pages not fetched directly)

- Hooks live in `.agents/hooks.json`; `PreToolUse` input arrives on stdin as JSON; hooks must exit 0 even when denying. Existing repo hooks use `{"decision": ...}` output and relative `python hooks/x.py` commands. The new hook MUST follow the repo's registered convention.
- Rules: `.agents/rules/*.md`. Skills: `.agents/skills/<name>/SKILL.md`. Subagents: `.agents/agents/<name>.md` (YAML frontmatter).
- **Open risk R1**: rtk's Antigravity hook rewrites via `overwrite.CommandLine`. The exact stdin tool-call shape (`toolCall.name`/`args.CommandLine`) and rewrite-response field must be confirmed against the Antigravity docs and with a live smoke test in task 1. The hook isolates this in one function (`protocol.py`). If rewrite via hook proves unsupported, fall back to rule/skill-driven explicit `buddhi scripts rtk run` usage (US1/US3 still ship).
- **Risk R2**: Antigravity evaluates permissions after hook rewrites, so allowlists must permit `buddhi scripts rtk run`. Document in README.

## Architecture Decisions (system-design)

| Decision | Choice | Rejected | Reason |
|---|---|---|---|
| Filter format | JSON, data-driven | TOML (needs `tomli` on 3.10), Python plugins | No dependency; user-chosen. Safe to load, no code execution, hashable for trust |
| Rewrite logic | Separate pure function `rewrite(command) -> Decision` shared by CLI `rtk rewrite` and the hook | Logic inside the hook | One place for gates, testable without Antigravity |
| Execution | `subprocess.Popen` with merged streaming read, no `shell=True` where avoidable | Always shell | Exit code fidelity, Windows `.cmd` handling via `shutil.which` |
| Destructive guard ordering | `guard_destructive.py` stays first in `hooks.json`; rtk hook second | rtk first | Guard must evaluate the original command |
| Scope of rewrites | Allowlist of known commands, only simple (no pipe, redirect, `&&`, heredoc, subshell) | Rewrite everything | Safe; rtk does the same |

Lenses: *Fewest-slices*: engine + `run` + generic filter (US1). *Risk-first*: hook protocol (R1), Windows execution, never losing errors (property tests), Apache attribution/BUSL exclusion. *Seam-quality*: engine knows nothing of Antigravity; hook is a thin adapter; skills only call the CLI.

Specialist agents were not dispatched in this run. Domains touched are backend (CLI/library), testing, security (hook rewrite, trust, redaction), and git (conventional commit/PR hygiene). The lens analysis above was done directly. Run the specialists in `/spec-tasks` review if desired.

## AGENTS.md Compliance Check

- [x] Project build & test commands adhered to (`uv run pytest`, `ruff check`, `ruff format --check`, `mypy src/ tests/`)
- [x] Architectural constraints respected (new code under `src/buddhi/scripts/`, wired in `commands/scripts.py`; hooks under `.agents/hooks/`)
- [x] No unapproved external dependencies introduced (stdlib only)
- [x] Licensing: only Apache-2.0 rtk scope used; `engine/` and `proxy/` (BUSL-1.1) not read or derived. Ported filters keep notice + "modified" marker
- [x] Evidence verification through `terminal-runner`; after `/implement`, refresh `.buddhi/docs` via `/document-codebase`

## Project Structure

### Documentation (this feature)

```text
.buddhi/specs/010-rtk-style-token/
  plan.md
  spec.md
  tasks.md              # created by /spec-tasks
```

### Source Code (repository root)

```text
src/buddhi/scripts/rtk/
  __init__.py           # public API: run_filtered, rewrite, gain
  engine.py             # apply_filter(): strip/keep/replace/dedup/head-tail/on_empty, error-line guard
  generic.py            # fallback: ANSI strip, blank collapse, dup collapse, truncation
  filters.py            # load/validate/match JSON filters; builtin + project; trust check
  runner.py             # subprocess exec, streaming capture, exit code, tee-on-failure
  rewrite.py            # command classification and Decision (rewrite/skip + reason)
  tracking.py           # runs.jsonl, token estimate (len/4), gain report, arg redaction
  trust.py              # sha256 pin store for project filters
  builtin_filters/      # ported *.json (~60) + NOTICE header fields (source, license, modified)
  NOTICE                # Apache-2.0 attribution for ported data
src/buddhi/commands/scripts.py   # + `rtk` Typer sub-app: run | rewrite | gain | filters list/test/verify | trust
.agents/hooks/rtk_hook.py        # thin adapter, fail-open, always exit 0
.agents/hooks.json               # + PreToolUse entry after guard_destructive.py
.agents/rules/rtk.md             # always-on guidance
.agents/skills/rtk/SKILL.md      # when/how to use, `--raw`, reading raw log path
.agents/agents/terminal-runner.md        # prefer `buddhi scripts rtk run --`, report raw log path
.agents/skills/verify/SKILL.md, implement/SKILL.md   # evidence rules with compression
ACKNOWLEDGMENTS.md, README.md, CHANGELOG.md          # per FR-012

tests/rtk/
  fixtures/             # captured raw outputs + expected filtered
  test_engine.py  test_generic.py  test_filters.py  test_runner.py
  test_rewrite.py  test_hook.py  test_tracking.py  test_trust.py  test_cli.py
```

**Structure Decision**: Mirrors the existing `scripts/autoharness` package pattern (library package + Typer wiring + `.agents` hook/rule/skill). Template-installed assets (`src/buddhi/templates/`, harness generator) must also ship the new rule, skill, hook, and `hooks.json` entry; confirm the generator mapping in task 1 (this repo's `.agents/` appears generated from these templates).

## Delivery Order (by story)

1. **US1 (P1)**: `engine`, `generic`, `runner`, `filters` + 10 core builtin filters (git, pytest, ruff, mypy, uv, pip, npm, cargo, docker, ls/grep), CLI `run`, tee-on-failure, tests.
2. **US2 (P2)**: `rewrite.py`, `rtk rewrite`, `rtk_hook.py`, `hooks.json`, R1 smoke test.
3. **US3 (P2)**: rule, skill, `terminal-runner`/`verify`/`implement` edits, template sync.
4. **Broad port**: convert remaining rtk filters from `temp/rtk/src/filters/*.toml` to JSON with a one-off conversion script (kept out of the package), each with attribution and inline tests migrated where present.
5. **US4 (P3)**: `tracking`, `gain`, `filters list|test|verify`, `trust`.
6. **Docs**: `ACKNOWLEDGMENTS.md`, `README.md`, `CHANGELOG.md [Unreleased]`, `/document-codebase`.

## Security Notes

- Hook only rewrites an allowlisted simple command; the rewritten command is `buddhi scripts rtk run -- <original args>` with args quoted using platform-correct quoting. Guard hook still sees the original.
- No filter can execute code (declarative regex only). Project filters need a hash pin. Regex safety: reject catastrophic patterns by length cap and per-line time-free `re` with a size limit on input lines.
- Redact args in `runs.jsonl`. Raw logs may contain secrets, so they live under git-ignored `.buddhi/rtk/raw/` with age/size pruning.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Separate `rewrite.py` plus hook adapter | Hook protocol is unconfirmed (R1); isolating it keeps the fallback cheap | Inline logic would couple the engine to an unverified protocol |
| ~60 JSON filters conversion script | User chose a broad port | MVP-only set would not meet the stated scope |
| Template sync for generated `.agents/` | Harness generator ships these assets to users | Editing only this repo's `.agents/` would not reach generated harnesses |
