# Feature Specification: Adapt `dzhng/skills` & Supportive Scripts into `buddhi-cli` SDD Workflow

**Feature Branch**: `004-adapt-dzhng-skills`

**Created**: 2026-10-24

**Status**: Ready for Planning

**Input**: User description: "Analyze the `skills` project located in `./temp/skills/` which has reusable AI agent skills for AI agents to function as software factories that explore ideas, write specs, implement, review, and run autonomous research. Then check the license of the project to clarify whether we can use the concepts in that project within our `buddhi-cli` project. If possible, do the following: 1. Adapt the skills, scripts etc., adhering to the Antigravity harness style, making them work well with Antigravity and including them in the `buddhi init` initialization... 2. Adapt those scripts in Python and integrate them into the `buddhi-cli` tool as tool commands under `buddhi scripts <flags and/or arguments>` 3. Update `ACKNOWLEDGMENTS.md`... 4. Update `README.md` and `CHANGELOG.md` under `[Unreleased]`."

---

## License Verification Summary

- **Upstream Repository**: [https://github.com/dzhng/skills](https://github.com/dzhng/skills) (`@dzhng/skills` v1.0.0)
- **Author & Copyright**: Copyright (c) 2026 David Zhang
- **License**: **MIT License** (permissive; allows commercial/non-commercial use, copying, modification, merging, publication, and distribution provided copyright and license notices are preserved).
- **Upstream Sub-Attributions**:
  - Matt Pocock (`retro` skill, MIT License, `Copyright (c) 2026 Matt Pocock`)
  - Matt Pocock & Thariq ("fog of war" and "discovering the map" concepts)
  - wheresryan22 (`Anatomy` skill adapted as `isometric-motion`)
  - helloianneo (`ian-xiaohei-illustrations` adapted as `xiaohei-illustrations`)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 - SDD-Complementary Skills & Enhanced SDD Lifecycle in `buddhi init` (Priority: P1)

When a developer runs `buddhi init` on a project, `buddhi-cli` scaffolds 23 adapted engineering, visual review, and skill-authoring skills from `dzhng/skills` into `.agents/skills/`, formatted according to official Google Antigravity `SKILL.md` conventions (`name`, `description`, progressive-disclosure `references/` and `assets/`, `terminal-runner` delegation, and `okf-context` / `buddhi-mcp` grounding). In addition, the existing 5 SDD lifecycle skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`) are enhanced with `dzhng/skills`'s software-factory practices (fog-of-war slicing, multi-perspective plan verification, maintenance checkpoints, `/review` + `/audit-choices` passes, visual verification, and `/close-spec` archiving) without replacing or duplicating the SDD workflow.

**Why this priority**: The core value of this feature is empowering Antigravity agents in any `buddhi init` workspace to explore unknowns, run fast research experiments, refactor cleanly, write/audit behavioral tests, review code and architectural choices, verify visuals, and close out specs seamlessly within the existing `.buddhi/specs/<branch>/` SDD workflow.

**Independent Test**: Run `uv run buddhi init <temp_dir>` and verify that all 23 complementary skills (plus their `references/` and `assets/` files) are created under `<temp_dir>/.agents/skills/`, follow Antigravity frontmatter/link conventions, reference `.buddhi/specs/<branch>/` and `buddhi scripts` commands instead of raw Node `.mjs` scripts, and leave out conflicting spec skills (`write-spec`, `implement-spec*`) and external CLI wrappers (`claude`, `codex`).

**Acceptance Scenarios**:

1. **Given** an uninitialized project directory, **When** the user runs `buddhi init`, **Then** `.agents/skills/` contains the 23 adapted complementary skills (`explore-unknowns`, `auto-research`, `refactor-clean`, `write-tests`, `audit-tests`, `audit-performance`, `ratchet-files`, `code-review`, `write-docs`, `review`, `audit-choices`, `handoff-spec`, `close-spec`, `eli5`, `retro`, `marketing-pages`, `design-with-images`, `compare-screenshots`, `screenshot-critique`, `preview-shots`, `write-skills`, `eval-skills`, `audit-agents`) along with their reference and asset files.
2. **Given** the scaffolded skills in `.agents/skills/`, **When** inspecting `explore-unknowns`, `audit-choices`, `handoff-spec`, and `close-spec`, **Then** they operate on `.buddhi/specs/<branch>/` (`spec.md`, `plan.md`, `tasks.md`, `choices.md`, and `.buddhi/specs/done/<branch>/`) and integrate cleanly with `/specify`, `/spec-plan`, `/tasks`, `/implement`, and `/verify`.
3. **Given** the existing SDD skills (`/specify`, `/spec-plan`, `/tasks`, `/implement`, `/verify`), **When** inspecting their instructions, **Then** they incorporate software-factory enhancements (upstream `/explore-unknowns` & `/auto-research` pointers in `/specify`; multi-angle slice/seam verification in `/spec-plan` & `/tasks`; periodic maintenance checkpoints, `/review`, and `/audit-choices` in `/implement`; `/compare-screenshots` + `/screenshot-critique` visual gates and `/close-spec` closeout prompt in `/verify`).
4. **Given** the scaffolded `.agents/skills/` directory after `buddhi init`, **When** listing skill directories, **Then** redundant spec skills (`write-spec`, `implement-spec`, `implement-spec-with-goal`, `implement-spec-with-codex`), external CLI wrappers (`claude`, `codex`), and heavy graphics skills (`isometric-motion`, `xiaohei-illustrations`, `cinematic-shot`, `launch-video`, `renderer`) are NOT eagerly scaffolded by `buddhi init`.

---

### User Story 2 - Pure-Python Supportive Scripts under `buddhi scripts` (Priority: P2)

Developers and Antigravity agents can execute deterministic helper scripts adapted from `dzhng/skills` directly via `buddhi scripts <subcommand>` in pure Python 3.10+ without needing Node.js or external npm packages:
- `buddhi scripts check-file-size` (supporting `ratchet-files`)
- `buddhi scripts visual-parity-diff` (supporting `compare-screenshots` and `design-with-images`)
- `buddhi scripts receipts` (supporting `screenshot-critique`)

**Why this priority**: Several high-leverage skills (`ratchet-files`, `compare-screenshots`, `screenshot-critique`) rely on deterministic CLI scripts for token-budget ratcheting, pixel/edge visual telemetry, and receipt verification of numeric claims and SHA-256 hashes. Porting them to pure Python under `buddhi scripts` ensures cross-platform reliability across Windows, macOS, and Linux.

**Independent Test**: Execute `uv run buddhi scripts check-file-size --selftest`, `uv run buddhi scripts visual-parity-diff --selftest`, and `uv run buddhi scripts receipts --selftest` (plus CLI invocations on test fixtures) and verify exit codes (`0` on pass, `1` on findings/violations, `2` on invalid usage) and JSON/text outputs.

**Acceptance Scenarios**:

1. **Given** a git repository, **When** running `buddhi scripts check-file-size --all [--max-tokens 8000]`, **Then** it inspects git-tracked source files (excluding `linguist-generated`/`linguist-vendored` attributes and files containing `@ratchet-files-ignore` in their first 10 lines), prints any files exceeding `max_tokens * 4` bytes sorted largest-first (`<tokens>\t<path>`), and exits `1` if violations exist or `0` if all pass.
2. **Given** staged files in a git repository, **When** running `buddhi scripts check-file-size <path>...`, **Then** it enforces the pre-commit ratchet: new files or previously compliant files that cross the token ceiling fail (`exit 1`), already-oversized files in `HEAD` (tracking renames) that grew fail (`exit 1`), and already-oversized files that shrank or stayed the same size pass (`exit 0`).
3. **Given** a directory of candidate PNGs (`--candidate-dir` or `CANDIDATE_DIR`), **When** running `buddhi scripts visual-parity-diff` without a reference directory, **Then** it computes solo scene metrics (`colorBuckets`, `colorEntropyBits`, `edgeDensity`, `dominantColorShare`, `transparentShare`, `luminanceMean`, `luminanceP5`, `luminanceP95`, `luminanceContrast`) and writes `<out-dir>/scene-metrics.json`.
4. **Given** matching PNGs in `--reference-dir` (`REFERENCE_DIR`) and `--candidate-dir` (`CANDIDATE_DIR`), **When** running `buddhi scripts visual-parity-diff`, **Then** it computes grayscale MAE/RMSE, diff ratios (`16`/`32`/`64`), Sobel edge energy and edge diff ratio, anti-aliased `pixelmatch` ratio, and composite `parityDistance`, writes 8 diagnostic PNGs per pair (plus optional crop metrics/PNGs when `--crops-json` / `CROPS_JSON` is provided), and writes `<out-dir>/visual-parity-diff.json`.
5. **Given** a visual critique markdown report, **When** running `buddhi scripts receipts [--json | --label] [--window N] [--base DIR] <report.md>`, **Then** it verifies that every numeric/hex measurement claim in prose appears in the output of a nearby executed command receipt block (`ran = true`) and that every referenced artifact file path and 64-hex SHA-256 digest matches the file on disk, exiting `0` when all claims are backed or `1` when any unsupported claim or missing/mismatched artifact is found.

---

### User Story 3 - Optional Graphics Skills via `buddhi skills` (Priority: P3)

Developers working on rich visual explainers, WebGPU renderers, launch videos, or editorial illustrations can selectively install the 5 graphics skills (`renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, `xiaohei-illustrations`) into `.agents/skills/` via `buddhi skills` using individual flags or the `--graphics` bundle flag.

**Why this priority**: Keeps `buddhi init` fast and lean for standard software projects while making all 5 specialized graphics skills (including `isometric-motion`'s kit/references and `xiaohei-illustrations`'s style references/examples) readily installable on demand.

**Independent Test**: Run `uv run buddhi skills` to verify the inventory table lists the 5 graphics skills and `--graphics`, then run `uv run buddhi skills --graphics --path <temp_dir>` (and individual flags) to confirm installation into `<temp_dir>/.agents/skills/`.

**Acceptance Scenarios**:

1. **Given** any terminal session, **When** the user runs `buddhi skills`, **Then** the inventory table displays `repo-to-skill` alongside `renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, and `xiaohei-illustrations` (and notes the `--graphics` bundle flag).
2. **Given** a target project directory, **When** the user runs `buddhi skills --isometric-motion --path <dir>` or `buddhi skills --graphics --path <dir>`, **Then** the selected skill(s) and their bundled `references/`, `assets/`, `kit/`, and `scripts/` subdirectories are copied into `<dir>/.agents/skills/<skill-name>/`.

---

### User Story 4 - License Attribution & Documentation Updates (Priority: P4)

Project documentation clearly credits `https://github.com/dzhng/skills` in `ACKNOWLEDGMENTS.md` and documents all new skills, enhanced SDD capabilities, `buddhi scripts` commands, and `buddhi skills` flags in `README.md` and `CHANGELOG.md` (under `[Unreleased]`).

**Why this priority**: Satisfies the MIT License attribution requirement and ensures users and AI agents can discover and use the newly integrated capabilities.

**Independent Test**: Inspect `ACKNOWLEDGMENTS.md`, `README.md`, and `CHANGELOG.md` to confirm accurate attribution, license text, CLI command documentation, and changelog entries under `[Unreleased]`.

**Acceptance Scenarios**:

1. **Given** `ACKNOWLEDGMENTS.md` at the repository root, **When** inspected, **Then** it includes a dedicated section for `dzhng/skills` (`https://github.com/dzhng/skills`, David Zhang, MIT License), lists the adapted skills and Python CLI scripts, credits upstream contributors (Matt Pocock, Thariq, wheresryan22, helloianneo), and includes the full MIT license text.
2. **Given** `README.md` and `CHANGELOG.md`, **When** inspected, **Then** `README.md` documents the new skills in `.agents/skills/`, the new `buddhi scripts` commands (`check-file-size`, `visual-parity-diff`, `receipts`), the new `buddhi skills` flags, and the acknowledgment link, while `CHANGELOG.md` records all additions and enhancements under `## [Unreleased]`.

---

### Edge Cases

- **Idempotency during `buddhi init`**: Rerunning `buddhi init` on an existing project MUST only add missing skill files under `.agents/skills/` and never overwrite user-modified `SKILL.md` files (`sync_template_tree` behavior).
- **Non-git or empty directories in `check-file-size`**: When `buddhi scripts check-file-size` is invoked outside a git repository or with no matching source files, it must fail gracefully or exit `0` (when no files match) with a clear message rather than an unhandled traceback.
- **Dimension mismatch or corrupt PNG in `visual-parity-diff`**: When reference and candidate PNGs have mismatched dimensions or no common `.png` filenames exist, `buddhi scripts visual-parity-diff` must print a descriptive error to stderr and exit with a non-zero code (`2` or `1`).
- **Ambiguous multi-hash lines in `receipts`**: When a single line in a critique report contains multiple artifact paths and multiple 64-hex hashes that cannot be paired 1-to-1, `buddhi scripts receipts` must fail closed and report an ambiguous hash-to-artifact pairing error.
- **Cross-platform `preview-shots`**: Because the upstream `preview-shots` skill used macOS-only `open -a Preview` and `osascript`, the adapted `preview-shots` skill must provide cross-platform commands (Windows PowerShell / default viewer, macOS `Preview`, Linux `xdg-open`) plus Antigravity artifact preview guidance.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `buddhi init` MUST scaffold the 23 adapted SDD-complementary skills (`explore-unknowns`, `auto-research`, `refactor-clean`, `write-tests`, `audit-tests`, `audit-performance`, `ratchet-files`, `code-review`, `write-docs`, `review`, `audit-choices`, `handoff-spec`, `close-spec`, `eli5`, `retro`, `marketing-pages`, `design-with-images`, `compare-screenshots`, `screenshot-critique`, `preview-shots`, `write-skills`, `eval-skills`, `audit-agents`) and their supporting `references/` and `assets/` subdirectories into `.agents/skills/`.
- **FR-002**: Every adapted `SKILL.md` MUST adhere to Google Antigravity skill conventions: valid YAML frontmatter (`name`, `description`), native subagent delegation (`invoke_subagent` / `terminal-runner` / `image-generator` / `research`), `okf-context` (`buddhi_search`, `buddhi_read`) codebase grounding where applicable, and relative links to `references/` or `assets/`.
- **FR-003**: Adapted skills that interact with specifications (`explore-unknowns`, `auto-research`, `audit-choices`, `handoff-spec`, `close-spec`, `eli5`) MUST target `buddhi-cli`'s SDD directory structure (`.buddhi/specs/<branch>/spec.md`, `plan.md`, `tasks.md`, `research.md`, `choices.md`, and `.buddhi/specs/done/<branch>/`) rather than a competing `specs/<feature>/slices/` layout.
- **FR-004**: Existing SDD skills (`specify`, `spec-plan`, `tasks`, `implement`, `verify`) MUST be updated to cross-reference and leverage the new complementary skills (e.g., `/explore-unknowns` and `/auto-research` before `/specify`; multi-angle slice/seam checks in `/spec-plan` and `/tasks`; maintenance checkpoints, `/review`, and `/audit-choices` in `/implement`; `/compare-screenshots`, `/screenshot-critique`, and `/close-spec` in `/verify`).
- **FR-005**: `buddhi scripts check-file-size` MUST be implemented in pure Python 3.10+ supporting `--all`, `--max-tokens <N>` (default `8000`), `[<path>...]`, and `--selftest`, replicating the exact git attribute filtering (`linguist-generated`, `linguist-vendored`), `@ratchet-files-ignore` first-10-lines marker, and `HEAD` ratchet semantics of `check-file-size.mjs`.
- **FR-006**: `buddhi scripts visual-parity-diff` MUST be implemented in pure Python 3.10+ (stdlib-only PNG decoding/encoding including filter types 0–4, Rec.709 luminance, 4-bit RGB entropy buckets, 3x3 Sobel edge detection, YIQ anti-aliased `pixelmatch`, and `parityDistance`), supporting both CLI options (`--candidate-dir`, `--reference-dir`, `--out-dir`, `--repo-root`, `--report-order`, `--crops-json`, `--selftest`) and environment variables (`CANDIDATE_DIR`, `REFERENCE_DIR`, `OUT_DIR`, `REPO_ROOT`, `REPORT_ORDER`, `CROPS_JSON`).
- **FR-007**: `buddhi scripts receipts` MUST be implemented in pure Python 3.10+ supporting `--json`, `--label`, `--window <N>` (default `4`), `--base <dir>`, `--selftest`, and `<report.md>...` (including `-` for stdin), verifying command-output receipt blocks (`buddhi` included in the allowed tool list) against prose numeric/hex measurement claims and validating artifact files and 64-hex SHA-256 digests.
- **FR-008**: `buddhi skills` MUST register the 5 graphics skills (`renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, `xiaohei-illustrations`) under `src/buddhi/templates/custom_skills/` with individual CLI flags (`--renderer`, `--launch-video`, `--cinematic-shot`, `--isometric-motion`, `--xiaohei-illustrations`) plus a `--graphics` bundle flag.
- **FR-009**: `ACKNOWLEDGMENTS.md`, `README.md`, `CHANGELOG.md` (under `[Unreleased]`), and `AGENTS.md` / `agents-template.md` MUST be updated to document and credit `https://github.com/dzhng/skills`.

### Key Entities

- **Default Harness Skill Template (`src/buddhi/templates/agents/skills/<name>/`)**: Skill package scaffolded automatically by `buddhi init` into `.agents/skills/<name>/`.
- **Custom Skill Template (`src/buddhi/templates/custom_skills/<name>/`)**: On-demand skill package registered in `src/buddhi/skills/registry.py` and installed via `buddhi skills --<flag>`.
- **CLI Script Subcommand (`src/buddhi/scripts/<script_name>.py` & `src/buddhi/commands/scripts.py`)**: Pure-Python utility exposed under `buddhi scripts <name>`.
- **Choices Ledger (`.buddhi/specs/<branch>/choices.md`)**: Decision audit artifact produced by `/audit-choices` recording unprompted architectural/implementation choices (`sound`, `unsound`, `needs-user`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running `buddhi init` on a clean project scaffolds all 23 new SDD-complementary skills and their reference/asset files into `.agents/skills/` with zero errors and 100% valid YAML frontmatter (`name` and `description`).
- **SC-002**: `buddhi scripts check-file-size --selftest`, `buddhi scripts visual-parity-diff --selftest`, and `buddhi scripts receipts --selftest` all pass with exit code `0` using only Python standard library modules.
- **SC-003**: `buddhi skills --graphics --path <target>` installs all 5 graphics skills (`renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, `xiaohei-illustrations`) cleanly into `<target>/.agents/skills/`.
- **SC-004**: `uv run pytest`, `uv run ruff check src tests`, and `uv run mypy src` pass with exit code `0` across the entire test suite and typechecker.

---

## Assumptions

- Target projects initialized with `buddhi init` use Google Antigravity as their primary agent harness.
- External CLI agent wrappers (`claude`, `codex`, `implement-spec-with-codex`) are excluded because Antigravity provides native subagent orchestration (`invoke_subagent`).
- Pure-Python PNG processing in `visual-parity-diff` operates on standard 8-bit RGB/RGBA/grayscale/palette PNGs generated by headless browsers and screenshot tools without requiring third-party C extensions.
