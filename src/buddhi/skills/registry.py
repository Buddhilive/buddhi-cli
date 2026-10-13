"""Custom Skills Registry for buddhi-cli.

## Adding Future Custom Skills

To introduce a new selective custom skill:
1. Create a template package under `src/buddhi/templates/custom_skills/<skill_name>/`
   containing:
   - `SKILL.md` (with Antigravity YAML frontmatter: `name`, `description`)
   - `references/` (optional on-demand reference markdown docs)
   - `scripts/` (optional cross-platform Python scripts)
   - `__init__.py` (so the template directory is an importable Python resource)

2. Register the skill in `_SKILL_REGISTRY` below by defining a `SkillRegistryEntry`:
   ```python
   "my-skill": SkillRegistryEntry(
       name="my-skill",
       flag="--my-skill",
       title="My New Agent Skill",
       description="Detailed description of what this skill enables.",
       template_pkg="buddhi.templates.custom_skills.my_skill",
       target_dir_name="my-skill",
       runner=_my_skill_runner_callable,  # Optional callable for `buddhi skills run my-skill`
   )
   ```

3. Expose the CLI flag in `src/buddhi/commands/skills.py` (e.g. `my_skill: bool = typer.Option(...)`).
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SkillRegistryEntry:
    """Metadata describing a registered custom agent skill."""

    name: str
    flag: str
    title: str
    description: str
    template_pkg: str
    target_dir_name: str
    runner: Callable[..., Any] | None = None

    def execute_runner(self, *args: Any, **kwargs: Any) -> Any:
        """Invoke runner callable if registered."""
        if self.runner is None:
            raise NotImplementedError(
                f"No execution runner configured for skill '{self.name}'."
            )
        return self.runner(*args, **kwargs)


def _run_repo_to_skill_wrapper(*args: Any, **kwargs: Any) -> Any:
    from buddhi.skills.repo_to_skill import run_repo_to_skill

    return run_repo_to_skill(*args, **kwargs)


_SKILL_REGISTRY: dict[str, SkillRegistryEntry] = {
    "repo-to-skill": SkillRegistryEntry(
        name="repo-to-skill",
        flag="--repo-to-skill",
        title="Repo to Skill Generator",
        description=(
            "Turn any GitHub repository or local directory into a tested, "
            "ready-to-use Google Antigravity agent skill."
        ),
        template_pkg="buddhi.templates.custom_skills.repo_to_skill",
        target_dir_name="repo-to-skill",
        runner=_run_repo_to_skill_wrapper,
    ),
    "renderer": SkillRegistryEntry(
        name="renderer",
        flag="--renderer",
        title="TypeGPU / WebGPU Renderer Architecture",
        description=(
            "Architecture rules for GPU rendering with TypeGPU/WebGPU: "
            "fixed-view cost, single contract owners, and pixel-level A/B verification."
        ),
        template_pkg="buddhi.templates.custom_skills.renderer",
        target_dir_name="renderer",
    ),
    "launch-video": SkillRegistryEntry(
        name="launch-video",
        flag="--launch-video",
        title="Launch Video Direction & Motion Graphics",
        description=(
            "Produce showreel-grade launch videos with beat-synced visuals and synthesized audio."
        ),
        template_pkg="buddhi.templates.custom_skills.launch_video",
        target_dir_name="launch-video",
    ),
    "cinematic-shot": SkillRegistryEntry(
        name="cinematic-shot",
        flag="--cinematic-shot",
        title="Cinematic Software UI Filming",
        description=(
            "Direct steep, oblique, shallow-DOF macro hero shots of software UI floating in black."
        ),
        template_pkg="buddhi.templates.custom_skills.cinematic_shot",
        target_dir_name="cinematic-shot",
    ),
    "isometric-motion": SkillRegistryEntry(
        name="isometric-motion",
        flag="--isometric-motion",
        title="Isometric Motion & Interactive Anatomy Visuals",
        description=(
            "Build animations and interactive elements in crafted isometric Anatomy style "
            "with live state readout and WebGL/SVG shaders."
        ),
        template_pkg="buddhi.templates.custom_skills.isometric_motion",
        target_dir_name="isometric-motion",
    ),
    "xiaohei-illustrations": SkillRegistryEntry(
        name="xiaohei-illustrations",
        flag="--xiaohei-illustrations",
        title="Xiaohei Conceptual Illustrations",
        description=(
            "Generate Ian-style monochrome conceptual illustrations starring Xiaohei "
            "for articles, docs, and processes."
        ),
        template_pkg="buddhi.templates.custom_skills.xiaohei_illustrations",
        target_dir_name="xiaohei-illustrations",
    ),
}

GRAPHICS_SKILLS: list[str] = [
    "renderer",
    "launch-video",
    "cinematic-shot",
    "isometric-motion",
    "xiaohei-illustrations",
]


def get_skill(name: str) -> SkillRegistryEntry | None:
    """Retrieve a skill entry by name or flag (e.g. 'repo-to-skill' or '--repo-to-skill')."""
    if name in _SKILL_REGISTRY:
        return _SKILL_REGISTRY[name]
    for entry in _SKILL_REGISTRY.values():
        if entry.flag == name or entry.flag.lstrip("-") == name.lstrip("-"):
            return entry
    return None


def list_skills() -> list[SkillRegistryEntry]:
    """List all registered custom skills."""
    return list(_SKILL_REGISTRY.values())


def register_skill(entry: SkillRegistryEntry) -> None:
    """Register a custom skill entry (used for testing and runtime extensions)."""
    _SKILL_REGISTRY[entry.name] = entry
