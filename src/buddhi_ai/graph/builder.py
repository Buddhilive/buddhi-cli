"""
Graph construction and loading from SQLite.
"""
import sqlite3
import igraph as ig  # type: ignore
from typing import Tuple, Dict
from buddhi_ai.graph.weights import get_weight

def load_graph(db_path: str) -> Tuple[ig.Graph, Dict[int, int]]:
    """
    Load nodes and edges from SQLite into an igraph.Graph.
    
    Returns:
        A tuple of (graph, ig_id_to_db_id)
        where ig_id_to_db_id maps from igraph vertex index to DB node ID.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Load nodes
    cursor.execute("SELECT id FROM nodes")
    db_nodes = cursor.fetchall()
    
    g = ig.Graph(directed=True)
    g.add_vertices(len(db_nodes))
    
    # igraph vertices are 0-indexed contiguous integers.
    # We need to map DB node IDs to igraph vertex IDs and vice-versa.
    db_id_to_ig_id = {}
    ig_id_to_db_id = {}
    
    for i, row in enumerate(db_nodes):
        db_id = row['id']
        db_id_to_ig_id[db_id] = i
        ig_id_to_db_id[i] = db_id
        g.vs[i]["db_id"] = db_id
        
    # Load edges
    cursor.execute("SELECT source_id, target_id, relationship_type FROM edges")
    db_edges = cursor.fetchall()
    
    edges_list = []
    weights_list = []
    
    for row in db_edges:
        source_id = row['source_id']
        target_id = row['target_id']
        rel_type = row['relationship_type']
        
        if source_id in db_id_to_ig_id and target_id in db_id_to_ig_id:
            u = db_id_to_ig_id[source_id]
            v = db_id_to_ig_id[target_id]
            edges_list.append((u, v))
            weights_list.append(get_weight(rel_type))
            
    g.add_edges(edges_list)
    g.es["weight"] = weights_list
    
    conn.close()
    
    return g, ig_id_to_db_id
