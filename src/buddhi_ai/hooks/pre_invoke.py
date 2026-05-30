"""
pre_invoke — Proactive Trajectory Injector for Antigravity PreInvocation hooks.

Executes before the LLM generates its next response. Reads the active
workspace context, queries the .buddhi/graph.db Leiden community structure,
and injects an ephemeral message containing domain awareness so the agent
stays aligned with the codebase architecture.

Protocol:
  1. Read JSON from stdin (Antigravity context dump).
  2. Identify active/focused files from workspacePaths.
  3. Query graph.db for community_id of those files.
  4. Synthesize a concise spatial awareness summary.
  5. Emit an injectSteps payload on stdout.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path


def _find_db(workspace_paths: list[str]) -> Path | None:
    """Locate .buddhi/graph.db from the workspace paths."""
    candidates: list[Path] = []
    for wp in workspace_paths:
        p = Path(wp).resolve()
        candidates.append(p / ".buddhi" / "graph.db")
        # Also try parent directories
        for parent in p.parents:
            candidates.append(parent / ".buddhi" / "graph.db")

    # Also check CWD
    candidates.append(Path.cwd().resolve() / ".buddhi" / "graph.db")

    for c in candidates:
        if c.exists():
            return c
    return None


def _query_communities(
    db_path: Path, rel_paths: list[str]
) -> dict[int, list[str]]:
    """Return {community_id: [node_names]} for the given relative file paths."""
    if not rel_paths:
        return {}

    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA foreign_keys = ON;")

    communities: dict[int, list[str]] = {}

    try:
        placeholders = ",".join("?" for _ in rel_paths)
        rows = conn.execute(
            f"""
            SELECT n.community_id, n.name, n.node_type, f.path
            FROM nodes n
            JOIN files f ON n.file_id = f.id
            WHERE f.path IN ({placeholders})
              AND n.community_id IS NOT NULL
            ORDER BY n.community_id
            """,
            rel_paths,
        ).fetchall()

        for community_id, name, node_type, _file_path in rows:
            if community_id not in communities:
                communities[community_id] = []
            label = f"{name} ({node_type})" if name else node_type
            communities[community_id].append(label)
    finally:
        conn.close()

    return communities


def _synthesize_message(communities: dict[int, list[str]]) -> str:
    """Build a concise community awareness summary."""
    if not communities:
        return ""

    parts: list[str] = []
    for cid, members in sorted(communities.items()):
        # Deduplicate and cap at 8 members for brevity
        unique = list(dict.fromkeys(members))
        display = unique[:8]
        suffix = f" (+{len(unique) - 8} more)" if len(unique) > 8 else ""
        parts.append(
            f"  • Leiden Community #{cid}: {', '.join(display)}{suffix}"
        )

    community_str = "\n".join(parts)
    return (
        f"⚠️ BUDDHI-AI CONTEXT ALERT: You are currently navigating within "
        f"the following localized code communities:\n{community_str}\n"
        f"When evaluating dependencies, prioritize structures within these "
        f"domains before searching external namespaces."
    )


def _resolve_relative_paths(
    workspace_paths: list[str], active_files: list[str]
) -> list[str]:
    """Convert absolute file paths to workspace-relative paths."""
    rel: list[str] = []
    for af in active_files:
        af_resolved = Path(af).resolve()
        for wp in workspace_paths:
            wp_resolved = Path(wp).resolve()
            try:
                r = af_resolved.relative_to(wp_resolved)
                rel.append(str(r).replace("\\", "/"))
                break
            except ValueError:
                continue
    return rel


def main() -> None:
    """Entrypoint for the pre_invoke hook script."""
    raw = sys.stdin.read()
    if not raw.strip():
        # No context — emit empty inject
        json.dump({"injectSteps": []}, sys.stdout)
        return

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        json.dump({"injectSteps": []}, sys.stdout)
        return

    workspace_paths = payload.get("workspacePaths", [])
    active_files = payload.get("activeFiles", [])

    if not workspace_paths or not active_files:
        json.dump({"injectSteps": []}, sys.stdout)
        return

    # Locate the graph database
    db_path = _find_db(workspace_paths)
    if db_path is None:
        json.dump({"injectSteps": []}, sys.stdout)
        return

    # Resolve relative paths and query communities
    rel_paths = _resolve_relative_paths(workspace_paths, active_files)
    if not rel_paths:
        json.dump({"injectSteps": []}, sys.stdout)
        return

    communities = _query_communities(db_path, rel_paths)
    message = _synthesize_message(communities)

    if not message:
        json.dump({"injectSteps": []}, sys.stdout)
        return

    json.dump(
        {
            "injectSteps": [
                {
                    "type": "ephemeralMessage",
                    "content": message,
                }
            ]
        },
        sys.stdout,
    )


if __name__ == "__main__":
    main()
