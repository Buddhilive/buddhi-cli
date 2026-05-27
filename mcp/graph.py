import networkx as nx

class CodeGraphAnalyzer:
    """Uses NetworkX to build a directed graph of symbols and edges,

    and runs community detection to find tightly knit components.
    """

    def __init__(self):
        pass

    def compute_communities(self, nodes, edges):
        """Loads edges into a NetworkX graph, computes communities,

        and returns a dictionary mapping node_id to community_id (1-indexed).
        """
        # If there are no nodes, return empty mapping
        if not nodes:
            return {}

        G = nx.DiGraph()

        # Add all nodes first
        for node in nodes:
            G.add_node(node["id"])

        # Add edges
        for edge in edges:
            G.add_edge(edge["source"], edge["target"], type=edge.get("type", "calls"))

        # Compute communities
        # Louvain community detection requires an undirected graph
        undirected_G = G.to_undirected()

        community_mappings = {}
        
        try:
            # Check if there are edges to cluster
            if undirected_G.number_of_edges() > 0:
                # Use networkx's built-in Louvain algorithm
                communities = nx.community.louvain_communities(undirected_G, seed=42)
                # Sort communities by size, descending, to give smaller IDs to larger clusters
                sorted_communities = sorted(communities, key=len, reverse=True)
                
                for idx, community in enumerate(sorted_communities, start=1):
                    for node_id in community:
                        community_mappings[node_id] = idx
            else:
                # Fallback: each connected component is a community
                components = list(nx.connected_components(undirected_G))
                for idx, component in enumerate(components, start=1):
                    for node_id in component:
                        community_mappings[node_id] = idx
        except Exception:
            # Safe absolute fallback: assign all nodes to community 1
            for node in nodes:
                community_mappings[node["id"]] = 1

        # Fill in any missing nodes (nodes that were not in edges or components somehow)
        for node in nodes:
            if node["id"] not in community_mappings:
                community_mappings[node["id"]] = 1

        return community_mappings
