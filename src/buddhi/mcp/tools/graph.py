"""Unified buddhi_graph MCP tool dispatcher."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from buddhi.graph.analyze import (
    find_import_cycles,
    find_shortest_path,
    get_community_detail,
    get_god_nodes,
    get_graph_stats,
    get_surprising_connections,
    suggest_questions,
)
from buddhi.graph.blast_radius import compute_blast_radius


def execute_buddhi_graph(
    action: str,
    db_path: str,
    root_path: Path | None = None,
    targets: list[str] | None = None,
    git_ref: str | None = None,
    staged: bool = False,
    source: str | None = None,
    target: str | None = None,
    community_id: int | None = None,
    max_hops: int = 3,
    top_n: int = 10,
    as_json: bool = False,
) -> str:
    """Execute action on CodeGraph SQLite database."""
    p = Path(db_path)
    if not p.is_file():
        err_payload = {
            "error": "graph_not_found",
            "hint": "Run `buddhi generate` or `buddhi init` to generate the code graph first.",
        }
        return (
            json.dumps(err_payload, indent=2)
            if as_json
            else f"Error: Code graph database not found at {db_path}. Run `buddhi generate` first."
        )

    root = root_path or Path.cwd()
    conn = sqlite3.connect(f"file:{p.resolve().as_posix()}?mode=ro", uri=True)

    try:
        if action == "blast_radius":
            report = compute_blast_radius(
                conn,
                targets=targets,
                git_ref=git_ref,
                staged=staged,
                max_hops=max_hops,
                root_path=root,
            )
            payload = {
                "risk_level": report.risk_level,
                "target_files": report.target_files,
                "target_nodes_count": len(report.target_nodes),
                "direct_callers_count": len(report.direct_callers),
                "direct_callers": report.direct_callers[:20],
                "transitive_callers_count": len(report.transitive_callers),
                "transitive_callers": report.transitive_callers[:20],
                "affected_communities": report.affected_communities,
                "impacted_god_nodes": report.impacted_god_nodes,
                "crossed_bridges_count": len(report.crossed_bridges),
                "import_cycles_involving_targets": report.new_import_cycles,
            }
            if as_json:
                return json.dumps(payload, indent=2)
            md = [
                f"# Blast Radius Report (Risk: **{report.risk_level.upper()}**)",
                f"- **Target Files**: {', '.join(report.target_files) or '(none)'}",
                f"- **Target Symbols**: {len(report.target_nodes)}",
                f"- **Direct Callers**: {len(report.direct_callers)}",
                f"- **Transitive Callers ({report.max_hops_traversed} hops)**: {len(report.transitive_callers)}",
                f"- **Impacted God Nodes**: {', '.join(report.impacted_god_nodes) or 'None'}",
                f"- **Affected Communities**: {len(report.affected_communities)}",
            ]
            for c in report.affected_communities:
                md.append(
                    f"  * Community {c['id']} (`{c['label']}`, cohesion: {c['cohesion']})"
                )
            if report.new_import_cycles:
                md.append(
                    f"- **Import Cycles**: {len(report.new_import_cycles)} cycle(s) detected involving targets"
                )
            return "\n".join(md)

        elif action == "god_nodes":
            gods = get_god_nodes(conn, top_n=top_n)
            if as_json:
                return json.dumps(gods, indent=2)
            lines = ["# Architectural God Nodes (Top Hubs)"]
            for g in gods:
                lines.append(
                    f"- `{g['id']}` (degree: **{g['degree']}**, file: `{g['file_path']}`)"
                )
            return "\n".join(lines)

        elif action == "surprises":
            surprises = get_surprising_connections(conn, top_n=top_n)
            if as_json:
                return json.dumps(surprises, indent=2)
            lines = ["# Surprising Architectural Connections"]
            for s in surprises:
                lines.append(
                    f"- `{s['source_name']}` -> `{s['target_name']}` (score: **{s['surprise_score']}**, confidence: `{s['confidence']}`)"
                )
            return "\n".join(lines)

        elif action == "questions":
            qs = suggest_questions(conn, top_n=top_n)
            if as_json:
                return json.dumps(qs, indent=2)
            lines = ["# Suggested Architectural Review Questions"]
            for q in qs:
                lines.append(f"- **[{q['category'].upper()}]** {q['question']}")
            return "\n".join(lines)

        elif action == "shortest_path":
            if not source or not target:
                return (
                    "Error: Both 'source' and 'target' are required for shortest_path."
                )
            res = find_shortest_path(conn, source, target, max_hops=max_hops)
            if as_json:
                return json.dumps(res, indent=2)
            if res.get("found"):
                return f"# Shortest Path ({res['hops']} hops)\n" + " -> \n".join(
                    res["path"]
                )
            if "candidates" in res:
                return "Disambiguation required for symbol. Candidates:\n" + "\n".join(
                    f"- {c}" for c in res["candidates"]
                )
            return f"No path found between `{source}` and `{target}` within {max_hops} hops."

        elif action == "cycles":
            cycles = find_import_cycles(conn, max_cycles=top_n)
            if as_json:
                return json.dumps(cycles, indent=2)
            if not cycles:
                return "No circular imports detected in code graph."
            lines = [f"# Detected Circular Imports ({len(cycles)} cycles)"]
            for cycle in cycles:
                lines.append(f"- {' -> '.join(cycle)}")
            return "\n".join(lines)

        elif action == "community":
            if community_id is not None:
                detail: dict[str, Any] = get_community_detail(conn, community_id)
                if as_json:
                    return json.dumps(detail, indent=2)
                lines = [
                    f"# Community {detail['id']}: {detail.get('label', '')} (Cohesion: {detail.get('cohesion', 0.0)})"
                ]
                for m in detail.get("members", [])[:30]:
                    lines.append(f"- `{m['id']}` ({m['kind']}, `{m['file_path']}`)")
                return "\n".join(lines)
            else:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, label, node_count, cohesion, hub_node_id FROM communities ORDER BY id ASC"
                )
                comms = [
                    {
                        "id": r[0],
                        "label": r[1],
                        "node_count": r[2],
                        "cohesion": r[3],
                        "hub": r[4],
                    }
                    for r in cur.fetchall()
                ]
                if as_json:
                    return json.dumps(comms, indent=2)
                lines = [f"# Communities ({len(comms)} total)"]
                for comm in comms:
                    lines.append(
                        f"- **Community {comm['id']}** `{comm['label']}`: {comm['node_count']} nodes, cohesion {comm['cohesion']}"
                    )
                return "\n".join(lines)

                return "\n".join(lines)

        elif action == "stats":
            stats = get_graph_stats(conn, root)
            if as_json:
                return json.dumps(stats, indent=2)
            lines = [
                "# Code Graph Statistics",
                f"- **Nodes**: {stats['nodes']}",
                f"- **Edges**: {stats['edges']}",
                f"- **Communities**: {stats['communities']}",
                f"- **Built at Commit**: `{stats['built_at_commit']}`",
                f"- **Current Git HEAD**: `{stats['current_git_head']}`",
                f"- **Graph is Stale**: {'⚠️ YES (run `buddhi generate`)' if stats['is_stale'] else 'NO (fresh)'}",
            ]
            if "confidence_breakdown" in stats:
                lines.append(
                    f"- **Confidence Breakdown**: {stats['confidence_breakdown']}"
                )
            return "\n".join(lines)

        else:
            return f"Error: Unknown action '{action}'. Valid actions: blast_radius, god_nodes, surprises, questions, shortest_path, cycles, community, stats."

    finally:
        conn.close()
