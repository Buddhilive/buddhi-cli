import os
import sqlite3

def get_workspace_root(cwd=None):
    """Helper to locate the actual workspace root containing pyproject.toml or .git.
    Prioritizes BUDDHI_WORKSPACE_ROOT environment variable, falling back to walking up from CWD.
    """
    env_root = os.environ.get("BUDDHI_WORKSPACE_ROOT")
    if env_root:
        abs_env_root = os.path.abspath(env_root)
        if os.path.exists(abs_env_root):
            return abs_env_root

    if not cwd:
        cwd = os.getcwd()
    curr = os.path.abspath(cwd)
    while True:
        if os.path.exists(os.path.join(curr, "pyproject.toml")) or os.path.exists(os.path.join(curr, ".git")):
            return os.path.abspath(curr)
        parent = os.path.dirname(curr)
        if parent == curr:
            break
        curr = parent
    
    return os.path.abspath(cwd)


def get_db_path(cwd=None):
    """Finds the root of the workspace and returns the database path in the .buddhi folder.
    """
    root = get_workspace_root(cwd)
    db_dir = os.path.join(root, ".buddhi")
    os.makedirs(db_dir, exist_ok=True)
    return os.path.join(db_dir, "graph.db")


class CodeGraphDB:
    def __init__(self, db_path=None):
        if not db_path:
            db_path = get_db_path()
        self.db_path = db_path
        self.init_db()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initializes tables for nodes, edges, and FTS5 search."""
        with self.get_connection() as conn:
            # Nodes table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS nodes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,          -- 'module', 'class', 'function', 'method'
                    file_path TEXT NOT NULL,
                    start_line INTEGER NOT NULL,
                    end_line INTEGER NOT NULL,
                    docstring TEXT,
                    community_id INTEGER DEFAULT 0
                )
            """)

            # Edges table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS edges (
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    type TEXT NOT NULL,          -- 'calls', 'inherits', 'contains'
                    PRIMARY KEY (source, target, type),
                    FOREIGN KEY (source) REFERENCES nodes(id) ON DELETE CASCADE,
                    FOREIGN KEY (target) REFERENCES nodes(id) ON DELETE CASCADE
                )
            """)

            # FTS5 virtual table for fast full-text searching
            try:
                conn.execute("""
                    CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
                        id UNINDEXED,
                        name,
                        docstring
                    )
                """)
            except sqlite3.OperationalError:
                # FTS5 might not be available in highly constrained python environments
                # Fallback to standard indexed columns if FTS5 is not compiled in SQLite
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS nodes_fts (
                        id TEXT PRIMARY KEY,
                        name TEXT,
                        docstring TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_nodes_fts_name ON nodes_fts(name)")

            conn.commit()

    def clear_database(self):
        """Wipes the database cleanly for full re-indexing."""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM edges")
            conn.execute("DELETE FROM nodes")
            try:
                conn.execute("DELETE FROM nodes_fts")
            except sqlite3.OperationalError:
                conn.execute("DELETE FROM nodes_fts")
            conn.commit()

    def insert_nodes(self, nodes):
        """Batch inserts or updates nodes in sqlite and syncs FTS."""
        with self.get_connection() as conn:
            for node in nodes:
                conn.execute("""
                    INSERT OR REPLACE INTO nodes (id, name, type, file_path, start_line, end_line, docstring)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    node["id"],
                    node["name"],
                    node["type"],
                    node["file_path"],
                    node["start_line"],
                    node["end_line"],
                    node.get("docstring", "")
                ))
                
                # Sync FTS
                try:
                    conn.execute("DELETE FROM nodes_fts WHERE id = ?", (node["id"],))
                    conn.execute("""
                        INSERT INTO nodes_fts (id, name, docstring)
                        VALUES (?, ?, ?)
                    """, (node["id"], node["name"], node.get("docstring", "")))
                except sqlite3.OperationalError:
                    conn.execute("INSERT OR REPLACE INTO nodes_fts (id, name, docstring) VALUES (?, ?, ?)",
                                 (node["id"], node["name"], node.get("docstring", "")))
            conn.commit()

    def insert_edges(self, edges):
        """Batch inserts structural dependency edges."""
        with self.get_connection() as conn:
            for edge in edges:
                conn.execute("""
                    INSERT OR IGNORE INTO edges (source, target, type)
                    VALUES (?, ?, ?)
                """, (edge["source"], edge["target"], edge["type"]))
            conn.commit()

    def update_communities(self, community_mappings):
        """Updates nodes with community IDs from graph clustering."""
        with self.get_connection() as conn:
            for node_id, community_id in community_mappings.items():
                conn.execute("UPDATE nodes SET community_id = ? WHERE id = ?", (community_id, node_id))
            conn.commit()

    def get_all_nodes(self):
        """Fetches all nodes in the database."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM nodes")
            return [dict(row) for row in cursor.fetchall()]

    def get_all_edges(self):
        """Fetches all edges in the database."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM edges")
            return [dict(row) for row in cursor.fetchall()]

    def get_codebase_summary(self):
        """Returns functional communities and major entry point nodes within each community."""
        with self.get_connection() as conn:
            # Query nodes grouped by community
            cursor = conn.execute("""
                SELECT community_id, id, name, type, file_path, start_line, end_line, docstring
                FROM nodes
                ORDER BY community_id, type DESC, name
            """)
            rows = cursor.fetchall()
            
            communities = {}
            for row in rows:
                c_id = row["community_id"]
                if c_id not in communities:
                    communities[c_id] = []
                communities[c_id].append({
                    "id": row["id"],
                    "name": row["name"],
                    "type": row["type"],
                    "file_path": row["file_path"],
                    "start_line": row["start_line"],
                    "end_line": row["end_line"],
                    "docstring": row["docstring"] or ""
                })
            return communities

    def find_relevant_symbols(self, query):
        """Queries the FTS5 index for matching symbols and brings their 1-hop dependencies."""
        with self.get_connection() as conn:
            # Check if FTS5 table supports MATCH or normal search
            use_fts5 = False
            try:
                # Test FTS query to verify FTS5 support
                conn.execute("SELECT 1 FROM nodes_fts WHERE name MATCH 'test' LIMIT 0")
                use_fts5 = True
            except sqlite3.OperationalError:
                pass

            if use_fts5:
                # Sanitize query for FTS syntax
                fts_query = " OR ".join(f'"{q}*"' for q in query.replace('"', '').split() if q)
                if not fts_query:
                    fts_query = f'"{query}"'
                cursor = conn.execute("""
                    SELECT n.*
                    FROM nodes_fts fts
                    JOIN nodes n ON fts.id = n.id
                    WHERE nodes_fts MATCH ?
                    LIMIT 20
                """, (fts_query,))
            else:
                # Standard fallback search
                wildcard = f"%{query}%"
                cursor = conn.execute("""
                    SELECT * FROM nodes
                    WHERE name LIKE ? OR docstring LIKE ?
                    LIMIT 20
                """, (wildcard, wildcard))

            nodes = [dict(row) for row in cursor.fetchall()]
            
            # Hybrid search fallback: If FTS5 is active but returns no matches,
            # fall back to a robust substring LIKE search over names and docstrings.
            if use_fts5 and not nodes:
                wildcard = f"%{query}%"
                cursor = conn.execute("""
                    SELECT * FROM nodes
                    WHERE name LIKE ? OR docstring LIKE ?
                    LIMIT 20
                """, (wildcard, wildcard))
                nodes = [dict(row) for row in cursor.fetchall()]
            
            # Fetch 1-hop neighbors for each matched node
            results = []
            for node in nodes:
                node_id = node["id"]
                
                # Fetch outgoing neighbors (what this node relies on)
                out_cursor = conn.execute("""
                    SELECT n.id, n.name, n.type, n.file_path, e.type as rel_type
                    FROM edges e
                    JOIN nodes n ON e.target = n.id
                    WHERE e.source = ?
                """, (node_id,))
                depends_on = [dict(r) for r in out_cursor.fetchall()]

                # Fetch incoming neighbors (what relies on this node)
                in_cursor = conn.execute("""
                    SELECT n.id, n.name, n.type, n.file_path, e.type as rel_type
                    FROM edges e
                    JOIN nodes n ON e.source = n.id
                    WHERE e.target = ?
                """, (node_id,))
                called_by = [dict(r) for r in in_cursor.fetchall()]

                results.append({
                    "symbol": node,
                    "depends_on": depends_on,
                    "called_by": called_by
                })
            
            return results

    def trace_impact_radius(self, symbol_id, max_depth=3):
        """Performs an upstream recursive CTE query starting at symbol_id

        to discover all callers up to max_depth levels.
        """
        with self.get_connection() as conn:
            cursor = conn.execute("""
                WITH RECURSIVE impact_radius(node_id, depth) AS (
                    SELECT ?, 0
                    UNION
                    SELECT e.source, ir.depth + 1
                    FROM edges e
                    JOIN impact_radius ir ON e.target = ir.node_id
                    WHERE ir.depth < ?
                )
                SELECT DISTINCT ir.node_id, ir.depth, n.name, n.type, n.file_path, n.start_line, n.end_line
                FROM impact_radius ir
                LEFT JOIN nodes n ON ir.node_id = n.id
                WHERE ir.depth > 0
                ORDER BY ir.depth ASC
            """, (symbol_id, max_depth))
            return [dict(row) for row in cursor.fetchall()]

    def get_symbol_details(self, symbol_id):
        """Fetches direct details about a symbol by its ID."""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM nodes WHERE id = ?", (symbol_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
