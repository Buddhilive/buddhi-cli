"""Multi-scope bundle store, MEMORY.md 200-line/25KB cap, compaction, and log.md."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from buddhi.memory.hash import verify_source_staleness
from buddhi.memory.models import (
    MemoryConfidence,
    MemoryKind,
    MemoryNode,
    MemoryStatus,
)
from buddhi.memory.security import (
    TOPIC_DIRS,
    assert_no_secrets_in_tracked_memory,
    build_memory_file_path,
)

MAX_MEMORY_LINES = 200
MAX_MEMORY_BYTES = 25600
MAX_LINE_CHARS = 150
WARNING_LINE_THRESHOLD = 180


@dataclass
class BudgetStatus:
    total_lines: int
    total_bytes: int
    max_line_length: int
    is_valid: bool
    violations: list[str] = field(default_factory=list)


class MemoryStore:
    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root.resolve()
        self.user_memory_root = Path("~/.buddhi/memory").expanduser().resolve()

    def get_scope_dir(self, scope: str = "project") -> Path:
        """Resolve base directory for a given scope."""
        if scope == "project":
            return self.workspace_root / ".agents" / "memory"
        elif scope == "local":
            return self.workspace_root / ".agents" / "memory.local"
        elif scope == "user":
            return self.user_memory_root
        elif scope.startswith("agent:"):
            agent_name = scope.split(":", 1)[1].strip()
            return self.workspace_root / ".agents" / "agent-memory" / agent_name
        elif scope.startswith("agent-local:"):
            agent_name = scope.split(":", 1)[1].strip()
            return self.workspace_root / ".agents" / "agent-memory-local" / agent_name
        raise ValueError(f"Unknown scope: {scope}")

    def init_bundle(self, scope: str = "project") -> Path:
        """Initialize directory layout, MEMORY.md, and log.md for scope."""
        base_dir = self.get_scope_dir(scope)
        base_dir.mkdir(parents=True, exist_ok=True)

        for topic in set(TOPIC_DIRS.values()):
            topic_dir = base_dir / topic
            topic_dir.mkdir(parents=True, exist_ok=True)
            topic_index = topic_dir / "index.md"
            if not topic_index.exists():
                topic_index.write_text(
                    f"# {topic.capitalize()} Index\n\n", encoding="utf-8"
                )

        memory_md = base_dir / "MEMORY.md"
        if not memory_md.exists():
            memory_md.write_text(
                '---\nokf_version: "0.2"\n---\n\n# Memory Index\n\n',
                encoding="utf-8",
            )

        log_md = base_dir / "log.md"
        if not log_md.exists():
            log_md.write_text("# Memory Mutation Log\n\n", encoding="utf-8")

        return base_dir

    def log_mutation(
        self,
        scope: str,
        action: str,
        node_id: str,
        title: str,
        details: str = "",
    ) -> None:
        """Prepend a mutation entry to log.md newest-first."""
        base_dir = self.get_scope_dir(scope)
        log_path = base_dir / "log.md"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

        new_entry = f"## {now_iso} - [{action.upper()}] `{node_id}`: {title}\n"
        if details:
            new_entry += f"{details.strip()}\n"
        new_entry += "\n"

        existing = (
            log_path.read_text(encoding="utf-8")
            if log_path.exists()
            else "# Memory Mutation Log\n\n"
        )
        if existing.startswith("# Memory Mutation Log\n\n"):
            header = "# Memory Mutation Log\n\n"
            rest = existing[len(header) :]
            updated = header + new_entry + rest
        else:
            updated = new_entry + existing

        log_path.write_text(updated, encoding="utf-8")

    def load_node(self, path: Path) -> MemoryNode:
        """Load an OKF memory concept file."""
        text = path.read_text(encoding="utf-8")
        return MemoryNode.from_markdown(text, file_path=path)

    def save_node(self, node: MemoryNode, scope: str = "project") -> Path:
        """Save an OKF memory concept file, enforcing security invariants and index sync."""
        assert_no_secrets_in_tracked_memory(
            node.body + " " + node.frontmatter.summary, scope
        )

        base_dir = self.init_bundle(scope)
        target_path = build_memory_file_path(base_dir, node.kind.value, node.id)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        content = node.to_markdown()
        target_path.write_text(content, encoding="utf-8")

        self.log_mutation(
            scope=scope,
            action="saved",
            node_id=node.id,
            title=node.title,
            details=f"Kind: {node.kind.value}, Summary: {node.summary}",
        )
        self.sync_indexes(scope)
        return target_path

    def list_nodes(
        self,
        scopes: list[str] | None = None,
        kind: MemoryKind | None = None,
    ) -> list[MemoryNode]:
        """List all memory nodes across given scopes."""
        target_scopes = scopes or ["project", "local"]
        nodes: list[MemoryNode] = []

        for scope in target_scopes:
            try:
                base_dir = self.get_scope_dir(scope)
            except ValueError:
                continue

            if not base_dir.is_dir():
                continue

            for md_file in sorted(base_dir.rglob("*.md")):
                if md_file.name in ("MEMORY.md", "log.md", "index.md"):
                    continue
                try:
                    node = self.load_node(md_file)
                    if kind is None or node.kind == kind:
                        nodes.append(node)
                except (OSError, ValueError):
                    continue

        return nodes

    def check_budget(self, scope: str = "project") -> BudgetStatus:
        """Check MEMORY.md entrypoint line and byte caps."""
        base_dir = self.get_scope_dir(scope)
        memory_md = base_dir / "MEMORY.md"
        if not memory_md.is_file():
            return BudgetStatus(0, 0, 0, True, [])

        text = memory_md.read_text(encoding="utf-8")
        lines = text.splitlines()
        total_lines = len(lines)
        total_bytes = len(text.encode("utf-8"))
        max_line_len = max((len(line) for line in lines), default=0)

        violations: list[str] = []
        if total_lines > MAX_MEMORY_LINES:
            violations.append(
                f"Lines {total_lines} exceeds hard cap of {MAX_MEMORY_LINES}"
            )
        if total_bytes > MAX_MEMORY_BYTES:
            violations.append(
                f"Size {total_bytes} bytes exceeds hard cap of {MAX_MEMORY_BYTES} bytes"
            )
        for idx, line in enumerate(lines, 1):
            if line.startswith("* [") and len(line) > MAX_LINE_CHARS:
                violations.append(
                    f"Line {idx} exceeds {MAX_LINE_CHARS} chars: ({len(line)} chars)"
                )

        is_valid = len(violations) == 0
        return BudgetStatus(
            total_lines, total_bytes, max_line_len, is_valid, violations
        )

    def sync_indexes(self, scope: str = "project") -> None:
        """Regenerate topic index.md files and root MEMORY.md."""
        base_dir = self.get_scope_dir(scope)
        nodes = self.list_nodes(scopes=[scope])

        # 1. Update topic index.md files
        topic_nodes: dict[str, list[MemoryNode]] = {t: [] for t in TOPIC_DIRS.values()}
        for node in nodes:
            topic_sub = TOPIC_DIRS.get(node.kind.value, "misc")
            topic_nodes.setdefault(topic_sub, []).append(node)

        for topic, t_nodes in topic_nodes.items():
            topic_dir = base_dir / topic
            topic_dir.mkdir(parents=True, exist_ok=True)
            lines = [f"# {topic.capitalize()} Index\n"]
            for n in sorted(t_nodes, key=lambda x: x.title.lower()):
                rel_path = f"{n.id}.md"
                clean_sum = n.summary.strip().replace("\n", " ")
                lines.append(f"* [{n.title}]({rel_path}) - {clean_sum}")
            (topic_dir / "index.md").write_text(
                "\n".join(lines) + "\n", encoding="utf-8"
            )

        # 2. Update MEMORY.md index entrypoint
        # Prioritize STABLE & VERIFIED nodes, demoting SUPERSEDED or lowest confidence if budget exceeds
        sorted_nodes = sorted(
            nodes,
            key=lambda n: (
                0 if n.frontmatter.status == MemoryStatus.STABLE else 1,
                0 if n.frontmatter.confidence == MemoryConfidence.VERIFIED else 1,
                n.title.lower(),
            ),
        )

        header_lines = [
            "---",
            'okf_version: "0.2"',
            "---",
            "",
            "# Memory Index",
            "",
        ]

        pointer_lines: list[str] = []
        for n in sorted_nodes:
            # Demote superseded or deprecated from top-level MEMORY.md if approaching budget
            if n.frontmatter.status in (
                MemoryStatus.DEPRECATED,
                MemoryStatus.SUPERSEDED,
            ):
                continue
            topic_sub = TOPIC_DIRS.get(n.kind.value, "misc")
            rel_link = f"{topic_sub}/{n.id}.md"
            summary_avail = MAX_LINE_CHARS - len(f"* [{n.title}]({rel_link}) - ") - 5
            truncated_summary = n.summary.strip().replace("\n", " ")[
                : max(10, summary_avail)
            ]
            pointer = f"* [{n.title}]({rel_link}) - {truncated_summary}"
            pointer_lines.append(pointer[:MAX_LINE_CHARS])

        # Slice to ensure <= 200 lines total
        allowed_pointers = MAX_MEMORY_LINES - len(header_lines) - 2
        final_pointers = pointer_lines[:allowed_pointers]

        content = "\n".join(header_lines + final_pointers) + "\n"
        (base_dir / "MEMORY.md").write_text(content, encoding="utf-8")

    def compact(self, scope: str = "project") -> list[str]:
        """Prune deprecated/superseded entries and enforce strict budget on MEMORY.md."""
        self.sync_indexes(scope)
        status = self.check_budget(scope)
        return status.violations

    def validate_bundle(self, scope: str = "project") -> dict[str, Any]:
        """Validate frontmatter, staleness of sources, broken relations, and budget."""
        nodes = self.list_nodes(scopes=[scope])
        budget = self.check_budget(scope)

        node_ids = {n.id for n in nodes}
        stale_nodes: list[dict[str, Any]] = []
        broken_relations: list[dict[str, Any]] = []

        for node in nodes:
            # Check source staleness
            for src in node.frontmatter.sources:
                res = verify_source_staleness(self.workspace_root, src)
                if res.is_stale:
                    stale_nodes.append(
                        {
                            "node_id": node.id,
                            "resource": src.resource,
                            "reason": res.reason,
                        }
                    )

            # Check internal memory relations
            for rel in node.frontmatter.relations:
                if rel.target.startswith("mem-") and rel.target not in node_ids:
                    broken_relations.append(
                        {
                            "node_id": node.id,
                            "relation": rel.to_dict(),
                        }
                    )

        return {
            "scope": scope,
            "total_nodes": len(nodes),
            "budget": {
                "total_lines": budget.total_lines,
                "total_bytes": budget.total_bytes,
                "is_valid": budget.is_valid,
                "violations": budget.violations,
            },
            "stale_nodes": stale_nodes,
            "broken_relations": broken_relations,
            "is_valid": budget.is_valid and len(stale_nodes) == 0,
        }
