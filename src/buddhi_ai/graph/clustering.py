"""
Leiden algorithm execution.
"""
import igraph as ig  # type: ignore
from typing import Dict

def run_leiden(g: ig.Graph, ig_id_to_db_id: Dict[int, int]) -> Dict[int, int]:
    """
    Run Leiden algorithm on the given graph to optimize modularity.
    
    Returns:
        A dictionary mapping DB node ID to community ID.
    """
    if g.vcount() == 0:
        return {}
        
    weights = g.es["weight"] if "weight" in g.edge_attributes() else None
    
    # Run the Leiden algorithm to maximize modularity
    partition = g.community_leiden(
        objective_function="modularity",
        weights=weights
    )
    
    # Extract community assignments
    community_mapping = {}
    for ig_id, comm_id in enumerate(partition.membership):
        db_id = ig_id_to_db_id[ig_id]
        community_mapping[db_id] = comm_id
        
    return community_mapping
