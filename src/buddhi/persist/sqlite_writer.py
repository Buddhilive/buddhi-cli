"""CodeGraph -> SQLite database with a nodes/edges schema tuned for recursive CTEs."""

from __future__ import annotations

import datetime
import json
import os
import sqlite3
import time
from pathlib import Path

from buddhi.graph.model import CodeGraph

SCHEMA_VERSION = "2"

_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = MEMORY;
PRAGMA synchronous = OFF;

CREATE TABLE nodes (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    name            TEXT NOT NULL,
    qualified_name  TEXT,
    file_path       TEXT,
    language        TEXT,
    start_line      INTEGER,
    end_line        INTEGER,
    parent_id       TEXT REFERENCES nodes(id) ON DELETE CASCADE,
    signature       TEXT,
    external        INTEGER NOT NULL DEFAULT 0 CHECK (external IN (0, 1)),
    snippet         TEXT,
    community_id    INTEGER
);

CREATE INDEX idx_nodes_parent       ON nodes(parent_id);
CREATE INDEX idx_nodes_kind         ON nodes(kind);
CREATE INDEX idx_nodes_file         ON nodes(file_path);
CREATE INDEX idx_nodes_community    ON nodes(community_id) WHERE community_id IS NOT NULL;
CREATE INDEX idx_nodes_name_lower   ON nodes(LOWER(name), external);
CREATE INDEX idx_nodes_qname_lower  ON nodes(LOWER(qualified_name), external);

CREATE TABLE edges (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id        TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id        TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    kind             TEXT NOT NULL,
    resolved         INTEGER NOT NULL DEFAULT 1 CHECK (resolved IN (0, 1)),
    confidence       TEXT NOT NULL DEFAULT 'EXTRACTED'
                     CHECK (confidence IN ('EXTRACTED', 'INFERRED', 'AMBIGUOUS')),
    confidence_score REAL NOT NULL DEFAULT 1.0
                     CHECK (confidence_score >= 0.0 AND confidence_score <= 1.0),
    context          TEXT NOT NULL DEFAULT 'contains'
                     CHECK (context IN ('call', 'import', 'inherit', 'type_ref', 'contains'))
);

CREATE INDEX idx_edges_kind_source   ON edges(kind, source_id);
CREATE INDEX idx_edges_kind_target   ON edges(kind, target_id);
CREATE INDEX idx_edges_source_target ON edges(source_id, target_id, kind);
CREATE INDEX idx_edges_confidence    ON edges(confidence) WHERE confidence != 'EXTRACTED';

CREATE TABLE communities (
    id          INTEGER PRIMARY KEY,
    label       TEXT NOT NULL,
    node_count  INTEGER NOT NULL CHECK (node_count >= 0),
    cohesion    REAL NOT NULL CHECK (cohesion >= 0.0 AND cohesion <= 1.0),
    hub_node_id TEXT REFERENCES nodes(id) ON DELETE SET NULL,
    top_files   TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE extract_cache (
    file_path    TEXT PRIMARY KEY,
    sha256       TEXT NOT NULL,
    language     TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);

CREATE INDEX idx_extract_cache_sha256 ON extract_cache(file_path, sha256);

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def get_db_capabilities(conn: sqlite3.Connection) -> dict[str, bool]:
    """Inspect SQLite database capabilities to ensure backward compatibility."""
    tables = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    edge_cols = (
        {r[1] for r in conn.execute("PRAGMA table_info(edges)")}
        if "edges" in tables
        else set()
    )
    return {
        "has_communities": "communities" in tables,
        "has_extract_cache": "extract_cache" in tables,
        "has_edge_confidence": "confidence" in edge_cols,
        "has_edge_context": "context" in edge_cols,
    }


def load_extract_cache(db_path: Path) -> dict[str, tuple[str, str, str, str]]:
    """Load existing (file_path -> (sha256, language, payload_json, updated_at)) from tree-graph.db."""
    if not db_path.is_file():
        return {}

    try:
        conn = sqlite3.connect(f"file:{db_path.resolve().as_posix()}?mode=ro", uri=True)
        try:
            caps = get_db_capabilities(conn)
            if not caps["has_extract_cache"]:
                return {}
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_path, sha256, language, payload_json, updated_at FROM extract_cache"
            )
            return {
                row[0]: (row[1], row[2], row[3], row[4]) for row in cursor.fetchall()
            }
        finally:
            conn.close()
    except (sqlite3.OperationalError, sqlite3.DatabaseError, OSError):
        return {}


def write_sqlite(
    graph: CodeGraph,
    path: Path,
    *,
    root_path: str,
    extract_cache_entries: list[tuple[str, str, str, str, str]] | None = None,
) -> None:
    """Atomically write CodeGraph to SQLite database (Schema v2)."""
    tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp_path.unlink(missing_ok=True)

    conn = sqlite3.connect(tmp_path)
    try:
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO nodes (id, kind, name, qualified_name, file_path, language, "
            "start_line, end_line, parent_id, signature, external, snippet, community_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    n.id,
                    n.kind,
                    n.name,
                    n.qualified_name,
                    n.file_path,
                    n.language,
                    n.start_line,
                    n.end_line,
                    n.parent_id,
                    n.signature,
                    int(n.external),
                    n.snippet,
                    n.community_id,
                )
                for n in graph.nodes.values()
            ),
        )

        conn.executemany(
            "INSERT INTO edges (source_id, target_id, kind, resolved, confidence, confidence_score, context) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                (
                    e.source,
                    e.target,
                    e.kind,
                    int(e.resolved),
                    e.confidence,
                    float(e.confidence_score),
                    e.context,
                )
                for e in graph.edges
            ),
        )

        if graph.communities:
            conn.executemany(
                "INSERT INTO communities (id, label, node_count, cohesion, hub_node_id, top_files) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        c.id,
                        c.label,
                        c.node_count,
                        float(c.cohesion),
                        c.hub_node_id,
                        json.dumps(c.top_files, ensure_ascii=False),
                    )
                    for c in graph.communities.values()
                ),
            )

        if extract_cache_entries:
            conn.executemany(
                "INSERT OR REPLACE INTO extract_cache (file_path, sha256, language, payload_json, updated_at) "
                "VALUES (?, ?, ?, ?, ?)",
                extract_cache_entries,
            )

        meta_entries = [
            ("schema_version", SCHEMA_VERSION),
            ("generated_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
            ("root_path", root_path),
            ("node_count", str(len(graph.nodes))),
            ("edge_count", str(len(graph.edges))),
            ("community_count", str(len(graph.communities))),
            ("built_at_commit", graph.built_at_commit or ""),
        ]
        conn.executemany("INSERT INTO meta (key, value) VALUES (?, ?)", meta_entries)
        conn.commit()
    finally:
        conn.close()

    # Retry replace for Windows file locks
    for attempt in range(4):
        try:
            os.replace(tmp_path, path)
            break
        except PermissionError:
            if attempt == 3:
                raise
            time.sleep(0.025 * (attempt + 1))
