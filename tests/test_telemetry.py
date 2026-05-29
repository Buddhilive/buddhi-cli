import sqlite3
import pytest
from buddhi_ai.mcp.compression.telemetry import log_read_event, should_trip_circuit_breaker


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.execute('''
        CREATE TABLE IF NOT EXISTS file_read_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT NOT NULL,
            mode TEXT NOT NULL,
            timestamp_micro INTEGER NOT NULL
        )
    ''')
    yield connection
    connection.close()


def test_circuit_breaker_trips(conn):
    # Log 4 events: map -> full -> signatures -> full
    log_read_event(conn, "test.py", "map")
    log_read_event(conn, "test.py", "full")
    log_read_event(conn, "test.py", "signatures")
    log_read_event(conn, "test.py", "full")
    
    # 4 reads, 2 bounces (map->full, signatures->full)
    # rate = 2 / 4 = 50%
    assert should_trip_circuit_breaker(conn, "test.py", 0.30)


def test_circuit_breaker_does_not_trip(conn):
    log_read_event(conn, "test.py", "full")
    log_read_event(conn, "test.py", "full")
    log_read_event(conn, "test.py", "full")
    
    # 3 reads, 0 bounces (full->full doesn't count)
    assert not should_trip_circuit_breaker(conn, "test.py", 0.30)
    
    
def test_ttl_cleanup(conn, monkeypatch):
    import time
    
    # Mock time to a specific point (1000 seconds)
    monkeypatch.setattr(time, "time", lambda: 1000)
    
    # Add an event that would be considered old
    log_read_event(conn, "test.py", "map")
    
    # Advance time by 6 minutes (360 seconds)
    monkeypatch.setattr(time, "time", lambda: 1360)
    
    # Log a new event - this should trigger the cleanup of the first event
    log_read_event(conn, "test.py", "full")
    
    cursor = conn.cursor()
    cursor.execute("SELECT mode FROM file_read_history ORDER BY timestamp_micro ASC")
    rows = cursor.fetchall()
    
    # Should only contain the new event
    assert len(rows) == 1
    assert rows[0][0] == "full"
