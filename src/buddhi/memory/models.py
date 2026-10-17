"""Core data models and enums for Google Open Knowledge Format (OKF v0.2) memory concepts.

Follows the OKF v0.2 standard while strictly excluding Attested Computation fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any


class MemoryKind(str, Enum):
    DECISION = "decision"
    CONVENTION = "convention"
    PREFERENCE = "preference"
    FEEDBACK = "feedback"
    SDD_RATIONALE = "sdd-rationale"
    DOMAIN_LEARNING = "domain-learning"


class MemoryStatus(str, Enum):
    DRAFT = "draft"
    STABLE = "stable"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class MemoryConfidence(str, Enum):
    VERIFIED = "verified"
    INFERRED = "inferred"
    PROPOSED = "proposed"


class RelationKind(str, Enum):
    SUPERSEDES = "supersedes"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    DERIVED_FROM_SPEC = "derived_from_spec"
    AFFECTS = "affects"


@dataclass
class MemorySource:
    id: str
    resource: str
    content_hash: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "resource": self.resource,
            "content_hash": self.content_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemorySource:
        return cls(
            id=str(data.get("id", "src")),
            resource=str(data.get("resource", "")),
            content_hash=str(data.get("content_hash", "")),
        )


@dataclass
class MemoryRelation:
    kind: RelationKind | str
    target: str

    def to_dict(self) -> dict[str, Any]:
        kind_str = (
            self.kind.value if isinstance(self.kind, RelationKind) else str(self.kind)
        )
        return {"kind": kind_str, "target": self.target}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryRelation:
        raw_kind = data.get("kind", RelationKind.RELATED_TO.value)
        try:
            kind_val: RelationKind | str = RelationKind(raw_kind)
        except ValueError:
            kind_val = str(raw_kind)
        return cls(kind=kind_val, target=str(data.get("target", "")))


@dataclass
class MemoryGenerated:
    by: str = "buddhi-cli"
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {"by": self.by, "at": self.at}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryGenerated:
        return cls(
            by=str(data.get("by", "buddhi-cli")),
            at=str(data.get("at", datetime.now(timezone.utc).isoformat())),
        )


@dataclass
class MemoryFrontmatter:
    id: str
    kind: MemoryKind
    title: str
    summary: str
    status: MemoryStatus = MemoryStatus.STABLE
    confidence: MemoryConfidence = MemoryConfidence.VERIFIED
    scope: str = "project"
    paths: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    generated: MemoryGenerated = field(default_factory=MemoryGenerated)
    sources: list[MemorySource] = field(default_factory=list)
    relations: list[MemoryRelation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind.value
            if isinstance(self.kind, MemoryKind)
            else str(self.kind),
            "title": self.title,
            "summary": self.summary,
            "status": self.status.value
            if isinstance(self.status, MemoryStatus)
            else str(self.status),
            "confidence": self.confidence.value
            if isinstance(self.confidence, MemoryConfidence)
            else str(self.confidence),
            "scope": self.scope,
        }
        if self.paths:
            d["paths"] = list(self.paths)
        if self.tags:
            d["tags"] = list(self.tags)
        d["generated"] = self.generated.to_dict()
        if self.sources:
            d["sources"] = [s.to_dict() for s in self.sources]
        if self.relations:
            d["relations"] = [r.to_dict() for r in self.relations]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryFrontmatter:
        # Resolve kind
        raw_kind = data.get("kind", MemoryKind.CONVENTION.value)
        try:
            kind_enum = MemoryKind(raw_kind)
        except ValueError:
            kind_enum = MemoryKind.CONVENTION

        # Resolve status
        raw_status = data.get("status", MemoryStatus.STABLE.value)
        try:
            status_enum = MemoryStatus(raw_status)
        except ValueError:
            status_enum = MemoryStatus.STABLE

        # Resolve confidence
        raw_conf = data.get("confidence", MemoryConfidence.VERIFIED.value)
        try:
            conf_enum = MemoryConfidence(raw_conf)
        except ValueError:
            conf_enum = MemoryConfidence.VERIFIED

        raw_gen = data.get("generated")
        generated = (
            MemoryGenerated.from_dict(raw_gen)
            if isinstance(raw_gen, dict)
            else MemoryGenerated()
        )

        raw_sources = data.get("sources", [])
        sources = [
            MemorySource.from_dict(s) for s in raw_sources if isinstance(s, dict)
        ]

        raw_relations = data.get("relations", [])
        relations = [
            MemoryRelation.from_dict(r) for r in raw_relations if isinstance(r, dict)
        ]

        raw_paths = data.get("paths", [])
        paths = [str(p) for p in raw_paths] if isinstance(raw_paths, list) else []

        raw_tags = data.get("tags", [])
        tags = [str(t) for t in raw_tags] if isinstance(raw_tags, list) else []

        return cls(
            id=str(data.get("id", "")),
            kind=kind_enum,
            title=str(data.get("title", "")),
            summary=str(data.get("summary", "")),
            status=status_enum,
            confidence=conf_enum,
            scope=str(data.get("scope", "project")),
            paths=paths,
            tags=tags,
            generated=generated,
            sources=sources,
            relations=relations,
        )


@dataclass
class MemoryNode:
    frontmatter: MemoryFrontmatter
    body: str = ""
    file_path: Path | None = None

    @property
    def id(self) -> str:
        return self.frontmatter.id

    @property
    def kind(self) -> MemoryKind:
        return self.frontmatter.kind

    @property
    def title(self) -> str:
        return self.frontmatter.title

    @property
    def summary(self) -> str:
        return self.frontmatter.summary

    def to_markdown(self) -> str:
        from buddhi.memory.frontmatter import dump_frontmatter

        return dump_frontmatter(self.frontmatter.to_dict(), self.body)

    @classmethod
    def from_markdown(cls, text: str, file_path: Path | None = None) -> MemoryNode:
        from buddhi.memory.frontmatter import split_frontmatter

        metadata, body = split_frontmatter(text)
        frontmatter = MemoryFrontmatter.from_dict(metadata)
        return cls(frontmatter=frontmatter, body=body, file_path=file_path)
