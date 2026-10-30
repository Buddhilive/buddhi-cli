# Implementation Plan: Anti-Slop Skills, Rules & Scripts Integration

**Branch**: `003-anti-slop-skills` | **Date**: 2026-10-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/.buddhi/specs/003-anti-slop-skills/spec.md`

## Summary

Ship the MIT-licensed `anti-slop` filter (miqdadbadjuber/anti-slop) as part of `buddhi init`: six `antislop*` skills and one always-on rule, adapted to Antigravity conventions. Port the stdlib-only helpers to Python as `buddhi scripts contrast` and `buddhi scripts antislop-mode`, and expose contrast checking to agents as a `check_contrast` tool in the existing `buddhi mcp` server. Add `ACKNOWLEDGMENTS.md` (MIT notice), and update README and CHANGELOG `[Unreleased]`.

No new mechanism is needed for `init`: `sync_template_tree` already copies everything under `src/buddhi/templates/agents/` into `.agents/` without overwriting user-edited files. Adding files there is sufficient.

## Technical Context

**Language/Version**: Python >=3.10 (stdlib only for new code)

**Primary Dependencies**: existing `typer`, `rich`; optional `mcp[cli]` (already used by `buddhi.mcp.server`). **No new dependencies.**

**Storage**: Files only. `antislop-mode` reads/writes the upstream-compatible global settings file (`%APPDATA%\antislop\settings.json` on Windows, else `~/.config/antislop/settings.json`; JSON `{"mode": "during|after|ask"}`), shared with other agents as the skill text states.

**Testing**: pytest (`tests/`, `typer.testing.CliRunner`), ruff, mypy per `pyproject.toml` dev group.

**Target Platform**: Windows, macOS, Linux.

**Project Type**: CLI library/tool (`buddhi-ai`, uv_build backend; templates shipped as package data).

**Performance Goals**: N/A (instant).

**Constraints**: settings file never overwritten if unparseable (parity with upstream); no execution of file content; output must survive Windows console encodings (ASCII-safe verdict text).

**Scale/Scope**: 6 skills, 1 rule, 1 command group (2 subcommands), 1 MCP tool.

## Findings from Grounding

1. **Antigravity format** (docs re-checked): skills live in `.agents/skills/<name>/SKILL.md`; `description` is mandatory, `name` optional (defaults to folder); optional `scripts/`, `references/`, `resources/` subfolders. Rules live in `.agents/rules/*.md` with `trigger` frontmatter (`always_on`, `model_decision`, `glob`, `manual`).
2. **Drafts audit** (`src/buddhi/templates/agents/skills/antislop*`): all six exist, already rewritten to say "scaffolded by `buddhi init`", with no Cursor/Claude references found. Gaps:
   - The always-on **rule is missing** (`templates/agents/rules/` has only `harness-core.md`, `okf-docs.md`).
   - Skills reference `buddhi scripts contrast` and **`buddhi scripts antislop-mode`** (upstream `cli/lib/settings.mjs`). Neither command exists (`src/buddhi/scripts/` is empty). Spec previously marked `cli/` out of scope; this plan pulls in **only** the mode-setting logic because the skill text depends on it (spec updated: FR-004b).
   - `antislop-human` lacks its `contrast-check.py`; the selftest needs the SKILL.md reference table, which must be resolvable from the installed package (see decision D2).
   - Skill frontmatter carries a `version` key; consistent with existing buddhi skills (`specify`, etc.), so kept.
   - `frontend-specialist.md` edit is fine; verify it renders in `init` output.
3. **Entry points**: new Typer sub-app registered in `src/buddhi/cli.py` via `app.add_typer(scripts_app, name="scripts")` alongside `docs`, `sdd`, `skills`. MCP tools are registered in `src/buddhi/mcp/server.py` with `@mcp.tool(...)`, delegating to `buddhi.mcp.tools.*` (lazy import).
4. **Dogfood**: this repo's own `.agents/` is separate from templates; syncing is optional (decision D4).
5. **Scripts package**: `src/buddhi/scripts/` exists but is an empty dir (no `__init__.py`); `buddhi.sdd` is the precedent for a logic package, `buddhi.commands.*` for Typer layers.

## Design Decisions

| # | Decision | Rationale / rejected alternative |
|---|---|---|
| D1 | Pure logic in `src/buddhi/scripts/contrast.py` and `antislop_mode.py` (no Typer/MCP imports); Typer layer in `src/buddhi/commands/scripts.py`; MCP tool delegates to `buddhi.scripts.contrast`. | Follows `sdd` / `commands` split; single source of truth for CLI and MCP. Rejected: duplicating the math in the MCP tool. |
| D2 | `--selftest` validates against a **reference table embedded in the shipped `antislop-human/SKILL.md`**, located via `importlib.resources` (`buddhi.templates.agents` → `skills/antislop-human/SKILL.md`), not via a path next to the script. | Upstream finds the doc beside the script; here the script lives in the package. Keeps "the skill doc is the source of truth". Fails with a clear message if the table is missing. |
| D3 | Contrast parsing accepts `#RRGGBB`, `RRGGBB`, `#RGB`, `black`, `white`; rejects alpha/`rgb()` with a clear error (exit 2). Exit 0 only if both normal (4.5) and large (3.0) pass, else 1. | Parity with upstream; spec edge case. |
| D4 | Do **not** hand-copy templates into this repo's `.agents/`; users get them via `buddhi init`. Optionally run `buddhi init` here at the end. | Avoids drift; `init` is idempotent. |
| D5 | Rule template `rules/antislop.md` uses `trigger: always_on` and a body adapted from upstream (`rules/antislop.md`), with paths changed to `.agents/skills/antislop*/SKILL.md`. Always installed, no flag. | User decision. Docs: `always_on` rules are injected every turn, so the body stays short and routes to skills. Rejected: `model_decision` (user wants always installed/active as upstream). |
| D6 | Attribution: short "Adapted from antislop (MIT, (c) 2026 Miqdad Badjuber)" note in each skill/rule is already partly present or added; full license in `ACKNOWLEDGMENTS.md`. | MIT requires the notice in substantial portions; root file plus pointer notes satisfy it. |
| D7 | Packaging: confirm `uv_build` includes non-`.py` template files and new subpackage (`scripts/__init__.py` required). Verified by building a wheel and listing contents. | Existing templates already ship, so likely automatic; verify only. |

## AGENTS.md Compliance Check

- [x] Project build & test commands adhered to (`uv run pytest`, `ruff check`, `mypy src/`, verified through `terminal-runner`; note AGENTS.md placeholders are unfilled, so commands come from `pyproject.toml` dev group)
- [x] Architectural constraints respected (grounded in existing `commands/`, `mcp/`, `templates/` layout; OKF docs refreshed afterwards)
- [x] No unapproved external dependencies introduced (stdlib only)

## Project Structure

### Documentation (this feature)

```text
.buddhi/specs/003-anti-slop-skills/
  spec.md
  plan.md          # this file
  tasks.md         # created by /tasks
```

### Source Code (repository root)

```text
ACKNOWLEDGMENTS.md                                  # NEW (MIT notice + credit)
README.md                                           # UPDATE (feature + `buddhi scripts` + credit link)
CHANGELOG.md                                        # UPDATE ([Unreleased] > Added)

src/buddhi/
  cli.py                                            # UPDATE: register scripts_app
  commands/scripts.py                               # NEW: `buddhi scripts contrast|antislop-mode`
  scripts/__init__.py                               # NEW
  scripts/contrast.py                               # NEW: parse_hex, luminance, ratio, verdicts, selftest
  scripts/antislop_mode.py                          # NEW: settings path, read, configure_mode
  mcp/server.py                                     # UPDATE: @mcp.tool check_contrast
  mcp/tools/contrast.py                             # NEW: execute_check_contrast (thin wrapper), matches tools/ pattern
  templates/agents/
    rules/antislop.md                               # NEW: always_on rule
    agents/frontend-specialist.md                   # EXISTING draft edit (verify)
    skills/antislop/SKILL.md                        # EXISTING draft (audit)
    skills/antislop-ui/SKILL.md                     # EXISTING draft (audit)
    skills/antislop-copywriting/SKILL.md            # EXISTING draft (audit)
    skills/antislop-human/SKILL.md                  # EXISTING draft (audit; mention `check_contrast` MCP tool)
    skills/antislop-layoutmobile/SKILL.md           # EXISTING draft (audit)
    skills/antislop-code/SKILL.md                   # EXISTING draft (audit)

tests/
  test_scripts_contrast.py                          # NEW
  test_scripts_antislop_mode.py                     # NEW (uses tmp settings path via env/monkeypatch)
  test_cli_scripts.py                               # NEW: CliRunner exit codes/output
  test_mcp_server.py                                # UPDATE: check_contrast tool
  test_cli_init.py                                  # UPDATE: assert 6 antislop skills + rule installed
```

**Structure Decision**: Single project. Logic in `buddhi.scripts`, CLI wiring in `buddhi.commands`, MCP wrapper in `buddhi.mcp.tools`, content in `templates/agents`, mirroring existing packages.

## Specialist Dispatch

Scoped to a small, single-package change; no specialist subagents were dispatched. Backend (CLI/MCP), testing and security (file write to user settings, untrusted JSON, no code execution) concerns are covered inline:

- **Security**: settings file read as data only; unparseable file never overwritten; `mode` validated against an allow-list; write is confined to the per-user config path; no shell/network.
- **Testing**: unit-test pure functions (known ratios 21:1, 1:1, boundary 4.5 and 3.0), CLI exit codes, selftest pass/fail, settings round-trip with invalid file, MCP tool output, init asset presence. Evidence via `terminal-runner`.
- **Git**: work stays on the feature branch; the existing untracked drafts are committed together with the feature. No destructive git operations.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Added `antislop-mode` script beyond the user's literal list | Draft skills (and upstream skill text) instruct the agent to read/save a global mode via it | Removing it would require rewriting the core skill's "Two Usage Modes", diverging from upstream behavior |

## Risks

- Windows console encoding: keep script output ASCII.
- `--selftest` coupling to SKILL.md table format: test guards the format.
- README/CHANGELOG conventions: follow existing headings (inspect during implementation).
