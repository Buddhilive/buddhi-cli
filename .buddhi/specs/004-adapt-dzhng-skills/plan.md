# Implementation Plan: Adapt `dzhng/skills` & Supportive Scripts into `buddhi-cli` SDD Workflow

**Branch**: `004-adapt-dzhng-skills` | **Date**: 2026-10-24 | **Spec**: [.buddhi/specs/004-adapt-dzhng-skills/spec.md](spec.md)

**Input**: Feature specification from `/.buddhi/specs/004-adapt-dzhng-skills/spec.md`

---

## Summary

Integrate software-factory capabilities adapted from [dzhng/skills](https://github.com/dzhng/skills) (MIT License, Copyright (c) 2026 David Zhang) into `buddhi-cli`:
1. **SDD-Complementary Skills**: Adapt 23 engineering, visual review, and authoring skills into `src/buddhi/templates/agents/skills/` conforming to Google Antigravity conventions (`SKILL.md` frontmatter, `okf-context` graph grounding, `terminal-runner` execution, and `.buddhi/specs/<branch>/` paths) for automatic scaffolding during `buddhi init`.
2. **Enhanced SDD Lifecycle**: Weave software-factory practices (pre-spec research, multi-perspective plan verification, maintenance checkpoints, `/review` + `/audit-choices` passes, visual verification gates, and `/close-spec` spec archival) into the existing 5 SDD skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`) without replacing or duplicating the SDD workflow.
3. **Pure-Python CLI Scripts (`buddhi scripts`)**: Implement 3 standalone, zero-external-dependency Python 3.10+ CLI tools (`check-file-size`, `visual-parity-diff`, `receipts`) under `src/buddhi/scripts/` and expose them in `src/buddhi/commands/scripts.py` with `--selftest` support.
4. **Custom Graphics Skills (`buddhi skills`)**: Package the 5 specialized graphics skills (`renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, `xiaohei-illustrations`) in `src/buddhi/templates/custom_skills/` and register them in `buddhi skills` with individual flags and a `--graphics` bundle flag.
5. **Attribution & Documentation**: Update `ACKNOWLEDGMENTS.md`, `README.md`, `CHANGELOG.md` (under `[Unreleased]`), and `AGENTS.md` / `agents-template.md`.

---

## Technical Context

**Language/Version**: Python >= 3.10

**Primary Dependencies**:
- Existing runtime: `typer`, `rich`, `tree-sitter`, `mcp`, `sqlite3`
- Standard library modules for new scripts: `zlib`, `struct`, `math`, `subprocess`, `hashlib`, `pathlib`, `re`, `json`, `sys`
- **Zero new external dependencies**: No Pillow, NumPy, or Node.js required.

**Storage**:
- File-based templates and configurations: `.agents/skills/`, `.buddhi/specs/<branch>/`, `src/buddhi/templates/`

**Testing**:
- `pytest` with `tmp_path`, `typer.testing.CliRunner(mix_stderr=False)`, `monkeypatch`
- Built-in `--selftest` modes for all scripts

**Target Platform**:
- Cross-platform: Windows, macOS, Linux

**Project Type**:
- CLI and agent harness generator

**Performance Goals**:
- `check-file-size`: Git index evaluation of 1,000 files in < 500ms
- `visual-parity-diff`: Pure Python decode, Rec.709 grayscale, 3x3 Sobel convolution, and diff generation of 1080p PNGs in < 3s without C extensions
- `receipts`: Markdown parsing and SHA-256 validation of reports in < 100ms

**Constraints**:
- Absolute compatibility with existing `buddhi init` idempotency (never clobber existing user customizations)
- Non-breaking enhancement to the existing 5 SDD lifecycle skills
- Pure Python 3.10+ stdlib implementations for all supportive scripts

---

## AGENTS.md Compliance Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- [x] Project build & test commands adhered to (`uv run pytest`, `uv run ruff check .`, `uv run mypy src/ tests/`)
- [x] Architectural constraints respected (Grounded Changes, Evidence-Based Verification via `terminal-runner`, Clean Code & Typings)
- [x] No unapproved external dependencies introduced (pure Python stdlib used for scripts)

---

## Project Structure

### Documentation (this feature)

```text
.buddhi/specs/004-adapt-dzhng-skills/
├── spec.md              # Feature specification
├── plan.md              # This implementation plan
├── research.md          # Upstream analysis, license checks, and architecture decisions
├── contracts/           # CLI argument and JSON schema definitions
│   ├── check-file-size.json
│   ├── visual-parity-diff.json
│   └── receipts.json
└── tasks.md             # Phase 2 output (/tasks command)
```

### Source Code (repository root)

```text
src/buddhi/
├── commands/
│   ├── init.py                         # Updated to report newly scaffolded skills
│   ├── scripts.py                      # Exposed subcommands: check-file-size, visual-parity-diff, receipts
│   └── skills.py                       # Exposed flags: graphics flags + --graphics bundle
├── scripts/
│   ├── check_file_size.py              # Pure Python port of check-file-size.mjs
│   ├── visual_parity_diff.py           # Pure Python PNG codec + visual telemetry & diffing
│   └── receipts.py                     # Pure Python markdown critique & SHA-256 verifier
├── skills/
│   └── registry.py                     # Registered 5 graphics skills + bundle
└── templates/
    ├── agents/
    │   ├── skills/                     # 23 SDD-complementary skills scaffolded by buddhi init:
    │   │   ├── audit-agents/
    │   │   ├── audit-choices/
    │   │   ├── audit-performance/
    │   │   ├── audit-tests/
    │   │   ├── auto-research/
    │   │   ├── close-spec/
    │   │   ├── code-review/
    │   │   ├── compare-screenshots/
    │   │   ├── design-with-images/
    │   │   ├── eli5/
    │   │   ├── eval-skills/
    │   │   ├── explore-unknowns/
    │   │   ├── handoff-spec/
    │   │   ├── marketing-pages/
    │   │   ├── preview-shots/
    │   │   ├── ratchet-files/
    │   │   ├── refactor-clean/
    │   │   ├── retro/
    │   │   ├── review/
    │   │   ├── screenshot-critique/
    │   │   ├── write-docs/
    │   │   ├── write-skills/
    │   │   └── write-tests/
    │   └── skills/                     # 5 enhanced existing SDD skills:
    │       ├── specify/SKILL.md
    │       ├── spec-plan/SKILL.md
    │       ├── tasks/SKILL.md
    │       ├── implement/SKILL.md
    │       └── verify/SKILL.md
    └── custom_skills/                  # 5 on-demand graphics skills:
        ├── renderer/
        ├── launch_video/
        ├── cinematic_shot/
        ├── isometric_motion/
        └── xiaohei_illustrations/

tests/
├── test_scripts_check_file_size.py     # Tests for file size ratcheting and pre-commit logic
├── test_scripts_visual_parity_diff.py  # Tests for PNG codec, metrics, Sobel, and diff artifacts
├── test_scripts_receipts.py            # Tests for receipts parsing, claim logic, and SHA-256
├── test_skills_graphics.py             # Tests for custom graphics skill installation & bundle
├── test_cli_scripts.py                 # CLI routing and argument testing
└── test_cli_init.py                    # Verification of all 23 skills on init and frontmatter

Root Documentation:
├── ACKNOWLEDGMENTS.md                  # Attribution for dzhng/skills + MIT license
├── README.md                           # Documentation for new skills, scripts, and flags
├── CHANGELOG.md                        # Recorded changes under [Unreleased]
└── AGENTS.md                           # Root conventions updated
```

**Structure Decision**:
- Follows the established single-project Python architecture under `src/buddhi/` and `tests/`.
- Uses package separation: default harness templates in `buddhi.templates.agents` (scaffolded by `buddhi init`) vs custom selective templates in `buddhi.templates.custom_skills` (installed on demand via `buddhi skills`).

---

## Complexity Tracking

| Violation / Trade-off | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Pure Python PNG encoder/decoder in `visual_parity_diff.py` (no Pillow or OpenCV) | Eliminates external C-extension binary dependencies, ensuring seamless installation across all OS platforms (Windows, macOS, Linux) via `pip` or `pipx`. | Requiring `Pillow` or `numpy` can cause wheel/compiler issues in minimal container/agent environments and adds installation overhead. |
| Exposing 5 graphics skills via `buddhi skills` rather than `buddhi init` | Prevents bloating the default `.agents/skills/` directory on projects that only need software-factory SDD tools. | Copying all 34 skills eagerly on every `buddhi init` would pollute the agent context window with irrelevant 3D/video skills. |
| Weaving `write-spec`/`implement-spec` into existing SDD skills instead of adding separate skills | Guarantees a single unified Spec-Driven Development workflow centered on `.buddhi/specs/<branch>/` without command collisions. | Having both `/specify` and `/write-spec`, or `/implement` and `/implement-spec`, would confuse agents and users regarding which workflow to follow. |
