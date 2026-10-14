# Plan: Remove Heavy Graphics Skills

**Plan Path**: `.buddhi/plans/remove-graphics-skills.md`  
**Goal**: Remove the 5 heavy graphics-related custom skills (`renderer`, `launch-video`, `cinematic-shot`, `isometric-motion`, `xiaohei-illustrations`) and associated `--graphics` bundle flag from `buddhi-cli`, streamlining the package and cleaning up documentation.

---

## 1. Scope & Impact Analysis

- **Retained Custom Skills**: Only [`repo-to-skill`](file:///e:/Projects/buddhi-cli/src/buddhi/skills/repo_to_skill.py) remains as an optional custom skill.
- **SDD Lifecycle & General Skills**: All 23 SDD-complementary skills and 5 core SDD lifecycle enhancements remain 100% intact in `buddhi init`.
- **Pure-Python CLI Scripts**: All 3 scripts under `buddhi scripts` (`check-file-size`, `visual-parity-diff`, `receipts`) remain 100% intact.

---

## 2. Files to be Touched / Deleted

### Deletions
1. `src/buddhi/templates/custom_skills/cinematic_shot/` (entire directory)
2. `src/buddhi/templates/custom_skills/isometric_motion/` (entire directory)
3. `src/buddhi/templates/custom_skills/launch_video/` (entire directory)
4. `src/buddhi/templates/custom_skills/renderer/` (entire directory)
5. `src/buddhi/templates/custom_skills/xiaohei_illustrations/` (entire directory)
6. `tests/test_skills_graphics.py` (entire test file)

### Modifications
1. [`src/buddhi/skills/registry.py`](file:///e:/Projects/buddhi-cli/src/buddhi/skills/registry.py):
   - Remove dictionary entries for `"renderer"`, `"launch-video"`, `"cinematic-shot"`, `"isometric-motion"`, and `"xiaohei-illustrations"` in `_SKILL_REGISTRY` (lines 74–126).
   - Remove `GRAPHICS_SKILLS` list (lines 129–135).
2. [`src/buddhi/commands/skills.py`](file:///e:/Projects/buddhi-cli/src/buddhi/commands/skills.py):
   - Remove `GRAPHICS_SKILLS` from imports (line 10).
   - Remove footer text referring to `--graphics` in `_render_skills_table` (lines 44–45).
   - Remove Typer CLI options (`--renderer`, `--launch-video`, `--cinematic-shot`, `--isometric-motion`, `--xiaohei-illustrations`, `--graphics`) from `skills_main` callback (lines 56–85).
   - Remove install targets handling for the removed skills and bundle in `skills_main` (lines 107–121).
3. [`tests/test_cli_init_expanded_skills.py`](file:///e:/Projects/buddhi-cli/tests/test_cli_init_expanded_skills.py):
   - Update `CUSTOM_SKILLS_NOT_IN_INIT` to only contain `["repo-to-skill"]`.
4. [`tests/test_cli_skills.py`](file:///e:/Projects/buddhi-cli/tests/test_cli_skills.py):
   - Add negative assertions ensuring removed skills do not show in `buddhi skills` table.
   - Add negative assertions checking that `--graphics` and `--renderer` are rejected with non-zero exit codes.
5. [`ACKNOWLEDGMENTS.md`](file:///e:/Projects/buddhi-cli/ACKNOWLEDGMENTS.md):
   - Remove bullet for "Custom Graphics Skills" (line 66).
   - Remove sub-attributions for `wheresryan22` and `helloianneo` (lines 77–78).
6. [`README.md`](file:///e:/Projects/buddhi-cli/README.md):
   - Remove `--graphics` and individual graphics skill flags under `### buddhi skills`.
7. [`CHANGELOG.md`](file:///e:/Projects/buddhi-cli/CHANGELOG.md):
   - Remove entries regarding graphics skills under `## [Unreleased]`.
   - Clean up attribution note mentioning `wheresryan22` and `helloianneo`.

---

## 3. Ordered Implementation Steps

1. **Step 1: Delete Templates & Obsolete Test**
   - Delete `cinematic_shot`, `isometric_motion`, `launch_video`, `renderer`, and `xiaohei_illustrations` from `src/buddhi/templates/custom_skills/`.
   - Delete `tests/test_skills_graphics.py`.

2. **Step 2: Update Code Registry & CLI Command**
   - Clean up `_SKILL_REGISTRY` and remove `GRAPHICS_SKILLS` in `src/buddhi/skills/registry.py`.
   - Clean up options and install logic in `src/buddhi/commands/skills.py`.

3. **Step 3: Update Test Assertions**
   - Update `tests/test_cli_init_expanded_skills.py` (`CUSTOM_SKILLS_NOT_IN_INIT = ["repo-to-skill"]`).
   - Add negative tests in `tests/test_cli_skills.py`.

4. **Step 4: Update Documentation**
   - Edit `ACKNOWLEDGMENTS.md`, `README.md`, and `CHANGELOG.md`.

5. **Step 5: Code Quality Gates & Verification**
   - Run `uv run ruff check .` and `uv run ruff format .`
   - Run `uv run mypy src/ tests/`
   - Run `uv run pytest` across the entire test suite via `terminal-runner`.

---

## 4. Testing & Verification Plan

- **Targeted Test Execution**:
  `uv run pytest tests/test_cli_skills.py tests/test_cli_init_expanded_skills.py -v`
- **Full Test Suite**:
  `uv run pytest`
- **Lint & Format**:
  `uv run ruff check src tests`
  `uv run ruff format --check src tests`
- **Static Typing**:
  `uv run mypy src tests`

