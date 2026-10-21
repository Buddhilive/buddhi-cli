"""Graph-grounded OKF v0.2 documentation synthesis pipeline.

Extracts topological code graph intelligence (communities, cohesion, god nodes,
surprising connections, import cycles, confidence breakdowns) from tree-graph.db
and emits an agent-crawlable and human-navigable OKF Markdown bundle under .buddhi/docs/.
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Any

from buddhi.docgen.planner import (
    PlanEntry,
    build_docs_plan,
    read_existing_content_hash,
)
from buddhi.docgen.slug import (
    SlugResolver,
    safe_filename,
    stem_filename_budget,
    write_text_atomic_if_changed,
)
from buddhi.graph.analyze import (
    find_import_cycles,
    get_community_detail,
    get_god_nodes,
    get_graph_stats,
    get_surprising_connections,
    suggest_questions,
)
from buddhi.graph.model import CodeGraph
from buddhi.memory.frontmatter import dump_frontmatter, split_frontmatter


def _mermaid_community_flow(
    hub_name: str,
    top_members: list[dict[str, Any]],
    cross_links: list[dict[str, Any]],
) -> str:
    """Generate a clean, readable Mermaid diagram for a community."""
    lines = ["```mermaid", "flowchart LR"]
    lines.append(f'  hub["{safe_filename(hub_name, 30)} (Hub)"]')

    for idx, mem in enumerate(top_members[:6]):
        name = safe_filename(mem.get("name") or "symbol", 30)
        lines.append(f'  m{idx}["{name}"] --> hub')

    for idx, cl in enumerate(cross_links[:4]):
        target = safe_filename(cl.get("target_community") or "Other", 30)
        count = cl.get("shared_edges", 1)
        lines.append(f'  hub -. "{count} calls" .-> c{idx}["{target}"]')

    lines.append("```")
    return "\n".join(lines)


def _render_architecture_report(
    root_name: str,
    stats: dict[str, Any],
    god_nodes: list[dict[str, Any]],
    surprises: list[dict[str, Any]],
    questions: list[dict[str, Any]],
    cycles: list[list[str]],
    community_slugs: dict[int, str],
    god_slugs: dict[str, str],
    communities_data: dict[int, dict[str, Any]] | None = None,
) -> str:
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    meta = {
        "type": "Concept",
        "title": "Architecture Report",
        "description": f"Topological codebase audit and architecture analysis for {root_name}.",
        "status": "stable",
        "tags": ["architecture", "code-graph", "audit-report"],
        "generated": {
            "by": "buddhi-docgen",
            "at": today,
            "git_commit": stats.get("built_at_commit", "unknown"),
        },
    }

    conf = stats.get("confidence_breakdown", {})
    total_edges = stats.get("edges", 1) or 1
    ext_pct = round((conf.get("EXTRACTED", 0) / total_edges) * 100)
    inf_pct = round((conf.get("INFERRED", 0) / total_edges) * 100)
    amb_pct = round((conf.get("AMBIGUOUS", 0) / total_edges) * 100)

    body_lines = [
        f"# Architecture Report: {root_name}",
        "",
        "> Topological analysis generated from the Schema v2 Code Graph.",
        "",
        "## Corpus & Graph Health",
        f"- **Graph Size**: {stats.get('nodes', 0)} nodes, {stats.get('edges', 0)} edges across {stats.get('communities', 0)} Leiden communities.",
        f"- **Edge Confidence**: {ext_pct}% EXTRACTED, {inf_pct}% INFERRED, {amb_pct}% AMBIGUOUS.",
        f"- **Git Commit Freshness**: `{stats.get('built_at_commit', 'unknown')[:8]}` (Stale: {stats.get('is_stale', False)}).",
        "",
        "## Community Hubs",
    ]

    comm_map = communities_data or {}
    for cid, slug in sorted(community_slugs.items()):
        clabel = comm_map.get(cid, {}).get("label") or f"Community {cid}"
        body_lines.append(f"- [{clabel}](communities/{slug}.md)")

    body_lines += [
        "",
        "## God Nodes (Core Architectural Abstractions)",
        "The highest incident degree symbols representing load-bearing components:",
        "",
    ]

    for idx, gn in enumerate(god_nodes, 1):
        slug = god_slugs.get(gn["id"], "")
        link = f"[{gn['name']}](god-nodes/{slug}.md)" if slug else gn["name"]
        body_lines.append(
            f"{idx}. **{link}** ({gn.get('degree', 0)} connections) in `{gn.get('file_path', '')}`"
        )

    body_lines += [
        "",
        "## Surprising Connections",
        "Cross-community dependencies and unexpected bridge relationships:",
        "",
    ]
    if surprises:
        for s in surprises:
            rel = s.get("relation", "calls")
            conf_tier = s.get("confidence", "EXTRACTED")
            body_lines.append(
                f"- `{s.get('source', '')}` --{rel}--> `{s.get('target', '')}` `[{conf_tier}]`"
            )
    else:
        body_lines.append(
            "- None detected: all connections are within community boundaries."
        )

    body_lines += [
        "",
        "## Import Cycles",
    ]
    if cycles:
        for c in cycles:
            cycle_str = " -> ".join(c + [c[0]])
            body_lines.append(f"- {len(c)}-file cycle: `{cycle_str}`")
    else:
        body_lines.append("- None detected.")

    body_lines += [
        "",
        "## Suggested Review Questions",
        "_Questions this code graph is uniquely positioned to answer during planning and reviews:_\n",
    ]
    for q in questions:
        body_lines.append(f"- **{q.get('question', '')}**")
        if q.get("target"):
            body_lines.append(f"  _Focus: `{q.get('target', '')}`_")

    return dump_frontmatter(meta, "\n".join(body_lines))


def _render_community_article(
    cid: int,
    cdata: dict[str, Any],
    resolver: SlugResolver,
    community_slugs: dict[int, str],
) -> str:
    label = cdata.get("label") or f"Community {cid}"
    cohesion = cdata.get("cohesion", 0.0)
    hub_name = cdata.get("hub_node_id") or "Hub"
    members = cdata.get("members", [])
    cross_links = cdata.get("cross_community_links", [])

    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    meta = {
        "type": "Concept",
        "title": label,
        "description": f"Leiden Community {cid}: {len(members)} nodes with cohesion rating {cohesion:.2f}.",
        "status": "stable",
        "community_id": cid,
        "cohesion": round(cohesion, 2),
        "tags": ["community", f"community-{cid}"],
        "generated": {"by": "buddhi-docgen", "at": today},
    }

    body_lines = [
        f"# {label}",
        "",
        f"> Leiden Community {cid} · {len(members)} nodes · Cohesion: {cohesion:.2f}",
        "",
        "## Architecture & Callflow",
        "",
        _mermaid_community_flow(hub_name, members, cross_links),
        "",
        "## Key Member Symbols",
        "",
    ]

    for m in members[:25]:
        name = m.get("name") or m.get("id", "")
        deg = m.get("degree", 0)
        file_p = m.get("file_path", "")
        body_lines.append(f"- **{name}** ({deg} connections) in `{file_p}`")

    if len(members) > 25:
        body_lines.append(
            f"- _... and {len(members) - 25} more nodes in this community._"
        )

    body_lines += [
        "",
        "## Cross-Community Connections",
        "",
    ]
    if cross_links:
        for cl in cross_links:
            target_cid = cl.get("target_community_id")
            target_slug = community_slugs.get(target_cid)
            target_label = cl.get("target_community") or f"Community {target_cid}"
            link = (
                f"[{target_label}]({target_slug}.md)" if target_slug else target_label
            )
            body_lines.append(f"- {link}: {cl.get('shared_edges', 1)} shared calls")
    else:
        body_lines.append("- No strong cross-community bridges detected.")

    return dump_frontmatter(meta, "\n".join(body_lines))


def _render_god_node_article(
    gn: dict[str, Any],
    resolver: SlugResolver,
    community_slugs: dict[int, str],
) -> str:
    name = gn.get("name") or "Symbol"
    deg = gn.get("degree", 0)
    file_p = gn.get("file_path", "")
    cid = gn.get("community_id")
    cslug = community_slugs.get(cid) if cid is not None else None

    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    meta = {
        "type": "Concept",
        "title": name,
        "description": f"God Node: high-centrality abstraction with {deg} connections.",
        "status": "stable",
        "tags": ["god-node", "core-abstraction"],
        "generated": {"by": "buddhi-docgen", "at": today},
    }

    community_line = (
        f"Community: [{cslug}](../communities/{cslug}.md)" if cslug else "Unassigned"
    )

    body_lines = [
        f"# {name}",
        "",
        f"> God Node · {deg} incident connections · `{file_p}`",
        "",
        f"- **{community_line}**",
        "",
        "## Incident Relationships by Context",
        "",
    ]

    relations = gn.get("relations", [])
    if relations:
        for rel in relations[:30]:
            kind = rel.get("kind", "calls")
            target = rel.get("target", "")
            conf = rel.get("confidence", "EXTRACTED")
            body_lines.append(f"- `{kind}` -> `{target}` `[{conf}]`")
    else:
        body_lines.append("- No detailed incident edges recorded.")

    return dump_frontmatter(meta, "\n".join(body_lines))


def _render_symbol_stub(entry: PlanEntry) -> str:
    """Generate deterministic structural OKF concept doc (status: draft)."""
    meta = {
        "type": entry.kind.capitalize(),
        "title": entry.name,
        "description": f"{entry.kind.capitalize()} {entry.qualified_name} in {entry.file_path or 'unknown'}.",
        "status": "draft",
        "tags": [entry.language or "code", entry.file_path or "unknown"],
        "sources": [
            {
                "id": "src",
                "resource": f"{entry.file_path or 'unknown'}#L{entry.start_line or 1}-L{entry.end_line or 1}",
                "content_hash": entry.content_hash,
            }
        ],
        "relations": entry.relations,
    }

    body_lines = [
        f"# {entry.name}",
        "",
        f"> {entry.kind.capitalize()} defined in `{entry.file_path or 'unknown'}`.",
        "",
        "## Signature",
        "```",
        entry.signature or f"{entry.kind} {entry.name}()",
        "```",
        "",
        "## Relationships",
        f"- **Calls**: {', '.join(f'`{c}`' for c in entry.callees[:10]) if entry.callees else 'None'}",
        f"- **Called by**: {', '.join(f'`{c}`' for c in entry.callers[:10]) if entry.callers else 'None'}",
    ]
    return dump_frontmatter(meta, "\n".join(body_lines))


def generate_docs_bundle(
    root: Path,
    conn: sqlite3.Connection | None = None,
    graph: CodeGraph | None = None,
) -> int:
    """Synthesize complete graph-backed OKF documentation bundle into .buddhi/docs/."""
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    docs_dir = root / ".buddhi" / "docs"
    docs_dir.mkdir(parents=True, exist_ok=True)
    communities_dir = docs_dir / "communities"
    communities_dir.mkdir(parents=True, exist_ok=True)
    god_nodes_dir = docs_dir / "god-nodes"
    god_nodes_dir.mkdir(parents=True, exist_ok=True)

    db_path = root / ".buddhi" / "graphs" / "tree-graph.db"
    should_close_conn = False
    if conn is None and db_path.is_file():
        conn = sqlite3.connect(db_path)
        should_close_conn = True

    written_count = 0

    try:
        # 1. Topological analytics
        stats = get_graph_stats(conn, root) if conn else {}
        god_nodes = get_god_nodes(conn, top_n=10) if conn else []
        surprises = get_surprising_connections(conn, top_n=10) if conn else []
        questions = suggest_questions(conn, top_n=7) if conn else []
        cycles = find_import_cycles(conn, max_cycles=50) if conn else []

        # 2. Extract community records
        communities_data: dict[int, dict[str, Any]] = {}
        if conn:
            try:
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, label, cohesion, hub_node_id FROM communities ORDER BY id"
                )
                for r in cur.fetchall():
                    cid = r[0]
                    cdata = get_community_detail(conn, cid)
                    cdata["label"] = r[1] or f"Community {cid}"
                    cdata["cohesion"] = r[2] or 0.0
                    cdata["hub_node_id"] = r[3] or ""
                    communities_data[cid] = cdata
            except sqlite3.OperationalError:
                pass

        # 3. Two-pass slug resolution
        budget = stem_filename_budget(communities_dir, limit=180)
        resolver = SlugResolver(limit=budget)

        community_slugs: dict[int, str] = {}
        for cid, cdata in communities_data.items():
            slug = resolver.register(cdata.get("label") or f"community_{cid}")
            community_slugs[cid] = slug

        god_slugs: dict[str, str] = {}
        for gn in god_nodes:
            slug = resolver.register(gn.get("name") or "god_node")
            god_slugs[gn["id"]] = slug

        # 4. Synthesize Architecture Report
        report_content = _render_architecture_report(
            root_name=root.name,
            stats=stats,
            god_nodes=god_nodes,
            surprises=surprises,
            questions=questions,
            cycles=cycles,
            community_slugs=community_slugs,
            god_slugs=god_slugs,
            communities_data=communities_data,
        )
        if write_text_atomic_if_changed(
            docs_dir / "architecture-report.md", report_content
        ):
            written_count += 1

        # 5. Synthesize Community Hubs
        produced_community_files: set[str] = set()
        for cid, cdata in communities_data.items():
            slug = community_slugs[cid]
            ccontent = _render_community_article(cid, cdata, resolver, community_slugs)
            cpath = communities_dir / f"{slug}.md"
            if write_text_atomic_if_changed(cpath, ccontent):
                written_count += 1
            produced_community_files.add(cpath.name)

        # 6. Synthesize God Node Articles
        produced_god_files: set[str] = set()
        for gn in god_nodes:
            slug = god_slugs[gn["id"]]
            gcontent = _render_god_node_article(gn, resolver, community_slugs)
            gpath = god_nodes_dir / f"{slug}.md"
            if write_text_atomic_if_changed(gpath, gcontent):
                written_count += 1
            produced_god_files.add(gpath.name)

        # 7. Synthesize Root index.md
        index_meta = {
            "type": "Concept",
            "title": f"{root.name} Documentation Index",
            "description": f"Index of OKF documentation concepts and code graph for {root.name}.",
            "status": "stable",
            "okf_version": "0.2",
            "tags": ["index", "catalog"],
            "generated": {"by": "buddhi-docgen", "at": today},
        }
        index_lines = [
            f"# {root.name} Documentation Index",
            "",
            "> Root catalog for Open Knowledge Format concepts and code graph navigation.",
            "",
            "## Architecture Overview",
            "- [Architecture Report](architecture-report.md) — Structural health and graph analytics",
            "- [Interactive Code Graph](graphs/tree-graph.html) — Cytoscape graph visualization",
            "",
            "## Leiden Communities",
        ]
        for cid, slug in sorted(community_slugs.items()):
            clabel = communities_data[cid].get("label", f"Community {cid}")
            index_lines.append(f"- [{clabel}](communities/{slug}.md)")

        index_lines += ["", "## God Nodes (Core Abstractions)"]
        for gn in god_nodes:
            slug = god_slugs[gn["id"]]
            index_lines.append(
                f"- [{gn['name']}](god-nodes/{slug}.md) ({gn.get('degree', 0)} edges)"
            )

        index_content = dump_frontmatter(index_meta, "\n".join(index_lines))
        existing_index = docs_dir / "index.md"
        should_write_index = True
        if existing_index.is_file():
            try:
                exist_meta, _ = split_frontmatter(
                    existing_index.read_text(encoding="utf-8")
                )
                gen = (
                    exist_meta.get("generated")
                    if isinstance(exist_meta, dict)
                    else None
                )
                if not isinstance(gen, dict) or gen.get("by") != "buddhi-docgen":
                    should_write_index = False
            except (OSError, ValueError):
                should_write_index = False
        if should_write_index and write_text_atomic_if_changed(
            existing_index, index_content
        ):
            written_count += 1

        # 8. Structural Symbol Stubs with LLM Preservation
        if graph:
            plan = build_docs_plan(graph, root)
            for entry in plan:
                target_doc_path = root / entry.doc_path
                existing_hash = read_existing_content_hash(target_doc_path)
                # If existing doc has matching content_hash, preserve untouched!
                if existing_hash == entry.content_hash and target_doc_path.is_file():
                    continue

                stub_content = _render_symbol_stub(entry)
                if write_text_atomic_if_changed(target_doc_path, stub_content):
                    written_count += 1

        # 9. Orphan Sweeping for stale community and god-node files
        for f in communities_dir.glob("*.md"):
            if f.name not in produced_community_files:
                f.unlink(missing_ok=True)
        for f in god_nodes_dir.glob("*.md"):
            if f.name not in produced_god_files:
                f.unlink(missing_ok=True)

    finally:
        if should_close_conn and conn:
            conn.close()

    return written_count
