from buddhi.memory.frontmatter import dump_frontmatter, split_frontmatter
from buddhi.memory.models import (
    MemoryConfidence,
    MemoryFrontmatter,
    MemoryKind,
    MemoryNode,
    MemoryRelation,
    MemorySource,
    MemoryStatus,
    RelationKind,
)


def test_memory_node_roundtrip() -> None:
    node = MemoryNode(
        frontmatter=MemoryFrontmatter(
            id="mem-decision-sqlite-wal",
            kind=MemoryKind.DECISION,
            title="Use SQLite WAL Mode",
            summary="Enable WAL mode for concurrency.",
            status=MemoryStatus.STABLE,
            confidence=MemoryConfidence.VERIFIED,
            scope="project",
            paths=["src/buddhi/persist/**/*.py"],
            tags=["sqlite", "concurrency"],
            sources=[
                MemorySource(
                    id="src-writer",
                    resource="src/buddhi/persist/sqlite_writer.py#L10-L20",
                    content_hash="abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234abcd1234",
                )
            ],
            relations=[
                MemoryRelation(
                    kind=RelationKind.SUPERSEDES,
                    target="mem-decision-sqlite-default",
                )
            ],
        ),
        body="# Context & Rationale\n\nConcurrency requires WAL.",
    )

    markdown = node.to_markdown()
    assert "okf_version" not in markdown
    assert "runtime" not in markdown  # Attested computation field excluded

    parsed = MemoryNode.from_markdown(markdown)
    assert parsed.id == "mem-decision-sqlite-wal"
    assert parsed.kind == MemoryKind.DECISION
    assert parsed.title == "Use SQLite WAL Mode"
    assert parsed.summary == "Enable WAL mode for concurrency."
    assert parsed.frontmatter.status == MemoryStatus.STABLE
    assert parsed.frontmatter.confidence == MemoryConfidence.VERIFIED
    assert len(parsed.frontmatter.sources) == 1
    assert (
        parsed.frontmatter.sources[0].resource
        == "src/buddhi/persist/sqlite_writer.py#L10-L20"
    )
    assert len(parsed.frontmatter.relations) == 1
    assert parsed.frontmatter.relations[0].kind == RelationKind.SUPERSEDES
    assert parsed.body == "# Context & Rationale\n\nConcurrency requires WAL."


def test_frontmatter_strips_forbidden_fields() -> None:
    raw = """---
id: test-node
kind: convention
title: Test
summary: Test summary
runtime: python-3.10
executor: sandbox-01
parameters: { foo: bar }
attester: pubkey-123
---

# Content
"""
    meta, body = split_frontmatter(raw)
    assert "runtime" not in meta
    assert "executor" not in meta
    assert "parameters" not in meta
    assert "attester" not in meta
    assert meta["id"] == "test-node"

    dumped = dump_frontmatter(meta, body)
    assert "runtime:" not in dumped
