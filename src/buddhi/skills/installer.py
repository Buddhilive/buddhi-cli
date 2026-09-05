from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from buddhi.skills.registry import SkillRegistryEntry
from buddhi.util.fsutil import BuddhiFsError


@dataclass
class SkillInstallReport:
    skill_name: str
    target_dir: Path
    created: list[Path] = field(default_factory=list)
    skipped: bool = False
    overwritten: bool = False


def install_skill(
    entry: SkillRegistryEntry,
    project_root: Path,
    force: bool = False,
) -> SkillInstallReport:
    """Install a custom skill template into `<project_root>/.agents/skills/<target_dir_name>`.

    If the destination directory already exists and `force` is False, the installation
    is skipped with a warning report. If `force` is True, existing files are overwritten.
    """
    root = project_root.resolve()
    target_skill_dir = root / ".agents" / "skills" / entry.target_dir_name

    report = SkillInstallReport(
        skill_name=entry.name,
        target_dir=target_skill_dir,
    )

    if target_skill_dir.exists():
        if not force:
            report.skipped = True
            return report
        report.overwritten = True

    try:
        template_root = resources.files(entry.template_pkg)
        with resources.as_file(template_root) as src_dir:
            if not src_dir.is_dir():
                raise BuddhiFsError(f"Template directory missing for skill '{entry.name}': {src_dir}")

            target_skill_dir.mkdir(parents=True, exist_ok=True)

            for src_path in sorted(src_dir.rglob("*")):
                if src_path.is_dir():
                    continue
                if "__pycache__" in src_path.parts:
                    continue
                if src_path.suffix in (".pyc", ".pyo"):
                    continue
                if src_path.name == "__init__.py":
                    # __init__.py exists only for packaging purposes; do not scaffold into skill
                    continue

                rel = src_path.relative_to(src_dir)
                dest_path = target_skill_dir / rel
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src_path, dest_path)
                report.created.append(dest_path)

    except (OSError, ModuleNotFoundError, FileNotFoundError) as exc:
        raise BuddhiFsError(f"Failed installing skill '{entry.name}' to {target_skill_dir}: {exc}") from exc

    return report
