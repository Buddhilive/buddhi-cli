"""`.buddhi/` filesystem bootstrap: directories, gitignore, and template scaffolding."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

BUDDHI_DIR_NAME = ".buddhi"
GRAPHS_DIR_NAME = "graphs"
DOCS_DIR_NAME = "docs"
GITIGNORE_CONTENT = "graphs/\n"

AGENTS_GITIGNORE_RULES = [
    "memory.local/",
    "agent-memory-local/",
]


class BuddhiFsError(Exception):
    pass


def ensure_buddhi_dirs(root: Path) -> Path:
    """Ensure `.buddhi/` and `.buddhi/graphs/` exist under root; return the graphs dir.

    Never overwrites an existing `.buddhi/.gitignore`.
    """
    buddhi_dir = root / BUDDHI_DIR_NAME
    graphs_dir = buddhi_dir / GRAPHS_DIR_NAME

    try:
        buddhi_dir.mkdir(exist_ok=True)
        gitignore_path = buddhi_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(GITIGNORE_CONTENT, encoding="utf-8")
        graphs_dir.mkdir(exist_ok=True)
    except OSError as exc:
        raise BuddhiFsError(f"could not prepare {buddhi_dir}: {exc}") from exc

    return graphs_dir


def ensure_docs_dir(root: Path) -> Path:
    """Ensure `.buddhi/docs/` exists under root; return it."""
    docs_dir = root / BUDDHI_DIR_NAME / DOCS_DIR_NAME
    try:
        docs_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise BuddhiFsError(f"could not prepare {docs_dir}: {exc}") from exc
    return docs_dir


@dataclass
class TemplateSyncReport:
    created: list[Path] = field(default_factory=list)
    kept_existing: list[Path] = field(default_factory=list)


def sync_template_tree(src_dir: Path, dest_dir: Path) -> TemplateSyncReport:
    """Copy every file under `src_dir` into `dest_dir`, preserving relative paths.

    Never overwrites a file that already exists at the destination — a file
    once written there may have been hand-edited by the user, and buddhi has
    no way to distinguish "untouched since last init" from "customized", so
    the safe default is to leave any existing file alone and only fill in
    what's missing.
    """
    report = TemplateSyncReport()
    if not src_dir.is_dir():
        raise BuddhiFsError(f"template source missing: {src_dir}")

    for src_path in sorted(src_dir.rglob("*")):
        if src_path.is_dir():
            continue
        if "__pycache__" in src_path.parts:
            continue
        if src_path.suffix in (".pyc", ".pyo"):
            continue
        if src_path.name == "__init__.py":
            # The template tree is itself a Python package (so it can be
            # packaged/imported), but __init__.py exists only for that
            # purpose — it is not harness content and must never be
            # scaffolded into a target project's `.agents/`.
            continue
        rel = src_path.relative_to(src_dir)
        dest_path = dest_dir / rel
        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            if dest_path.exists():
                report.kept_existing.append(dest_path)
                continue
            shutil.copyfile(src_path, dest_path)
            report.created.append(dest_path)
        except OSError as exc:
            raise BuddhiFsError(f"could not write {dest_path}: {exc}") from exc

    return report


@dataclass
class WorkflowMigrationReport:
    migrated: list[Path] = field(default_factory=list)
    skipped_existing: list[Path] = field(default_factory=list)
    removed: list[Path] = field(default_factory=list)


def _ensure_skill_frontmatter(content: str, default_name: str) -> str:
    """Ensure content has valid YAML frontmatter containing 'name' and 'description'."""
    match = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n(.*)$", content, flags=re.DOTALL)
    if not match:
        desc = f"Custom skill migrated from {default_name}."
        lines = content.strip().splitlines()
        for line in lines:
            if line.startswith("# "):
                title = line.lstrip("# ").strip()
                desc = f"Skill for {title}. Migrated from {default_name}."
                break
        return f"---\nname: {default_name}\ndescription: {desc}\n---\n\n{content}"

    fm_raw = match.group(1)
    body = match.group(2)

    has_name = re.search(r"^name:\s*", fm_raw, flags=re.MULTILINE)
    has_desc = re.search(r"^description:\s*", fm_raw, flags=re.MULTILINE)

    fm_lines = [line for line in fm_raw.splitlines() if line.strip()]
    if not has_name:
        fm_lines.insert(0, f"name: {default_name}")
    if not has_desc:
        fm_lines.append(f"description: Custom skill migrated from {default_name}.")

    new_fm = "\n".join(fm_lines)
    return f"---\n{new_fm}\n---\n{body}"


def migrate_legacy_workflows(agents_dir: Path) -> WorkflowMigrationReport:
    """Migrate legacy Antigravity workflows (.agents/workflows/*.md) to skills (.agents/skills/<name>/SKILL.md)
    and remove legacy workflow files and directory to prevent conflicts.

    Follows the Antigravity migration standard:
    1. For each .agents/workflows/<name>.md:
       - If .agents/skills/<name>/SKILL.md exists, preserve existing without overwrite.
       - If .agents/skills/<name>/SKILL.md does not exist, convert workflow to SKILL.md
         ensuring valid YAML frontmatter (name and description).
       - Delete the legacy workflow file.
    2. Clean up or remove .agents/workflows.json manifest if present.
    3. Remove the .agents/workflows directory once all workflows are cleaned up.
    """
    report = WorkflowMigrationReport()
    workflows_dir = agents_dir / "workflows"
    if not workflows_dir.is_dir():
        return report

    # 1. Convert active workflow files (.md)
    for wf_file in sorted(workflows_dir.glob("*.md")):
        if wf_file.name.endswith(".bak"):
            continue
        skill_name = "spec-plan" if wf_file.stem == "plan" else wf_file.stem
        target_skill_dir = agents_dir / "skills" / skill_name
        target_skill_file = target_skill_dir / "SKILL.md"

        if target_skill_file.exists():
            report.skipped_existing.append(target_skill_file)
        else:
            try:
                target_skill_dir.mkdir(parents=True, exist_ok=True)
                raw_content = wf_file.read_text(encoding="utf-8")
                converted_content = _ensure_skill_frontmatter(
                    raw_content, default_name=skill_name
                )
                target_skill_file.write_text(converted_content, encoding="utf-8")
                report.migrated.append(target_skill_file)
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not convert workflow to skill {target_skill_file}: {exc}"
                ) from exc

    # 2. Remove all legacy workflow files (.md and .md.bak)
    removed_names: set[str] = set()
    for wf_file in sorted(workflows_dir.iterdir()):
        if wf_file.is_file():
            name = wf_file.name
            if name.endswith(".md.bak"):
                removed_names.add(name[:-7])
            elif name.endswith(".md"):
                removed_names.add(wf_file.stem)
            try:
                wf_file.unlink()
                report.removed.append(wf_file)
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not remove legacy workflow file {wf_file}: {exc}"
                ) from exc

    # 3. Clean up or remove workflows.json manifest if present
    manifest_path = agents_dir / "workflows.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                new_data = [
                    item
                    for item in data
                    if not (
                        isinstance(item, dict) and item.get("name") in removed_names
                    )
                ]
                if new_data:
                    manifest_path.write_text(
                        json.dumps(new_data, indent=2) + "\n", encoding="utf-8"
                    )
                else:
                    manifest_path.unlink()
            elif isinstance(data, dict):
                has_remaining = False
                for key in ("workflows", "entries"):
                    if key in data and isinstance(data[key], list):
                        data[key] = [
                            item
                            for item in data[key]
                            if not (
                                isinstance(item, dict)
                                and item.get("name") in removed_names
                            )
                        ]
                        if data[key]:
                            has_remaining = True
                if has_remaining:
                    manifest_path.write_text(
                        json.dumps(data, indent=2) + "\n", encoding="utf-8"
                    )
                else:
                    manifest_path.unlink()
            else:
                manifest_path.unlink()
        except (json.JSONDecodeError, OSError):
            pass

    # 4. Remove workflows_dir if empty
    try:
        if workflows_dir.exists():
            shutil.rmtree(workflows_dir)
    except OSError as exc:
        raise BuddhiFsError(
            f"could not remove legacy workflows directory {workflows_dir}: {exc}"
        ) from exc

    return report


@dataclass
class PlanMigrationReport:
    migrated_skill: bool = False
    removed_legacy_skill: bool = False
    updated_files: list[Path] = field(default_factory=list)


def migrate_legacy_plan_skill(
    agents_dir: Path, project_root: Path | None = None
) -> PlanMigrationReport:
    """Migrate legacy .agents/skills/plan to .agents/skills/spec-plan and update references.

    1. Directory Migration:
       - If .agents/skills/plan exists and .agents/skills/spec-plan does not exist:
         Moves .agents/skills/plan to .agents/skills/spec-plan, updating its frontmatter
         ('name: plan' -> 'name: spec-plan', '# /plan' -> '# /spec-plan').
       - If .agents/skills/plan exists and .agents/skills/spec-plan already exists:
         Removes .agents/skills/plan to prevent collision with Antigravity's built-in /plan.

    2. Reference Updates:
       - Safely updates '/plan' references to '/spec-plan' across:
         * project_root / 'AGENTS.md' (if present)
         * agents_dir / 'rules' / 'harness-core.md'
         * agents_dir / 'skills' / 'specify' / 'SKILL.md'
         * agents_dir / 'skills' / 'implement' / 'SKILL.md'
         * agents_dir / 'skills' / 'README.md'
       - Uses regex boundary matching (?<![a-zA-Z0-9_/-])/plan(?![a-zA-Z0-9_/-])
         ensuring commands like /quick-plan, plan.md, or buddhi docs plan are never touched.
    """
    report = PlanMigrationReport()
    plan_dir = agents_dir / "skills" / "plan"
    spec_plan_dir = agents_dir / "skills" / "spec-plan"

    if plan_dir.is_dir():
        if not spec_plan_dir.exists():
            try:
                shutil.move(str(plan_dir), str(spec_plan_dir))
                report.migrated_skill = True
                spec_plan_file = spec_plan_dir / "SKILL.md"
                if spec_plan_file.is_file():
                    content = spec_plan_file.read_text(encoding="utf-8")
                    content = re.sub(
                        r"^name:\s*plan\s*$",
                        "name: spec-plan",
                        content,
                        flags=re.MULTILINE,
                    )
                    content = re.sub(
                        r"^#\s*/plan\b", "# /spec-plan", content, flags=re.MULTILINE
                    )
                    content = re.sub(
                        r"(?<![a-zA-Z0-9_/-])/plan(?![a-zA-Z0-9_/-])",
                        "/spec-plan",
                        content,
                    )
                    spec_plan_file.write_text(content, encoding="utf-8")
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not migrate legacy plan skill: {exc}"
                ) from exc
        else:
            try:
                shutil.rmtree(plan_dir)
                report.removed_legacy_skill = True
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not remove legacy plan skill directory {plan_dir}: {exc}"
                ) from exc

    candidates: list[Path] = []
    if project_root is not None:
        candidates.append(project_root / "AGENTS.md")
    candidates.extend(
        [
            agents_dir / "rules" / "harness-core.md",
            agents_dir / "skills" / "specify" / "SKILL.md",
            agents_dir / "skills" / "implement" / "SKILL.md",
            agents_dir / "skills" / "README.md",
        ]
    )

    pattern = re.compile(r"(?<![a-zA-Z0-9_/-])/plan(?![a-zA-Z0-9_/-])")

    for file_path in candidates:
        if file_path.is_file():
            try:
                original = file_path.read_text(encoding="utf-8")
                updated = pattern.sub("/spec-plan", original)
                if updated != original:
                    file_path.write_text(updated, encoding="utf-8")
                    report.updated_files.append(file_path)
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not update references in {file_path}: {exc}"
                ) from exc

    return report


@dataclass
class TasksMigrationReport:
    migrated_skill: bool = False
    removed_legacy_skill: bool = False
    updated_files: list[Path] = field(default_factory=list)


def migrate_legacy_tasks_skill(
    agents_dir: Path, project_root: Path | None = None
) -> TasksMigrationReport:
    """Migrate legacy .agents/skills/tasks to .agents/skills/spec-tasks and update references.

    1. Directory Migration:
       - If .agents/skills/tasks exists and .agents/skills/spec-tasks does not exist:
         Moves .agents/skills/tasks to .agents/skills/spec-tasks, updating its frontmatter
         ('name: tasks' -> 'name: spec-tasks', '# /tasks' -> '# /spec-tasks').
       - If .agents/skills/tasks exists and .agents/skills/spec-tasks already exists:
         Removes .agents/skills/tasks to prevent collision with Antigravity's built-in /tasks.

    2. Reference Updates:
       - Safely updates '/tasks' references to '/spec-tasks' across:
         * project_root / 'AGENTS.md' (if present)
         * agents_dir / 'rules' / 'harness-core.md'
         * agents_dir / 'skills' / 'spec-plan' / 'SKILL.md'
         * agents_dir / 'skills' / 'implement' / 'SKILL.md'
         * agents_dir / 'skills' / 'README.md'
         * agents_dir / 'templates' / 'agents-template.md'
         * agents_dir / 'templates' / 'plan-template.md'
         * agents_dir / 'templates' / 'tasks-template.md'
       - Uses regex boundary matching (?<![a-zA-Z0-9_/-])/tasks(?![a-zA-Z0-9_/-])
         ensuring commands or filenames like tasks.md or --require-tasks are never touched.
    """
    report = TasksMigrationReport()
    tasks_dir = agents_dir / "skills" / "tasks"
    spec_tasks_dir = agents_dir / "skills" / "spec-tasks"

    if tasks_dir.is_dir():
        if not spec_tasks_dir.exists():
            try:
                shutil.move(str(tasks_dir), str(spec_tasks_dir))
                report.migrated_skill = True
                spec_tasks_file = spec_tasks_dir / "SKILL.md"
                if spec_tasks_file.is_file():
                    content = spec_tasks_file.read_text(encoding="utf-8")
                    content = re.sub(
                        r"^name:\s*tasks\s*$",
                        "name: spec-tasks",
                        content,
                        flags=re.MULTILINE,
                    )
                    content = re.sub(
                        r"^#\s*/tasks\b", "# /spec-tasks", content, flags=re.MULTILINE
                    )
                    content = re.sub(
                        r"(?<![a-zA-Z0-9_/-])/tasks(?![a-zA-Z0-9_/-])",
                        "/spec-tasks",
                        content,
                    )
                    content = content.replace(
                        "`tasks`: Actionable", "`spec-tasks`: Actionable"
                    )
                    spec_tasks_file.write_text(content, encoding="utf-8")
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not migrate legacy tasks skill: {exc}"
                ) from exc
        else:
            try:
                shutil.rmtree(tasks_dir)
                report.removed_legacy_skill = True
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not remove legacy tasks skill directory {tasks_dir}: {exc}"
                ) from exc

    candidates: list[Path] = []
    if project_root is not None:
        candidates.append(project_root / "AGENTS.md")
    candidates.extend(
        [
            agents_dir / "rules" / "harness-core.md",
            agents_dir / "skills" / "spec-plan" / "SKILL.md",
            agents_dir / "skills" / "implement" / "SKILL.md",
            agents_dir / "skills" / "README.md",
            agents_dir / "templates" / "agents-template.md",
            agents_dir / "templates" / "plan-template.md",
            agents_dir / "templates" / "tasks-template.md",
        ]
    )

    pattern = re.compile(r"(?<![a-zA-Z0-9_/-])/tasks(?![a-zA-Z0-9_/-])")

    for file_path in candidates:
        if file_path.is_file():
            try:
                original = file_path.read_text(encoding="utf-8")
                updated = pattern.sub("/spec-tasks", original)
                updated = updated.replace(
                    "`tasks`: Actionable", "`spec-tasks`: Actionable"
                )
                if updated != original:
                    file_path.write_text(updated, encoding="utf-8")
                    report.updated_files.append(file_path)
            except OSError as exc:
                raise BuddhiFsError(
                    f"could not update references in {file_path}: {exc}"
                ) from exc

    return report


def ensure_agents_gitignore(agents_dir: Path) -> Path:
    """Ensure .agents/.gitignore exists and ignores local memory dirs."""
    agents_dir.mkdir(parents=True, exist_ok=True)
    gitignore_path = agents_dir / ".gitignore"
    try:
        existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""
        lines = [line.strip() for line in existing.splitlines()]
        added = []
        for rule in AGENTS_GITIGNORE_RULES:
            if rule not in lines:
                added.append(rule)
        if added:
            content = (existing.rstrip() + "\n" + "\n".join(added) + "\n").lstrip()
            gitignore_path.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise BuddhiFsError(f"could not prepare {gitignore_path}: {exc}") from exc
    return gitignore_path
