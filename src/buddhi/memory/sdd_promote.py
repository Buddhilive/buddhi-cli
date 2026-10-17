"""Extraction of durable architectural decisions and verified choices from SDD into OKF memory nodes."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from buddhi.memory.models import (
    MemoryConfidence,
    MemoryFrontmatter,
    MemoryGenerated,
    MemoryKind,
    MemoryNode,
    MemoryRelation,
    MemoryStatus,
    RelationKind,
)
from buddhi.memory.security import sanitize_slug
from buddhi.memory.store import MemoryStore


@dataclass
class PromotionResult:
    promoted_nodes: list[MemoryNode] = field(default_factory=list)
    spec_branch: str = ""


def _find_spec_dir(workspace_root: Path, branch: str | None = None) -> Path | None:
    specs_root = workspace_root / ".buddhi" / "specs"
    if not specs_root.is_dir():
        return None

    if branch:
        target = specs_root / branch
        if target.is_dir():
            return target
        done_target = specs_root / "done" / branch
        if done_target.is_dir():
            return done_target
        return None

    # Search for any active spec directory with spec.md
    candidates = [
        d
        for d in specs_root.iterdir()
        if d.is_dir() and d.name != "done" and (d / "spec.md").is_file()
    ]
    if candidates:
        return candidates[0]

    return None


def extract_choices(choices_path: Path) -> list[tuple[str, str, str]]:
    """Extracts (choice_type, title, description) from choices.md (sound, unsound, needs-user)."""
    if not choices_path.is_file():
        return []

    text = choices_path.read_text(encoding="utf-8")
    entries: list[tuple[str, str, str]] = []

    pattern = re.compile(
        r"###\s*\[?(SOUND|UNSOUND|NEEDS-USER)\]?:?\s*(.+?)\n+(.+?)(?=\n###|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    for m in pattern.finditer(text):
        ctype = m.group(1).upper()
        title = m.group(2).strip()
        body = m.group(3).strip()
        entries.append((ctype, title, body))

    return entries


def promote_sdd_artifacts(
    workspace_root: Path, branch: str | None = None
) -> PromotionResult:
    """Promotes durable decisions from spec.md, plan.md, and sound choices from choices.md."""
    spec_dir = _find_spec_dir(workspace_root, branch)
    if not spec_dir:
        return PromotionResult()

    branch_name = spec_dir.name
    store = MemoryStore(workspace_root)
    store.init_bundle("project")

    promoted: list[MemoryNode] = []

    # 1. Promote sound choices from choices.md
    choices_path = spec_dir / "choices.md"
    for ctype, title, body in extract_choices(choices_path):
        if ctype != "SOUND":
            continue

        slug = sanitize_slug(title)
        node_id = f"mem-decision-{slug}"
        node = MemoryNode(
            frontmatter=MemoryFrontmatter(
                id=node_id,
                kind=MemoryKind.DECISION,
                title=title,
                summary=body.splitlines()[0][:140] if body else title,
                status=MemoryStatus.STABLE,
                confidence=MemoryConfidence.VERIFIED,
                scope="project",
                tags=["sdd-choice", branch_name],
                generated=MemoryGenerated(by=f"buddhi-sdd/{branch_name}"),
                relations=[
                    MemoryRelation(
                        kind=RelationKind.DERIVED_FROM_SPEC,
                        target=f".buddhi/specs/{branch_name}/spec.md",
                    )
                ],
            ),
            body=f"# Summary\n\n{title}\n\n# Context & Rationale\n\n{body}\n",
        )
        store.save_node(node, "project")
        promoted.append(node)

    # 2. Promote spec rationale as sdd-rationale
    spec_file = spec_dir / "spec.md"
    if spec_file.is_file():
        spec_text = spec_file.read_text(encoding="utf-8")
        title_match = re.search(
            r"^#\s*Feature Specification:\s*(.+)$", spec_text, re.MULTILINE
        )
        spec_title = title_match.group(1).strip() if title_match else branch_name
        slug = sanitize_slug(spec_title)
        node_id = f"mem-sdd-{slug}"

        node = MemoryNode(
            frontmatter=MemoryFrontmatter(
                id=node_id,
                kind=MemoryKind.SDD_RATIONALE,
                title=f"SDD: {spec_title}",
                summary=f"Durable rationale for feature {branch_name}",
                status=MemoryStatus.STABLE,
                confidence=MemoryConfidence.VERIFIED,
                scope="project",
                tags=["sdd-spec", branch_name],
                generated=MemoryGenerated(by=f"buddhi-sdd/{branch_name}"),
                relations=[
                    MemoryRelation(
                        kind=RelationKind.DERIVED_FROM_SPEC,
                        target=f".buddhi/specs/{branch_name}/spec.md",
                    )
                ],
            ),
            body=f"# Summary\n\nDurable architectural rationale and invariants for feature `{branch_name}`.\n\n@.buddhi/specs/{branch_name}/spec.md\n",
        )
        store.save_node(node, "project")
        promoted.append(node)

    if promoted:
        store.log_mutation(
            scope="project",
            action="sdd-promote",
            node_id=f"sdd-{branch_name}",
            title=f"Promoted {len(promoted)} SDD concept(s) from branch {branch_name}",
        )
        store.sync_indexes("project")

    return PromotionResult(promoted_nodes=promoted, spec_branch=branch_name)
