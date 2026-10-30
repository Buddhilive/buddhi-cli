"""SDD topological impact analyzer: bridges spec/plan and code graph."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path
from typing import Any

from buddhi.graph.analyze import (
    find_import_cycles,
    get_god_nodes,
    get_graph_stats,
    suggest_questions,
)
from buddhi.graph.blast_radius import compute_blast_radius
from buddhi.sdd.common import get_feature_paths


def compute_sdd_topology_context(
    repo_root: Path,
    targets: list[str] | None = None,
    git_ref: str | None = None,
    staged: bool = False,
) -> dict[str, Any]:
    """Compute topological summary and blast radius for the active SDD context."""
    db_path = repo_root / ".buddhi" / "graphs" / "tree-graph.db"
    if not db_path.is_file():
        return {
            "status": "no_graph",
            "hint": "Run `buddhi generate` to enable topological context.",
        }

    conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
    try:
        report = compute_blast_radius(
            conn,
            targets=targets,
            git_ref=git_ref,
            staged=staged,
            max_hops=3,
            root_path=repo_root,
        )
        gods = get_god_nodes(conn, top_n=5)
        questions = suggest_questions(conn, top_n=5)
        cycles = find_import_cycles(conn, max_cycles=5)
        stats = get_graph_stats(conn, repo_root)

        return {
            "status": "ready",
            "blast_radius": {
                "risk_level": report.risk_level,
                "target_files": report.target_files,
                "target_nodes_count": len(report.target_nodes),
                "direct_callers_count": len(report.direct_callers),
                "transitive_callers_count": len(report.transitive_callers),
                "affected_communities": report.affected_communities,
                "impacted_god_nodes": report.impacted_god_nodes,
            },
            "top_god_nodes": gods,
            "suggested_questions": questions,
            "import_cycles": cycles,
            "graph_stats": stats,
        }
    finally:
        conn.close()


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    json_mode = "--json" in args
    staged = "--staged" in args
    git_ref = None
    if "--git-ref" in args:
        idx = args.index("--git-ref")
        if idx + 1 < len(args):
            git_ref = args[idx + 1]

    try:
        paths = get_feature_paths(script_file=Path(__file__))
        repo_root = paths.repo_root
    except (RuntimeError, ValueError, OSError):
        repo_root = Path.cwd().resolve()

    res = compute_sdd_topology_context(repo_root, git_ref=git_ref, staged=staged)
    if json_mode:
        print(json.dumps(res, indent=2))
    else:
        if res.get("status") == "no_graph":
            print(res.get("hint", "No graph found."))
        else:
            br = res.get("blast_radius", {})
            print(f"Topological Impact (Risk: {br.get('risk_level', 'low').upper()})")
            print(
                f"- Target files: {', '.join(br.get('target_files', [])) or '(none)'}"
            )
            print(f"- Direct callers: {br.get('direct_callers_count', 0)}")
            print(f"- Transitive callers: {br.get('transitive_callers_count', 0)}")
            print(
                f"- Impacted god nodes: {', '.join(br.get('impacted_god_nodes', [])) or 'None'}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
