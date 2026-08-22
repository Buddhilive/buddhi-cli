"""Deterministic RepoAgent-style doc planning: order, hashing, staleness.

buddhi never calls an LLM itself. This module only computes the structure an
external agent (Antigravity) needs to write docs in the right order with the
right context: a bottom-up (callees-before-callers) traversal of the
class/function/method subgraph, a content hash per node for change detection,
and a staleness check against any OKF doc already on disk.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path, PurePosixPath

from buddhi.graph.model import (
    CALLS,
    CLASS,
    FUNCTION,
    INHERITS,
    METHOD,
    CodeGraph,
    GraphNode,
)

_CLUSTERABLE_KINDS = (CLASS, FUNCTION, METHOD)
_ORDER_EDGE_KINDS = (CALLS, INHERITS)

_CONTENT_HASH_RE = re.compile(r"content_hash:\s*([0-9a-fA-F]+)")
_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)

_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.-]+")


def content_hash(snippet: str | None) -> str:
    return hashlib.sha256((snippet or "").encode("utf-8")).hexdigest()


def topological_doc_order(graph: CodeGraph) -> list[GraphNode]:
    """Return clusterable nodes ordered so every callee/base precedes its callers.

    Cycles (mutual/recursive calls) can't be strictly ordered; nodes involved
    in a cycle are appended in a stable (id-sorted) order once every node
    outside the cycle that can be resolved has been. This never raises on
    cyclic graphs — RepoAgent's own DAG assumption doesn't hold for real
    codebases with recursion, so we degrade gracefully instead of crashing.
    """
    nodes = {n.id: n for n in graph.nodes.values() if n.kind in _CLUSTERABLE_KINDS}
    if not nodes:
        return []

    # dependency edges: source depends on target (target must be documented first)
    depends_on: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    dependents: dict[str, set[str]] = {node_id: set() for node_id in nodes}
    for edge in graph.edges:
        if edge.kind not in _ORDER_EDGE_KINDS:
            continue
        if edge.source not in nodes or edge.target not in nodes:
            continue
        if edge.source == edge.target:
            continue
        depends_on[edge.source].add(edge.target)
        dependents[edge.target].add(edge.source)

    remaining_deps = {node_id: set(deps) for node_id, deps in depends_on.items()}
    ready = sorted(node_id for node_id, deps in remaining_deps.items() if not deps)
    ordered: list[str] = []
    seen: set[str] = set()

    while ready:
        ready.sort()
        node_id = ready.pop(0)
        if node_id in seen:
            continue
        seen.add(node_id)
        ordered.append(node_id)
        for dependent in sorted(dependents.get(node_id, ())):
            if dependent in seen:
                continue
            remaining_deps[dependent].discard(node_id)
            if not remaining_deps[dependent]:
                ready.append(dependent)

    # Anything left is part of a cycle; append deterministically.
    leftover = sorted(node_id for node_id in nodes if node_id not in seen)
    ordered.extend(leftover)

    return [nodes[node_id] for node_id in ordered]


def _safe_component(text: str) -> str:
    return _SAFE_NAME_RE.sub("_", text).strip("_") or "_"


def doc_path_for_node(node: GraphNode) -> str:
    """Where the OKF concept doc for this node should live, relative to the repo root."""
    file_path = node.file_path or "unknown"
    posix = PurePosixPath(file_path)
    doc_dir = posix.parent / posix.stem
    filename = f"{_safe_component(node.qualified_name)}.md"
    return str(PurePosixPath(".buddhi") / "docs" / doc_dir / filename)


def read_existing_content_hash(doc_abs_path: Path) -> str | None:
    """Extract `sources[0].content_hash` from an existing OKF doc's frontmatter, if any."""
    if not doc_abs_path.is_file():
        return None
    try:
        text = doc_abs_path.read_text(encoding="utf-8")
    except OSError:
        return None

    match = _FRONTMATTER_RE.match(text)
    frontmatter = match.group(1) if match else text
    hash_match = _CONTENT_HASH_RE.search(frontmatter)
    return hash_match.group(1) if hash_match else None


@dataclass
class PlanEntry:
    node_id: str
    kind: str
    name: str
    qualified_name: str
    file_path: str | None
    language: str | None
    start_line: int | None
    end_line: int | None
    snippet: str | None
    content_hash: str
    parent_id: str | None
    callers: list[str] = field(default_factory=list)
    callees: list[str] = field(default_factory=list)
    doc_path: str = ""
    needs_generation: bool = True


def build_docs_plan(graph: CodeGraph, root: Path) -> list[PlanEntry]:
    """Compute the ordered, staleness-annotated doc plan for `graph`."""
    ordered_nodes = topological_doc_order(graph)

    callers: dict[str, set[str]] = {n.id: set() for n in ordered_nodes}
    callees: dict[str, set[str]] = {n.id: set() for n in ordered_nodes}
    node_ids = set(callers)
    for edge in graph.edges:
        if edge.kind not in _ORDER_EDGE_KINDS:
            continue
        if edge.source not in node_ids or edge.target not in node_ids:
            continue
        callees[edge.source].add(edge.target)
        callers[edge.target].add(edge.source)

    plan: list[PlanEntry] = []
    for node in ordered_nodes:
        h = content_hash(node.snippet)
        doc_path = doc_path_for_node(node)
        existing_hash = read_existing_content_hash(root / doc_path)
        plan.append(
            PlanEntry(
                node_id=node.id,
                kind=node.kind,
                name=node.name,
                qualified_name=node.qualified_name,
                file_path=node.file_path,
                language=node.language,
                start_line=node.start_line,
                end_line=node.end_line,
                snippet=node.snippet,
                content_hash=h,
                parent_id=node.parent_id,
                callers=sorted(callers[node.id]),
                callees=sorted(callees[node.id]),
                doc_path=doc_path,
                needs_generation=(existing_hash != h),
            )
        )
    return plan


def plan_to_json(plan: list[PlanEntry]) -> list[dict]:
    return [asdict(entry) for entry in plan]
