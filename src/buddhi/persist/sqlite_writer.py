"""CodeGraph -> SQLite database with a nodes/edges schema tuned for recursive CTEs."""

from __future__ import annotations

import datetime
import os
import sqlite3
from pathlib import Path

from buddhi.graph.model import CodeGraph

_SCHEMA = """
PRAGMA foreign_keys = ON;

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
    external        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_nodes_parent ON nodes(parent_id);
CREATE INDEX idx_nodes_kind   ON nodes(kind);
CREATE INDEX idx_nodes_file   ON nodes(file_path);

CREATE TABLE edges (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id    TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id    TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL,
    resolved     INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_edges_kind_source ON edges(kind, source_id);
CREATE INDEX idx_edges_kind_target ON edges(kind, target_id);

CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def write_sqlite(graph: CodeGraph, path: Path, *, root_path: str) -> None:
    tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
    tmp_path.unlink(missing_ok=True)

    conn = sqlite3.connect(tmp_path)
    try:
        conn.executescript(_SCHEMA)
        conn.executemany(
            "INSERT INTO nodes (id, kind, name, qualified_name, file_path, language, "
            "start_line, end_line, parent_id, signature, external) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
                )
                for n in graph.nodes.values()
            ),
        )
        conn.executemany(
            "INSERT INTO edges (source_id, target_id, kind, resolved) VALUES (?, ?, ?, ?)",
            ((e.source, e.target, e.kind, int(e.resolved)) for e in graph.edges),
        )
        conn.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("generated_at", datetime.datetime.now(datetime.timezone.utc).isoformat()),
                ("root_path", root_path),
                ("node_count", str(len(graph.nodes))),
                ("edge_count", str(len(graph.edges))),
            ],
        )
        conn.commit()
    finally:
        conn.close()

    os.replace(tmp_path, path)
