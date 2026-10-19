"""Blast Radius analysis engine: evaluate transitive change impact across symbols, communities, and bridges."""

from __future__ import annotations

import re
import sqlite3
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from buddhi.graph.analyze import find_import_cycles
from buddhi.persist.sqlite_writer import get_db_capabilities

_SAFE_GIT_REF_PATTERN = re.compile(r"^[A-Za-z0-9_./~^@-]{1,128}$")


@dataclass
class BlastRadiusReport:
    target_nodes: list[str] = field(default_factory=list)
    target_files: list[str] = field(default_factory=list)
    direct_callers: list[str] = field(default_factory=list)
    transitive_callers: list[str] = field(default_factory=list)
    affected_communities: list[dict[str, Any]] = field(default_factory=list)
    impacted_god_nodes: list[str] = field(default_factory=list)
    crossed_bridges: list[dict[str, Any]] = field(default_factory=list)
    new_import_cycles: list[list[str]] = field(default_factory=list)
    risk_level: str = "low"  # low, medium, high, critical
    max_hops_traversed: int = 0


def _resolve_git_diff_files(
    root_path: Path, git_ref: str | None, staged: bool
) -> list[str]:
    """Safely obtain changed file paths from git diff."""
    cmd = ["git", "diff", "--name-only"]
    if staged:
        cmd.append("--cached")
    if git_ref:
        if git_ref.startswith("-") or not _SAFE_GIT_REF_PATTERN.fullmatch(git_ref):
            return []
        cmd.append(git_ref)
    cmd.extend(["--"])

    try:
        res = subprocess.run(
            cmd,
            cwd=root_path,
            capture_output=True,
            text=True,
            check=False,
            shell=False,
            timeout=5.0,
        )
        if res.returncode == 0:
            return [
                line.strip().replace("\\", "/")
                for line in res.stdout.splitlines()
                if line.strip()
            ]
    except (OSError, subprocess.SubprocessError):
        pass
    return []


def compute_blast_radius(
    conn: sqlite3.Connection,
    *,
    targets: list[str] | None = None,
    git_ref: str | None = None,
    staged: bool = False,
    max_hops: int = 3,
    root_path: Path | None = None,
) -> BlastRadiusReport:
    """Compute the impact radius of modified files or symbols."""
    max_hops = max(1, min(max_hops, 6))
    root = root_path or Path(".")

    target_files: set[str] = set()
    target_node_ids: set[str] = set()

    # 1. Resolve targets from git diff or explicit targets
    if git_ref or staged:
        diff_files = _resolve_git_diff_files(root, git_ref, staged)
        target_files.update(diff_files)
    elif targets:
        for t in targets:
            norm_t = t.replace("\\", "/").strip()
            if "/" in norm_t or norm_t.endswith((".py", ".ts", ".go")):
                target_files.add(norm_t)
            else:
                # Direct symbol name or ID
                cur = conn.cursor()
                cur.execute(
                    "SELECT id, file_path FROM nodes WHERE id = ? OR name = ? OR qualified_name = ?",
                    (norm_t, norm_t, norm_t),
                )
                for nid, fpath in cur.fetchall():
                    target_node_ids.add(nid)
                    if fpath:
                        target_files.add(fpath)
    else:
        # Default: working tree diff against HEAD
        diff_files = _resolve_git_diff_files(root, "HEAD", False)
        target_files.update(diff_files)

    # Resolve target files to symbol node IDs
    if target_files:
        placeholders = ",".join("?" for _ in target_files)
        cur = conn.cursor()
        cur.execute(
            f"SELECT id FROM nodes WHERE file_path IN ({placeholders}) AND kind IN ('class', 'function', 'method')",
            list(target_files),
        )
        for (nid,) in cur.fetchall():
            target_node_ids.add(nid)

    if not target_node_ids:
        return BlastRadiusReport(
            target_files=sorted(target_files),
            risk_level="low",
        )

    # 2. Detect super-hubs to block expansion
    cur = conn.cursor()
    cur.execute("""
        SELECT node_id, COUNT(*) FROM (
            SELECT source_id AS node_id FROM edges WHERE kind IN ('calls', 'inherits') AND resolved = 1
            UNION ALL
            SELECT target_id AS node_id FROM edges WHERE kind IN ('calls', 'inherits') AND resolved = 1
        ) GROUP BY node_id
    """)
    deg_map = dict(cur.fetchall())
    degs = sorted(deg_map.values())
    p99 = degs[int(0.99 * len(degs))] if degs else 50
    hub_thresh = max(50, p99)
    super_hubs = {nid for nid, deg in deg_map.items() if deg > hub_thresh}

    # 3. Hub-Blocked Reverse BFS (find incoming callers/dependents)
    direct_callers: set[str] = set()
    transitive_callers: set[str] = set()
    impacted_god_nodes: set[str] = set()
    visited: set[str] = set(target_node_ids)
    current_frontier = set(target_node_ids)

    actual_hops = 0
    for hop in range(1, max_hops + 1):
        if not current_frontier:
            break
        actual_hops = hop
        next_frontier: set[str] = set()
        p_holders = ",".join("?" for _ in current_frontier)
        cur.execute(
            f"SELECT source_id, target_id FROM edges WHERE target_id IN ({p_holders}) AND kind IN ('calls', 'inherits') AND resolved = 1",
            list(current_frontier),
        )
        for src, tgt in cur.fetchall():
            if src in visited:
                continue
            visited.add(src)
            if hop == 1:
                direct_callers.add(src)
            else:
                transitive_callers.add(src)

            if src in super_hubs:
                impacted_god_nodes.add(src)
                # Hub-block: do NOT add super-hub to next_frontier
            else:
                next_frontier.add(src)

        current_frontier = next_frontier

    # 4. Affected Communities & Crossed Bridges
    all_impacted_nodes = target_node_ids | direct_callers | transitive_callers
    all_placeholders = ",".join("?" for _ in all_impacted_nodes)
    cur.execute(
        f"SELECT id, community_id FROM nodes WHERE id IN ({all_placeholders}) AND community_id IS NOT NULL",
        list(all_impacted_nodes),
    )
    node_to_comm = dict(cur.fetchall())
    impacted_comm_ids = set(node_to_comm.values())

    caps = get_db_capabilities(conn)
    affected_comms: list[dict[str, Any]] = []
    if caps["has_communities"] and impacted_comm_ids:
        c_placeholders = ",".join("?" for _ in impacted_comm_ids)
        cur.execute(
            f"SELECT id, label, node_count, cohesion FROM communities WHERE id IN ({c_placeholders})",
            list(impacted_comm_ids),
        )
        for cid, label, ncount, cohesion in cur.fetchall():
            affected_comms.append(
                {
                    "id": cid,
                    "label": label,
                    "node_count": ncount,
                    "cohesion": cohesion,
                }
            )

    # Crossed bridges on the impact frontier
    crossed_bridges: list[dict[str, Any]] = []
    for src in direct_callers | transitive_callers:
        s_comm = node_to_comm.get(src)
        if s_comm is not None:
            for tgt in target_node_ids:
                t_comm = node_to_comm.get(tgt)
                if t_comm is not None and s_comm != t_comm:
                    crossed_bridges.append(
                        {"from": src, "to": tgt, "from_comm": s_comm, "to_comm": t_comm}
                    )

    # 5. Import cycles
    import_cycles = find_import_cycles(conn, max_cycles=10)
    relevant_cycles = [c for c in import_cycles if any(f in target_files for f in c)]

    # 6. Risk Level Calculation
    total_callers = len(direct_callers) + len(transitive_callers)
    low_cohesion_affected = any(c["cohesion"] < 0.10 for c in affected_comms)

    if len(relevant_cycles) > 0 or len(impacted_god_nodes) >= 2 or total_callers >= 50:
        risk = "critical"
    elif len(impacted_god_nodes) >= 1 or low_cohesion_affected or total_callers >= 20:
        risk = "high"
    elif total_callers >= 5 or len(crossed_bridges) >= 3:
        risk = "medium"
    else:
        risk = "low"

    return BlastRadiusReport(
        target_nodes=sorted(target_node_ids),
        target_files=sorted(target_files),
        direct_callers=sorted(direct_callers),
        transitive_callers=sorted(transitive_callers),
        affected_communities=affected_comms,
        impacted_god_nodes=sorted(impacted_god_nodes),
        crossed_bridges=crossed_bridges[:25],
        new_import_cycles=relevant_cycles,
        risk_level=risk,
        max_hops_traversed=actual_hops,
    )
