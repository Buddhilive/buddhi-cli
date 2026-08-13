"""Core node/edge data model for the code graph."""

from __future__ import annotations

from dataclasses import dataclass, field

# Node kinds
DIRECTORY = "directory"
FILE = "file"
MODULE = "module"
CLASS = "class"
FUNCTION = "function"
METHOD = "method"
EXTERNAL = "external"

# Edge kinds
CONTAINS = "contains"
IMPORTS = "imports"
CALLS = "calls"
INHERITS = "inherits"


@dataclass
class GraphNode:
    id: str
    kind: str
    name: str
    qualified_name: str
    file_path: str | None = None
    language: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    parent_id: str | None = None
    signature: str | None = None
    external: bool = False


@dataclass
class GraphEdge:
    source: str
    target: str
    kind: str
    resolved: bool = True


def file_node_id(rel_path: str) -> str:
    return f"file:{rel_path}"


def dir_node_id(rel_path: str) -> str:
    return f"dir:{rel_path}"


def symbol_node_id(kind: str, rel_path: str, qualified_name: str) -> str:
    return f"{kind}:{rel_path}::{qualified_name}"


def external_node_id(dotted_name: str) -> str:
    return f"external:{dotted_name}"


@dataclass
class CodeGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: list[GraphEdge] = field(default_factory=list)

    def add_node(self, node: GraphNode) -> GraphNode:
        existing = self.nodes.get(node.id)
        if existing is not None:
            return existing
        self.nodes[node.id] = node
        return node

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)

    def get_or_create_external(self, dotted_name: str) -> GraphNode:
        node_id = external_node_id(dotted_name)
        existing = self.nodes.get(node_id)
        if existing is not None:
            return existing
        node = GraphNode(
            id=node_id,
            kind=EXTERNAL,
            name=dotted_name.rsplit(".", 1)[-1],
            qualified_name=dotted_name,
            external=True,
        )
        return self.add_node(node)
