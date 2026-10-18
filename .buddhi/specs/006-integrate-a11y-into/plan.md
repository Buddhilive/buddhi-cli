# Implementation Plan: Integrate A11Y.md into Antigravity Harness and Spec-Driven Workflow

**Branch**: `006-integrate-a11y-into` | **Date**: 2026-10-27 | **Spec**: [spec.md](file:///c:/DevDojo/Buddhi/buddhi-cli/.buddhi/specs/006-integrate-a11y-into/spec.md)

**Input**: Feature specification from `/.buddhi/specs/006-integrate-a11y-into/spec.md`

## Summary

Integrate `A11Y.md` (v2.5.0) into the Google Antigravity agent harness scaffolded by `buddhi init`, creating an end-to-end accessibility constraint and verification system. The integration delivers:
1. An always-on Antigravity routing rule (`.agents/rules/a11y.md`) and core skill (`.agents/skills/a11y/SKILL.md`), customized with Buddhi CLI/MCP tooling and fresh-context subagent verification.
2. Complete local lazy-loading reference library (31 `references/guide-*.md` files) and lifecycle governance templates (`REPORT.md`, `EXCEPTIONS.md`, `A11Y-DECISIONS.md`, `ACCESSIBILITY.md`).
3. Pure Python CLI static gate (`buddhi scripts verify-a11y`) decomposed into modular components under `src/buddhi/scripts/verify_a11y/` to strictly comply with the 8,000-token (~32 KB) ratchet budget, complete with 31 upstream self-test fixtures.
4. Extended WCAG contrast checking (`buddhi scripts contrast`) preserving 100% backward compatibility for two-color positional checks while adding pair mode (`--bg`/`--fg`/`--profile` generating Markdown table rows for `REPORT.md`) and CSS triage mode (`--css`/`--page-bg`).
5. FastMCP server tools (`verify_a11y`, enhanced `check_contrast`) on `buddhi-mcp`.
6. Full SDD lifecycle integration across `/specify`, `/spec-plan`, `/spec-tasks`, `/implement`, `/verify`, and `/close-spec` with `A11Y-DECISIONS.md` promotion into durable OKF memory (`buddhi memory sdd-promote`).
7. Attribution in `ACKNOWLEDGMENTS.md`, `CHANGELOG.md` entry under `[Unreleased]`, and updated `README.md`.

## Technical Context

**Language/Version**: Python >= 3.10  
**Primary Dependencies**: `typer>=0.27.1`, `rich>=15.0.0`, `mcp[cli]>=1.2.0,<2.0.0`, standard library only for `verify_a11y` and `contrast`  
**Storage**: File-based markdown artifacts (`REPORT.md`, `EXCEPTIONS.md`, `A11Y-DECISIONS.md`, `ACCESSIBILITY.md`), OKF concept memory nodes (`.agents/memory/decisions/`)  
**Testing**: `uv run pytest`, `buddhi scripts verify-a11y --selftest`, `buddhi scripts contrast --selftest`, `uv run mypy src/ tests/`, `uv run ruff check .`  
**Target Platform**: Cross-platform (Windows, Linux, macOS)  
**Project Type**: CLI / Agent Harness Generator / FastMCP Server  
**Performance Goals**: Instant static analysis (<2s across repositories), strict token budgeting (<8,000 tokens per module)  
**Constraints**: Zero regressions on existing CLI commands, no external network dependencies during gate checks, strict file-size ratchet compliance (`buddhi scripts check-file-size --all`)

## AGENTS.md Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Project build & test commands adhered to (`uv run pytest`, `uv run ruff check .`, `uv run mypy src/ tests/`)
- [x] Architectural constraints respected (pure Python stdlib for verification scripts, idempotent template syncing in `init.py`, OKF v0.2 concept schemas in `memory/`)
- [x] No unapproved external dependencies introduced (uses existing `typer`, `rich`, `mcp`)

## Architectural Multi-Angle Evaluation

- **Fewest-slices**: Upstream `A11Y.md` files (`docs/en/A11Y.md`, `references/`, `templates/`, `tools/`) are ported directly into `buddhi-cli`'s template tree and script packages, minimizing unnecessary rewrites while customizing agent instructions for Antigravity tools.
- **Risk-first**: Upstream's `verify-a11y.py` is 76 KB (~19,000 tokens), which would immediately violate `buddhi scripts check-file-size --all` (8,000 token limit). We decompose it into modular Python packages (`src/buddhi/scripts/verify_a11y/`) so each submodule stays well below 5,000 tokens while preserving 100% logic and test fidelity.
- **Seam-quality**:
  - `buddhi scripts contrast` retains existing signature and return contract for positional calls, adding optional flag groups without breaks.
  - `A11Y-DECISIONS.md` seamlessly bridges into `buddhi memory sdd-promote` as durable `mem-decision-a11y-*` OKF nodes.
  - `antislop-human` remains focused on rapid anti-slop visual filtering while `a11y` handles normative WCAG criteria, WAI-ARIA APG patterns, and release evidence.

## Project Structure

### Documentation & Templates

```text
src/buddhi/templates/agents/
├── rules/
│   └── a11y.md                              # Always-on Antigravity A11Y constraint rule
├── skills/
│   └── a11y/
│       ├── SKILL.md                         # Adapted normative core skill
│       ├── references/                      # 31 lazy-loaded component/platform guides
│       │   ├── guide-buttons.md
│       │   ├── guide-forms.md
│       │   ├── guide-modals.md
│       │   ├── guide-navigation.md
│       │   └── ... (31 total)
│       └── templates/                       # 4 lifecycle governance templates
│           ├── REPORT.md
│           ├── EXCEPTIONS.md
│           ├── A11Y-DECISIONS.md
│           └── ACCESSIBILITY.md
├── agents/
│   └── frontend-specialist.md               # Updated frontend specialist with A11Y integration
└── skills/
    ├── specify/SKILL.md                     # Updated /specify with Compliance Profile prompt
    ├── spec-plan/SKILL.md                   # Updated /spec-plan with component reuse & guide mapping
    ├── spec-tasks/SKILL.md                  # Updated /spec-tasks with guide slice tags
    ├── implement/SKILL.md                   # Updated /implement with evidence capture & static checks
    ├── verify/SKILL.md                      # Updated /verify with verify-a11y & fresh-context subagent
    └── close-spec/SKILL.md                  # Updated /close-spec with A11Y decision promotion
```

### Source Code

```text
src/buddhi/
├── scripts/
│   ├── contrast.py                          # Enhanced contrast calculation (pair + CSS triage mode)
│   └── verify_a11y/                         # Modularized static gate engine (<8,000 tokens/file)
│       ├── __init__.py                      # Package entrypoint & runner
│       ├── models.py                        # Dataclasses & types
│       ├── artifacts.py                     # Artifact ladder, freshness, status, independence, exceptions
│       ├── antipatterns.py                  # 11 source anti-pattern checks & register suppressions
│       ├── coverage.py                      # 17 component signatures & contrast table recomputation
│       └── selftest.py                      # 31 built-in fixture test cases
├── commands/
│   └── scripts.py                           # Typer CLI commands: verify-a11y & contrast
├── mcp/
│   ├── server.py                            # FastMCP tools: verify_a11y & check_contrast
│   └── tools/
│       ├── a11y.py                          # MCP handler for verify_a11y
│       └── contrast.py                      # MCP handler for check_contrast
└── memory/
    └── sdd_promote.py                       # Promotion of A11Y-DECISIONS.md into OKF decision concepts

tests/
├── test_scripts_verify_a11y.py              # Unit & CLI tests for verify-a11y
├── test_scripts_contrast.py                 # Extended unit & CLI tests for contrast
├── test_cli_init_a11y.py                    # Scaffolding & idempotency tests for buddhi init
├── test_mcp_a11y.py                         # FastMCP tests for verify_a11y & check_contrast
└── test_memory_sdd_promote_a11y.py          # Promotion tests for A11Y-DECISIONS.md
```

## Implementation Phases

### Phase 1: Modular Static Gate & Contrast Engine
- Implement `src/buddhi/scripts/verify_a11y/` (`models.py`, `artifacts.py`, `antipatterns.py`, `coverage.py`, `selftest.py`, `__init__.py`).
- Extend `src/buddhi/scripts/contrast.py` with multi-pair mode (`--bg`, `--fg`, `--profile`), CSS triage mode (`--css`, `--page-bg`), alpha compositing, and self-tests.
- Wire CLI subcommands into `src/buddhi/commands/scripts.py` (`buddhi scripts verify-a11y` and updated `buddhi scripts contrast`).
- Verify via `terminal-runner`: `uv run buddhi scripts verify-a11y --selftest` and `uv run buddhi scripts contrast --selftest`.

### Phase 2: FastMCP Tools & SDD Memory Promotion
- Add `src/buddhi/mcp/tools/a11y.py` and register `verify_a11y` on `src/buddhi/mcp/server.py`.
- Update `src/buddhi/mcp/tools/contrast.py` to support `profile`, `bg`, `fg`, and `page_bg` in `check_contrast`.
- Update `src/buddhi/memory/sdd_promote.py` to extract entries from `A11Y-DECISIONS.md` into OKF decision nodes.

### Phase 3: Template Bundling & SDD Harness Customization
- Bundle `src/buddhi/templates/agents/rules/a11y.md`, `skills/a11y/SKILL.md` (customized for Antigravity), all 31 `references/guide-*.md`, and 4 `templates/*.md`.
- Update `src/buddhi/templates/agents/agents/frontend-specialist.md`.
- Update SDD skills: `specify`, `spec-plan`, `spec-tasks`, `implement`, `verify`, and `close-spec`.
- Sync `.agents/` in the local workspace to mirror updated templates.

### Phase 4: Test Suite & Verification
- Add comprehensive pytest suites: `test_scripts_verify_a11y.py`, `test_cli_init_a11y.py`, `test_mcp_a11y.py`, `test_memory_sdd_promote_a11y.py`, and update `test_scripts_contrast.py`.
- Run `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/ tests/`, `uv run pytest`, and `uv run buddhi scripts check-file-size --all`.

### Phase 5: Documentation & Attribution
- Update `ACKNOWLEDGMENTS.md` with dedicated section and full MIT license text for `fecarrico/A11Y.md`.
- Update `CHANGELOG.md` under `[Unreleased]` documenting the `A11Y.md` integration.
- Update `README.md` to document the new `a11y` skill, CLI scripts (`verify-a11y`, `contrast`), and MCP tools.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Split `verify_a11y` into 6 submodules | `verify-a11y.py` is 76 KB (~19,000 tokens) which breaches the project's 8,000-token ratchet ceiling | Single-file script would fail `buddhi scripts check-file-size --all` and prevent future clean maintenance |
| Bundling 31 references & 4 templates locally | Offline accessibility compliance without external GitHub raw fetches during agent execution | Pointing agents to external raw GitHub URLs introduces latency, rate limits, and network failure modes |
