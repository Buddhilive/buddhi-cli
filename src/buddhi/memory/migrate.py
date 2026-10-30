"""Legacy flat-file memory migration into OKF v0.2 concept bundles."""

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
    MemoryStatus,
)
from buddhi.memory.security import sanitize_slug
from buddhi.memory.store import MemoryStore

LEGACY_FILES_MAP: dict[str, MemoryKind] = {
    "user-preferences.md": MemoryKind.PREFERENCE,
    "project-conventions.md": MemoryKind.CONVENTION,
    "tech-decisions.md": MemoryKind.DECISION,
    "feedback-history.md": MemoryKind.FEEDBACK,
}

BOILERPLATE_SUBSTRINGS = [
    "no entries yet",
    "durable user preferences about how to work",
    "durable project conventions discovered",
    "architecture and technology decisions",
    "corrections and confirmations about how to approach work",
]


@dataclass
class MigrationResult:
    migrated_count: int = 0
    created_nodes: list[Path] = field(default_factory=list)
    backed_up_files: list[Path] = field(default_factory=list)


def is_boilerplate(line: str) -> bool:
    """Check if line is template boilerplate rather than user entry."""
    cleaned = line.lower().strip()
    return any(bp in cleaned for bp in BOILERPLATE_SUBSTRINGS)


def parse_legacy_entries(text: str) -> list[str]:
    """Parse distinct bullet points, numbered items, or paragraph entries."""
    lines = text.splitlines()
    entries: list[str] = []
    current_entry: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if is_boilerplate(stripped):
            continue

        if stripped.startswith(("- ", "* ", "+ ")) or re.match(r"^\d+\.\s+", stripped):
            if current_entry:
                entries.append(" ".join(current_entry))
                current_entry = []
            clean_item = re.sub(r"^[-*+\d.]+\s*", "", stripped)
            current_entry.append(clean_item)
        else:
            current_entry.append(stripped)

    if current_entry:
        entries.append(" ".join(current_entry))

    return [e.strip() for e in entries if e.strip()]


def migrate_legacy_memory(workspace_root: Path) -> MigrationResult:
    """Migrates legacy flat topic files in .agents/memory/ to OKF concept nodes."""
    memory_dir = workspace_root / ".agents" / "memory"
    if not memory_dir.is_dir():
        return MigrationResult()

    store = MemoryStore(workspace_root)
    store.init_bundle("project")

    result = MigrationResult()

    for legacy_name, kind in LEGACY_FILES_MAP.items():
        legacy_path = memory_dir / legacy_name
        if not legacy_path.is_file():
            continue

        text = legacy_path.read_text(encoding="utf-8")
        entries = parse_legacy_entries(text)

        for idx, entry in enumerate(entries, 1):
            # Extract first sentence or up to 50 chars as title
            title_match = re.split(r"[.!?]\s+", entry, maxsplit=1)
            title = title_match[0].strip() if title_match else entry[:50]
            if len(title) > 60:
                title = title[:57] + "..."

            slug = sanitize_slug(title)
            node_id = f"mem-{kind.value}-{slug}"

            node = MemoryNode(
                frontmatter=MemoryFrontmatter(
                    id=node_id,
                    kind=kind,
                    title=title,
                    summary=entry[:140],
                    status=MemoryStatus.STABLE,
                    confidence=MemoryConfidence.VERIFIED,
                    scope="project",
                    tags=["migrated-legacy"],
                    generated=MemoryGenerated(by="buddhi-cli/migrate"),
                ),
                body=f"# Context & Rationale\n\n{entry}\n",
            )
            saved_path = store.save_node(node, "project")
            result.created_nodes.append(saved_path)
            result.migrated_count += 1

        # Backup legacy file as .md.bak
        backup_path = memory_dir / f"{legacy_name}.bak"
        legacy_path.rename(backup_path)
        result.backed_up_files.append(backup_path)

    if result.migrated_count > 0:
        store.log_mutation(
            scope="project",
            action="migrated",
            node_id="legacy-bundle",
            title=f"Migrated {result.migrated_count} legacy memory entries to OKF concepts",
        )
        store.sync_indexes("project")

    return result
