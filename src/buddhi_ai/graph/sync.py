"""
Database synchronization for graph clustering.
"""
import sqlite3
from typing import Dict

def update_communities(db_path: str, community_mapping: Dict[int, int]) -> None:
    """
    Update the nodes table with the assigned community IDs.
    """
    if not community_mapping:
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Batch update
    update_data = [(comm_id, db_id) for db_id, comm_id in community_mapping.items()]
    
    cursor.executemany(
        "UPDATE nodes SET community_id = ? WHERE id = ?",
        update_data
    )
    
    conn.commit()
    conn.close()
