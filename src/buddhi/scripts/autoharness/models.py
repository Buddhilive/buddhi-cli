"""Core data models and dataclasses for AutoHarness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

ActionType = Literal["create", "update", "patch", "remove_file", "delete"]
LayerType = Literal["project", "global"]


@dataclass
class SkillIntent:
    action: ActionType
    name: str
    layer: LayerType = "project"
    body: str | None = None
    old_string: str | None = None
    new_string: str | None = None
    files: dict[str, str] = field(default_factory=dict)
    reason: str = ""
    evidence: str = ""
    absorbed_into: str | None = None


@dataclass
class SidecarData:
    created_by: str = "agent"
    use: int = 0
    view: int = 0
    patch: int = 0
    reused_gen: int = 0
    anchor: int = 0
    verification: dict[str, str | int | float | bool] = field(default_factory=dict)


@dataclass
class GateFinding:
    gate: str
    code: str
    message: str
    file_path: str | None = None


@dataclass
class ValidationResult:
    valid: bool
    findings: list[GateFinding] = field(default_factory=list)


@dataclass
class RunAccount:
    run_id: str
    timestamp: str
    landed: list[str] = field(default_factory=list)
    rejected: list[dict[str, str]] = field(default_factory=list)
    spawn_error: str | None = None


@dataclass
class LifecycleDecision:
    keep: list[str] = field(default_factory=list)
    archive: list[str] = field(default_factory=list)

