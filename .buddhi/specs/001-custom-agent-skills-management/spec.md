# Feature Specification: Custom Agent Skills Management (`buddhi skills`)

**Feature Branch**: `001-custom-agent-skills-management`

**Created**: 2026-09-06

**Status**: Specified

**Input**: User description: "implement a new buddhi-cli command for adding new agent skills to the initial agent harness, as needed. The main command is buddhi skills and it accepts a flag. For this scope, we accept flag --repo-to-skill which will add repo-to-skill skill which is formatted and optimized to Google Antigravity, based on the repo-to-skill GitHub repo. If user just enter buddhi skills, list down all available custom skills and their respective flags. Keep provision for future implementations."

---

## User Scenarios & Testing

### User Story 1 - Discover Available Custom Skills (Priority: P1)

As an AI engineer or developer using `buddhi-cli`,
I want to run `buddhi skills` without any flags
So that I can see a formatted list of all available custom agent skills, what they do, and their respective CLI flags.

**Why this priority**:
Discoverability is essential. Users need an immediate, zero-friction way to inspect which skills can be added to their agent harness and what CLI flags to use.

**Independent Test**:
Run `buddhi skills` in any terminal. Verify that it prints a clean table or list of available custom skills including `--repo-to-skill`, its human-readable title, and its description.

**Acceptance Scenarios**:

1. **Given** `buddhi-cli` is installed,
   **When** the user runs `buddhi skills` (with no flags),
   **Then** the CLI displays a formatted table/list containing:
     - Skill name: `repo-to-skill`
     - Flag: `--repo-to-skill`
     - Description: Overview explaining that it generates agent skills from any GitHub repo, optimized for Google Antigravity
   **And** exits with status code 0.

---

### User Story 2 - Install `repo-to-skill` into Agent Harness (Priority: P1)

As a developer building or maintaining an AI agent harness with Antigravity,
I want to run `buddhi skills --repo-to-skill`
So that the `repo-to-skill` skill (optimized for Google Antigravity) is installed into my project's `.agents/skills/repo-to-skill/` directory.

**Why this priority**:
Delivers the core functional capability: empowering Antigravity agents to turn external GitHub repositories into full agent skills with compliant YAML frontmatter, references, and helper scripts.

**Independent Test**:
In an initialized or blank directory, run `buddhi skills --repo-to-skill`. Verify that `.agents/skills/repo-to-skill/` is populated with `SKILL.md`, `references/`, and `scripts/`, correctly formatted for Antigravity.

**Acceptance Scenarios**:

1. **Given** a target project directory,
   **When** the user runs `buddhi skills --repo-to-skill`,
   **Then** `repo-to-skill` is copied into `.agents/skills/repo-to-skill/`
   **And** `SKILL.md` contains valid Antigravity frontmatter (`name: repo-to-skill`, `description: ...`)
   **And** the CLI outputs confirmation with green status indicators and the installed file paths.

2. **Given** `.agents/skills/repo-to-skill/` already exists,
   **When** the user runs `buddhi skills --repo-to-skill` without `--force`,
   **Then** the CLI prints a warning that the skill already exists and skips modification without error.

3. **Given** `.agents/skills/repo-to-skill/` already exists,
   **When** the user runs `buddhi skills --repo-to-skill --force`,
   **Then** the existing skill files are overwritten with the fresh template and a success message is printed.

4. **Given** an optional target directory path (e.g., `buddhi skills --repo-to-skill --path /custom/dir`),
   **When** the command executes,
   **Then** the skill is installed into `/custom/dir/.agents/skills/repo-to-skill/`.

---

### User Story 3 - Execute Skill Scripts via CLI Runner (Priority: P2)

As an AI agent or developer running `buddhi-cli`,
I want to execute skill helper scripts directly via `buddhi skills run repo-to-skill <target>`
So that repository analysis and skill generation helpers run natively in Python with zero external shell dependencies (`bash`, `sed`, `grep`), guaranteeing 100% cross-platform compatibility across Windows, macOS, and Linux.

**Why this priority**:
Upstream uses a bash script (`analyze_repo.sh`) which fails or requires emulation on Windows. Implementing this logic in Python and exposing it via `buddhi skills run` ensures seamless, deterministic execution for Antigravity agents across all operating systems.

**Independent Test**:
Run `buddhi skills run repo-to-skill <path-or-url> --json` against a test repository or local directory. Verify that it analyzes the project structure, language, entry points, and documentation, returning clean JSON or formatted analysis output.

**Acceptance Scenarios**:

1. **Given** a local repository path or remote GitHub URL,
   **When** the user/agent runs `buddhi skills run repo-to-skill <target>`,
   **Then** the pure Python analyzer runs within the `buddhi-cli` runtime and outputs a structured analysis (project type, entry points, dependencies, CLI/library patterns).

2. **Given** an agent inspecting `.agents/skills/repo-to-skill/scripts/`,
   **When** the agent executes `python .agents/skills/repo-to-skill/scripts/analyze_repo.py <target>`,
   **Then** the script executes with identical logic (dual execution capability).

---

### User Story 4 - Extensible Skills Registry Architecture (Priority: P2)

As a maintainer or contributor to `buddhi-cli`,
I want custom skills and their runnable scripts to be governed by a centralized, modular registry,
So that subsequent skills can be registered with minimal code changes (defining metadata, flag name, bundling the template files, and optional script runner hooks).

**Why this priority**:
Ensures long-term maintainability and prevents ad-hoc, hardcoded flag logic as more agent skills are added in future iterations.

**Independent Test**:
Inspect code and automated unit tests. Verify that the command builds dynamically or cleanly routes via a registry data structure (`SkillRegistryEntry`), decoupling command discovery from individual skill file management.

**Acceptance Scenarios**:

1. **Given** the custom skills registry,
   **When** a new skill definition entry is added to the registry,
   **Then** `buddhi skills` automatically includes it in the listing output, exposes its installation flag, and registers any script execution runner without needing changes to filesystem copying logic.

---

### Edge Cases

- **Missing `.agents` directory**: The CLI automatically creates `.agents/` and `.agents/skills/` if they do not exist in the target project.
- **Permission errors / read-only paths**: Returns a descriptive error message using `BuddhiFsError` and exits with code 1 instead of an unhandled traceback.
- **Multiple skill flags passed simultaneously**: If future flags are combined or passed together, each requested skill is processed sequentially.
- **Offline execution of `buddhi skills run`**: If a local directory path is passed to `buddhi skills run repo-to-skill`, analysis performs 100% offline without network calls.

---

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide a top-level CLI command `buddhi skills`.
- **FR-002**: When invoked with no skill-selection flags, `buddhi skills` MUST render a list/table of all available custom skills, showing their skill ID, CLI flag, and description.
- **FR-003**: System MUST accept the flag `--repo-to-skill` to trigger installation of the `repo-to-skill` agent skill.
- **FR-004**: When `--repo-to-skill` is passed, system MUST install the skill files into `<target_path>/.agents/skills/repo-to-skill/`.
- **FR-005**: System MUST bundle the Antigravity-optimized custom skills in a dedicated template package (e.g., `buddhi.templates.custom_skills`) strictly separate from the default agent harness (`buddhi.templates.agents`). This ensures selective skills are NOT eagerly copied by `buddhi init` and are only provisioned on-demand via `buddhi skills`.
- **FR-006**: The bundled `repo-to-skill` `SKILL.md` MUST comply with Google Antigravity skill conventions (valid YAML frontmatter with `name` and `description`, Antigravity tool workflows, and references).
- **FR-007**: System MUST support a `--force` / `-f` flag to allow overwriting an existing skill directory when re-installing.
- **FR-008**: System MUST support an optional `--path` / `-p` option (defaulting to current working directory `.`) to specify the target project root.
- **FR-009**: System MUST manage custom skills through an extensible registry data structure (`SkillRegistryEntry`) to support seamless future skill additions.
- **FR-010**: System MUST provide a `buddhi skills run <skill-name> [args]` command to execute registered skill scripts directly through the `buddhi-cli` Python runtime.
- **FR-011**: The `repo-to-skill` repository analysis logic MUST be implemented as a pure, cross-platform Python script (`analyze_repo.py`) instead of upstream bash scripts, providing both human-readable and structured `--json` output.

### Key Entities

- **`SkillRegistryEntry`**:
  - `name`: String identifier (e.g. `"repo-to-skill"`)
  - `flag`: CLI flag name (e.g. `"--repo-to-skill"`)
  - `title`: Human-readable display title (e.g. `"Repo to Skill Generator"`)
  - `description`: Detailed summary of the skill's capability
  - `template_resource_pkg`: Dedicated Python package path isolated from base harness (e.g. `"buddhi.templates.custom_skills.repo_to_skill"`)
  - `target_dir_name`: Name of folder inside `.agents/skills/` (`"repo-to-skill"`)
  - `runner_func`: Optional callable routing to `buddhi skills run <skill-name>`

- **`SkillInstallReport`**:
  - `skill_name`: Identifier of the processed skill
  - `target_path`: Destination path
  - `created_files`: List of paths created
  - `skipped`: Boolean indicating if installation was skipped because it already existed

---

## Success Criteria

### Measurable Outcomes

- **SC-001**: `buddhi skills` displays all registered custom skills with exit code 0 in under 500ms.
- **SC-002**: `buddhi skills --repo-to-skill` installs the complete `repo-to-skill` template into `.agents/skills/repo-to-skill/` with zero external network calls.
- **SC-003**: Antigravity agents can immediately discover and parse the installed `repo-to-skill/SKILL.md` per Antigravity custom skill standards.
- **SC-004**: Adding a new skill to `buddhi-cli` in the future requires only registering an entry in the skills registry and placing its template folder in the dedicated custom skills package.
- **SC-005**: Running `buddhi init` does NOT install selective custom skills (e.g., `repo-to-skill`), keeping the initial harness lean until explicitly installed.
- **SC-006**: `buddhi skills run repo-to-skill <target>` executes natively on Windows, macOS, and Linux without bash/sed or external virtual environment dependencies.
- **SC-007**: 100% test coverage on CLI command flags, listing output, installation, overwrite guard, `--force` behavior, and skill script execution.

---

## Assumptions & Packaging Architecture

- **Template Isolation**: Selective custom skills are packaged under `src/buddhi/templates/custom_skills/` rather than `src/buddhi/templates/agents/skills/`. This isolates them from `buddhi init`'s automatic template tree sync (`sync_template_tree`), making them purely opt-in/selective.
- **Python Native Execution**: All skill helper scripts are authored in Python 3.10+ rather than platform-specific shell scripts, enabling dual execution via `buddhi skills run <skill>` and direct `python <script_path>`.
- The target directory is a repository or workspace intended for use with Google Antigravity or Antigravity-compatible harnesses.
- Templates are statically bundled inside `buddhi-cli` distribution wheels so users do not need active internet access or `git` installed to add custom skills.
- The default target directory is the current working directory (`.`).


