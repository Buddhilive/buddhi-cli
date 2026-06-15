import sqlite3
import time


def log_read_event(conn: sqlite3.Connection, filepath: str, mode: str):
    """
    Logs a file read event to the history table and runs a TTL cleanup.
    
    Records older than 5 minutes are deleted to prevent unbounded growth.
    """
    timestamp_micro = int(time.time() * 1_000_000)
    
    # 5 minutes TTL in microseconds (300,000,000)
    cutoff = timestamp_micro - 300_000_000
    
    cursor = conn.cursor()
    # TTL Cleanup
    cursor.execute("DELETE FROM file_read_history WHERE timestamp_micro < ?", (cutoff,))
    
    # Log current event
    cursor.execute(
        "INSERT INTO file_read_history (filepath, mode, timestamp_micro) VALUES (?, ?, ?)",
        (filepath, mode, timestamp_micro)
    )
    conn.commit()


def should_trip_circuit_breaker(conn: sqlite3.Connection, filepath: str, threshold: float = 0.30) -> bool:
    """
    Calculates rolling bounce metric over the last 5 minutes for a specific file.
    
    Bounce Rate = (Compressed Reads followed by an Immediate Full Read) / (Total Session File Reads)
    
    Returns True if bounce rate > threshold (e.g. 30%).
    """
    cursor = conn.cursor()
    # We only look at records within the 5-minute TTL window (which are already filtered during insert)
    cursor.execute(
        "SELECT mode FROM file_read_history WHERE filepath = ? ORDER BY timestamp_micro ASC",
        (filepath,)
    )
    rows = cursor.fetchall()
    
    if not rows:
        return False
        
    total_reads = len(rows)
    if total_reads < 2:
        return False # Cannot have a bounce with fewer than 2 reads
        
    bounces = 0
    for i in range(len(rows) - 1):
        current_mode = rows[i][0]
        next_mode = rows[i+1][0]
        
        # A compressed read followed by an immediate full read
        if current_mode != 'full' and next_mode == 'full':
            bounces += 1
            
    bounce_rate = bounces / total_reads
    return bounce_rate > threshold
