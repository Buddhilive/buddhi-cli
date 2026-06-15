import sqlite3
from pathlib import Path

def get_metrics_db_path() -> Path:
    """Returns the path to the global metrics SQLite database."""
    # Global user-level metrics path (not per-workspace)
    buddhi_dir = Path.home() / ".buddhi" / "data"
    buddhi_dir.mkdir(parents=True, exist_ok=True)
    return buddhi_dir / "metric.db"

def init_metrics_db() -> sqlite3.Connection:
    """Initializes the metrics database and runs the schema if needed."""
    db_path = get_metrics_db_path()
    conn = sqlite3.connect(str(db_path))

    # Run schema
    schema_sql = """
    CREATE TABLE IF NOT EXISTS tool_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_name TEXT NOT NULL,
        timestamp_iso TEXT NOT NULL,
        timestamp_unix REAL NOT NULL,
        input_tokens INTEGER,
        output_tokens INTEGER,
        raw_input_tokens INTEGER,
        tokens_saved INTEGER,
        status TEXT NOT NULL,
        error_message TEXT,
        duration_ms REAL,
        workspace_path TEXT,
        extra_json TEXT
    );

    CREATE INDEX IF NOT EXISTS idx_tool_events_tool ON tool_events(tool_name);
    CREATE INDEX IF NOT EXISTS idx_tool_events_ts ON tool_events(timestamp_unix);
    CREATE INDEX IF NOT EXISTS idx_tool_events_status ON tool_events(status);
    """
    conn.executescript(schema_sql)
    conn.commit()

    return conn
