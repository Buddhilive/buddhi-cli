# Implementation Plan: Rename `/tasks` Skill to `/spec-tasks` and Update Agent Harness Initialization

**Date**: 2026-10-26  
**Status**: Pending Approval  
**Context**: Avoid collision with Google Antigravity CLI's built-in slash command `/tasks` by renaming the SDD breakdown skill to `/spec-tasks` (mirroring the `/plan` -> `/spec-plan` convention) and ensuring automatic harness migration during `buddhi init`.

---

## 1. Objectives
1. Rename the bundled skill from `tasks` to `spec-tasks` so the slash command becomes `/spec-tasks`.
2. Update the active repository's `.agents/skills/tasks` to `.agents/skills/spec-tasks`.
3. Add migration logic `migrate_legacy_tasks_skill` in `src/buddhi/util/fsutil.py` and hook it into `buddhi init` (`src/buddhi/commands/init.py`) so existing consumer repositories automatically transition without collision.
4. Update references to `/tasks` across skills, templates, documentation (`AGENTS.md`, `README.md`), and SDD prerequisite messaging (`src/buddhi/sdd/common.py`, `check_prerequisites.py`, `setup_tasks.py`).
5. Add unit and end-to-end regression tests in `tests/test_cli_init.py` covering both clean scaffold and migration behavior.

---

## 2. Scope & Boundaries
- **In Scope**:
  - Slash command and skill definition: `/tasks` -> `/spec-tasks`.
  - Harness scaffold template and current `.agents/` harness sync.
  - Automatic migration for projects upgrading via `buddhi init`.
  - Safe replacement preserving non-command identifiers (`tasks.md`, `setup-tasks`, `--require-tasks`).
- **Out of Scope**:
  - The feature markdown artifact name `tasks.md` remains unchanged (it represents the document on disk, not the CLI command).
  - The CLI command `buddhi sdd setup-tasks` and `--require-tasks` flag remain unchanged.

---

## 3. Detailed Work Breakdown

### Step 1: Bundled Templates & Active Harness Skills
- **Move Directory**:
  - `src/buddhi/templates/agents/skills/tasks/` -> `src/buddhi/templates/agents/skills/spec-tasks/`
  - `.agents/skills/tasks/` -> `.agents/skills/spec-tasks/`
- **Update Frontmatter & Content**:
  - In `skills/spec-tasks/SKILL.md` (both template and `.agents/`):
    - `name: spec-tasks`
    - `description`: update trigger mention to `/spec-tasks`
    - Header: `# /spec-tasks`
- **Update Skill & Template References**:
  - `skills/README.md` (template & `.agents/`): change `/tasks` to `/spec-tasks`.
  - `skills/spec-plan/SKILL.md` (template & `.agents/`): update next step prompt to `/spec-tasks`.
  - `skills/implement/SKILL.md` (template & `.agents/`): update prerequisite validation message.
  - `templates/agents-template.md` (template & `.agents/`): step 3: `/spec-tasks`.
  - `templates/plan-template.md` (template & `.agents/`): update reference from `/tasks command` to `/spec-tasks command`.
  - `templates/tasks-template.md` (template & `.agents/`): update reference from `/tasks command` to `/spec-tasks command`.

### Step 2: Harness Migration Logic (`src/buddhi/util/fsutil.py` & `src/buddhi/commands/init.py`)
- In [fsutil.py](file:///c:/DevDojo/Buddhi/buddhi-cli/src/buddhi/util/fsutil.py):
  - Implement `TasksMigrationReport` and `migrate_legacy_tasks_skill(agents_dir: Path, project_root: Path | None = None) -> TasksMigrationReport`.
  - Directory Migration:
    - If `agents_dir / "skills" / "tasks"` exists and `spec-tasks` does not: move directory, update `name: spec-tasks`, `# /spec-tasks`, and replace `/tasks` with `/spec-tasks`.
    - If `agents_dir / "skills" / "tasks"` exists and `spec-tasks` already exists: remove `tasks` to avoid collisions.
  - Reference Updates:
    - Use word boundary regex `(?<![a-zA-Z0-9_/-])/tasks(?![a-zA-Z0-9_/-])` to update references across:
      - `project_root / "AGENTS.md"`
      - `agents_dir / "skills" / "spec-plan" / "SKILL.md"`
      - `agents_dir / "skills" / "implement" / "SKILL.md"`
      - `agents_dir / "skills" / "README.md"`
      - `agents_dir / "templates" / "agents-template.md"`
      - `agents_dir / "templates" / "plan-template.md"`
      - `agents_dir / "templates" / "tasks-template.md"`
- In [init.py](file:///c:/DevDojo/Buddhi/buddhi-cli/src/buddhi/commands/init.py):
  - Call `tasks_migration_report = migrate_legacy_tasks_skill(root / ".agents", project_root=root)`.
  - Report console output: `console.print("  migrated legacy tasks skill to spec-tasks")`.

### Step 3: SDD Prerequisite Messaging & Command Formatting
- In [common.py](file:///c:/DevDojo/Buddhi/buddhi-cli/src/buddhi/sdd/common.py):
  - Enhance `format_speckit_command` to handle `"tasks"` and `"plan"` canonical mappings:
    - `"tasks"` / `"spec-tasks"` -> `"/spec-tasks"`
    - `"plan"` / `"spec-plan"` -> `"/spec-plan"`
- In [check_prerequisites.py](file:///c:/DevDojo/Buddhi/buddhi-cli/src/buddhi/sdd/check_prerequisites.py) and [setup_tasks.py](file:///c:/DevDojo/Buddhi/buddhi-cli/src/buddhi/sdd/setup_tasks.py):
  - Ensure missing prerequisite guidance outputs `Run /spec-tasks ...` or `Run /spec-plan ...`.

### Step 4: Documentation
- Update root [AGENTS.md](file:///c:/DevDojo/Buddhi/buddhi-cli/AGENTS.md):
  - Change `3. /tasks — break down tasks by user story in tasks.md` to `3. /spec-tasks — break down tasks by user story in tasks.md`.
- Update [README.md](file:///c:/DevDojo/Buddhi/buddhi-cli/README.md):
  - Update SDD lifecycle and table references from `/tasks` to `/spec-tasks`.

### Step 5: Tests & Verification
- In [tests/test_cli_init.py](file:///c:/DevDojo/Buddhi/buddhi-cli/tests/test_cli_init.py):
  - Update `expected_skills` to assert `spec-tasks` and assert `not (agents_dir / "skills" / "tasks").exists()`.
  - Add `test_init_clean_directory_scaffolds_spec_tasks_and_not_tasks(tmp_path)`.
  - Add `test_init_migrates_existing_project_with_legacy_tasks_skill(tmp_path)`.
- Verify with tests and linter:
  - `uv run pytest tests/test_cli_init.py tests/test_sdd.py`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src/ tests/`

---

## 4. Files to be Modified / Created / Moved

| Action | Path | Description |
|---|---|---|
| **Move/Edit** | `src/buddhi/templates/agents/skills/tasks/` -> `spec-tasks/` | Rename skill directory & update `SKILL.md` |
| **Move/Edit** | `.agents/skills/tasks/` -> `spec-tasks/` | Rename skill directory & update `SKILL.md` |
| **Edit** | `src/buddhi/templates/agents/skills/README.md` | Update table and list to `/spec-tasks` |
| **Edit** | `.agents/skills/README.md` | Update table and list to `/spec-tasks` |
| **Edit** | `src/buddhi/templates/agents/skills/spec-plan/SKILL.md` | Update next step prompt to `/spec-tasks` |
| **Edit** | `.agents/skills/spec-plan/SKILL.md` | Update next step prompt to `/spec-tasks` |
| **Edit** | `src/buddhi/templates/agents/skills/implement/SKILL.md` | Update validation reference to `/spec-tasks` |
| **Edit** | `.agents/skills/implement/SKILL.md` | Update validation reference to `/spec-tasks` |
| **Edit** | `src/buddhi/templates/agents/templates/agents-template.md` | Update lifecycle item 3 to `/spec-tasks` |
| **Edit** | `.agents/templates/agents-template.md` | Update lifecycle item 3 to `/spec-tasks` |
| **Edit** | `src/buddhi/templates/agents/templates/plan-template.md` | Update reference to `/spec-tasks` |
| **Edit** | `.agents/templates/plan-template.md` | Update reference to `/spec-tasks` |
| **Edit** | `src/buddhi/templates/agents/templates/tasks-template.md` | Update reference to `/spec-tasks` |
| **Edit** | `.agents/templates/tasks-template.md` | Update reference to `/spec-tasks` |
| **Edit** | `src/buddhi/util/fsutil.py` | Add `migrate_legacy_tasks_skill` |
| **Edit** | `src/buddhi/commands/init.py` | Run and report `migrate_legacy_tasks_skill` |
| **Edit** | `src/buddhi/sdd/common.py` | Update `format_speckit_command` with canonical mapping |
| **Edit** | `src/buddhi/sdd/check_prerequisites.py` | Verify output messages |
| **Edit** | `src/buddhi/sdd/setup_tasks.py` | Verify output messages |
| **Edit** | `AGENTS.md` | Update lifecycle command to `/spec-tasks` |
| **Edit** | `README.md` | Update documentation references to `/spec-tasks` |
| **Edit** | `tests/test_cli_init.py` | Update expectations and add migration unit tests |
| **Create** | `.buddhi/plans/rename-tasks-to-spec-tasks.md` | Durable plan artifact |

