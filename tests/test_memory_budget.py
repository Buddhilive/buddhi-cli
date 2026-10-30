from pathlib import Path

from buddhi.memory.models import (
    MemoryConfidence,
    MemoryFrontmatter,
    MemoryKind,
    MemoryNode,
    MemoryStatus,
)
from buddhi.memory.store import MemoryStore


def test_memory_store_budget_and_compaction(tmp_path: Path) -> None:
    store = MemoryStore(tmp_path)
    store.init_bundle("project")

    # Add 10 valid nodes
    for i in range(10):
        node = MemoryNode(
            frontmatter=MemoryFrontmatter(
                id=f"mem-decision-{i}",
                kind=MemoryKind.DECISION,
                title=f"Decision {i}",
                summary=f"This is decision summary number {i} with valuable rationale.",
                status=MemoryStatus.STABLE,
                confidence=MemoryConfidence.VERIFIED,
            ),
            body="# Details\n\nSome body text.",
        )
        store.save_node(node, "project")

    budget = store.check_budget("project")
    assert budget.is_valid
    assert budget.total_lines < 200
    assert budget.total_bytes < 25600

    # Add a superseded node
    superseded = MemoryNode(
        frontmatter=MemoryFrontmatter(
            id="mem-decision-old",
            kind=MemoryKind.DECISION,
            title="Old Decision",
            summary="This was superseded.",
            status=MemoryStatus.SUPERSEDED,
            confidence=MemoryConfidence.PROPOSED,
        ),
        body="Old text",
    )
    store.save_node(superseded, "project")

    # Verify MEMORY.md does not include superseded node in top index
    memory_md = tmp_path / ".agents" / "memory" / "MEMORY.md"
    content = memory_md.read_text(encoding="utf-8")
    assert "Decision 9" in content
    assert "Old Decision" not in content  # Pruned from top index

    # But it IS present in decisions/index.md
    decisions_index = tmp_path / ".agents" / "memory" / "decisions" / "index.md"
    d_content = decisions_index.read_text(encoding="utf-8")
    assert "Old Decision" in d_content
