"""CodeGraph -> Cytoscape.js elements JSON."""

from __future__ import annotations

import json
from pathlib import Path

from buddhi.graph.model import CodeGraph
from buddhi.persist.atomic import atomic_write_bytes


def to_cytoscape_elements(graph: CodeGraph) -> dict:
    nodes = []
    for node in graph.nodes.values():
        data = {
            "id": node.id,
            "label": node.name,
            "kind": node.kind,
            "qualified_name": node.qualified_name,
            "file_path": node.file_path,
            "language": node.language,
            "start_line": node.start_line,
            "end_line": node.end_line,
            "external": node.external,
            "snippet": node.snippet,
            "community_id": node.community_id,
        }
        if node.parent_id:
            data["parent"] = node.parent_id
        nodes.append({"data": data})

    edges = []
    for i, edge in enumerate(graph.edges):
        edges.append(
            {
                "data": {
                    "id": f"e{i}",
                    "source": edge.source,
                    "target": edge.target,
                    "kind": edge.kind,
                    "resolved": edge.resolved,
                }
            }
        )

    return {"nodes": nodes, "edges": edges}


def write_json(graph: CodeGraph, path: Path) -> None:
    payload = to_cytoscape_elements(graph)
    data = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    atomic_write_bytes(path, data)
