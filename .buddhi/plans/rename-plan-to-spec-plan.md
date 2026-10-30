# Implementation Plan: Rename SDD Skill `plan` to `spec-plan`

## 1. Summary
Google Antigravity provides a built-in `/plan` slash command. Currently, `buddhi-cli` bundles an SDD planning skill named `plan` (`.agents/skills/plan/SKILL.md`), creating a command collision with Antigravity's built-in slash command.

This plan renames our Spec-Driven Development planning skill and slash command to `spec-plan` (`/spec-plan`), while keeping underlying artifacts intact (`plan.md`, `plan-template.md`, `buddhi sdd setup-plan`, `buddhi docs plan`). It also adds automatic migration logic to `buddhi init` so that re-initializing an existing project automatically transitions `.agents/skills/plan` to `.agents/skills/spec-plan`, updates references in documentation, and removes the colliding skill directory without losing user customizations.

---

## 2. Files to be Touched

### CLI & Migration Logic
- [`src/buddhi/util/fsutil.py`](file:///e:/Projects/buddhi-cli/src/buddhi/util/fsutil.py):
  - Add `PlanMigrationReport` dataclass.
  - Implement `migrate_legacy_plan_skill(root: Path, agents_dir: Path | None = None) -> PlanMigrationReport`.
  - Update `migrate_legacy_workflows()` to map any legacy `plan.md` workflow to `spec-plan`.
- [`src/buddhi/commands/init.py`](file:///e:/Projects/buddhi-cli/src/buddhi/commands/init.py):
  - Call `migrate_legacy_plan_skill()` before `sync_template_tree()`.
  - Update init docstring and reporting output.

### Bundled Templates (`src/buddhi/templates/agents/`)
- Directory move: `src/buddhi/templates/agents/skills/plan/` -> `src/buddhi/templates/agents/skills/spec-plan/`
- [`src/buddhi/templates/agents/skills/spec-plan/SKILL.md`](file:///e:/Projects/buddhi-cli/src/buddhi/templates/agents/skills/spec-plan/SKILL.md): Update frontmatter `name: spec-plan`, title `# /spec-plan`, and references to `/spec-plan`.
- [`src/buddhi/templates/agents/templates/agents-template.md`](file:///e:/Projects/buddhi-cli/src/buddhi/templates/agents/templates/agents-template.md): Update SDD step 2 from `/plan` to `/spec-plan`.
- [`src/buddhi/templates/agents/rules/harness-core.md`](file:///e:/Projects/buddhi-cli/src/buddhi/templates/agents/rules/harness-core.md): Update references from `/plan` to `/spec-plan`.
- [`src/buddhi/templates/agents/skills/specify/SKILL.md`](file:///e:/Projects/buddhi-cli/src/buddhi/templates/agents/skills/specify/SKILL.md): Update next step prompt to `/spec-plan`.
- [`src/buddhi/templates/agents/skills/implement/SKILL.md`](file:///e:/Projects/buddhi-cli/src/buddhi/templates/agents/skills/implement/SKILL.md): Update references to `/spec-plan`.
- [`src/buddhi/templates/agents/skills/README.md`](file:///e:/Projects/buddhi-cli/src/buddhi/templates/agents/skills/README.md): Update catalog listing `plan` to `spec-plan`.

### Active Workspace Harness (`.agents/` and Workspace Root)
- Directory move: `.agents/skills/plan/` -> `.agents/skills/spec-plan/`
- [`.agents/skills/spec-plan/SKILL.md`](file:///e:/Projects/buddhi-cli/.agents/skills/spec-plan/SKILL.md): Update frontmatter `name: spec-plan`, title `# /spec-plan`, and references.
- [`AGENTS.md`](file:///e:/Projects/buddhi-cli/AGENTS.md): Update SDD step 2 from `/plan` to `/spec-plan`.
- [`.agents/rules/harness-core.md`](file:///e:/Projects/buddhi-cli/.agents/rules/harness-core.md): Update `/plan` references to `/spec-plan`.
- [`.agents/skills/specify/SKILL.md`](file:///e:/Projects/buddhi-cli/.agents/skills/specify/SKILL.md): Update next step prompt to `/spec-plan`.
- [`.agents/skills/implement/SKILL.md`](file:///e:/Projects/buddhi-cli/.agents/skills/implement/SKILL.md): Update references to `/spec-plan`.
- [`.agents/skills/README.md`](file:///e:/Projects/buddhi-cli/.agents/skills/README.md): Update catalog listing `plan` to `spec-plan`.

### Tests
- [`tests/test_cli_init.py`](file:///e:/Projects/buddhi-cli/tests/test_cli_init.py):
  - Update `expected_skills` to assert `spec-plan` instead of `plan`.
  - Update `test_init_migrates_and_removes_legacy_workflows` for `spec-plan`.
  - Add `test_init_clean_directory_scaffolds_spec_plan_and_not_plan`.
  - Add `test_init_migrates_existing_project_with_legacy_plan_skill`.
- [`tests/test_fsutil.py`](file:///e:/Projects/buddhi-cli/tests/test_fsutil.py):
  - Add unit tests for `migrate_legacy_plan_skill`: directory migration, frontmatter updates, user customization preservation, reference replacement without affecting `/quick-plan`, and idempotency.

---

## 3. Ordered Implementation Steps

1. **Skill & Template Renaming**:
   - Rename `src/buddhi/templates/agents/skills/plan` to `src/buddhi/templates/agents/skills/spec-plan`.
   - Update frontmatter in `src/buddhi/templates/agents/skills/spec-plan/SKILL.md` (`name: spec-plan`, description `/spec-plan`, title `# /spec-plan`).
   - Rename `.agents/skills/plan` to `.agents/skills/spec-plan` and update its `SKILL.md`.
2. **Template & Documentation References**:
   - Update `src/buddhi/templates/agents/templates/agents-template.md` (SDD step 2 -> `/spec-plan`).
   - Update `src/buddhi/templates/agents/rules/harness-core.md` (`/plan` -> `/spec-plan`).
   - Update `src/buddhi/templates/agents/skills/specify/SKILL.md` (`/plan` -> `/spec-plan`).
   - Update `src/buddhi/templates/agents/skills/implement/SKILL.md` (`/plan` -> `/spec-plan`).
   - Update `src/buddhi/templates/agents/skills/README.md` (`spec-plan`).
   - Update workspace `AGENTS.md`, `.agents/rules/harness-core.md`, `.agents/skills/specify/SKILL.md`, `.agents/skills/implement/SKILL.md`, and `.agents/skills/README.md`.
3. **Migration Logic in `fsutil.py` & `init.py`**:
   - Implement `migrate_legacy_plan_skill(root: Path, agents_dir: Path | None = None) -> PlanMigrationReport`:
     - Checks if `.agents/skills/plan` exists.
     - If `.agents/skills/spec-plan` doesn't exist, moves `.agents/skills/plan` to `spec-plan` and updates `SKILL.md` frontmatter (`name: spec-plan`, `# /spec-plan`).
     - If `.agents/skills/spec-plan` exists, removes `.agents/skills/plan` via `shutil.rmtree()`.
     - Updates `/plan` references across `AGENTS.md`, `rules/harness-core.md`, and `skills/specify/SKILL.md` using regex negative lookahead/lookbehind `(?<![a-zA-Z0-9_])/plan(?![a-zA-Z0-9_-])` (protecting `/quick-plan`).
   - In `init()`: Call `migrate_legacy_plan_skill(root, root / ".agents")` prior to `sync_template_tree()`.
   - Update `migrate_legacy_workflows()` to convert legacy `workflows/plan.md` to `skills/spec-plan`.
4. **Unit & Integration Tests**:
   - Add unit tests in `tests/test_fsutil.py` for all migration conditions and reference protections.
   - Update existing tests in `tests/test_cli_init.py` (`expected_skills`).
   - Add re-init migration tests in `tests/test_cli_init.py`.

---

## 4. Testing & Verification

- **Verification Commands**:
  - `uv run pytest tests/test_fsutil.py -v`
  - `uv run pytest tests/test_cli_init.py -v`
  - `uv run pytest` (full suite)
- **Manual Verification**:
  - Run `buddhi init` in a temporary test directory containing an initialized `.agents/skills/plan/` harness.
  - Verify `.agents/skills/plan/` is gone, `.agents/skills/spec-plan/SKILL.md` is present and functional, and `AGENTS.md` reflects `/spec-plan`.

