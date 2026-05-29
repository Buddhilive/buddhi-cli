import sqlite3
import json
import colorsys
import os

HTML_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <title>Buddhi Code Graph</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body { margin: 0; padding: 0; overflow: hidden; font-family: sans-serif; background-color: #1e1e1e; color: #f0f0f0; }
        #mynetwork {
            width: 100vw;
            height: 100vh;
        }
        #searchBox {
            position: absolute;
            top: 20px;
            left: 20px;
            z-index: 10;
            background: rgba(45, 45, 45, 0.9);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            border: 1px solid #444;
            display: flex;
            gap: 10px;
        }
        input {
            padding: 8px 12px;
            border: 1px solid #555;
            border-radius: 4px;
            background: #333;
            color: #fff;
            outline: none;
        }
        button {
            padding: 8px 16px;
            background: #007acc;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover { background: #0098ff; }
    </style>
</head>
<body>
    <div id="searchBox">
        <input type="text" id="searchInput" placeholder="Search node name..." />
        <button onclick="searchNode()">Search</button>
    </div>
    <div id="mynetwork"></div>
    <script type="text/javascript">
        var nodesData = __NODES_JSON__;
        var edgesData = __EDGES_JSON__;

        var nodes = new vis.DataSet(nodesData);
        var edges = new vis.DataSet(edgesData);

        var container = document.getElementById('mynetwork');
        var data = {
            nodes: nodes,
            edges: edges
        };
        var options = {
            nodes: {
                shape: 'dot',
                size: 10,
                font: {
                    size: 14,
                    color: '#ffffff'
                },
                borderWidth: 2,
                shadow: true
            },
            edges: {
                scaling: {
                    min: 1,
                    max: 5
                },
                color: { color: 'rgba(255,255,255,0.2)', highlight: 'rgba(255,255,255,0.8)' },
                smooth: { type: 'continuous' }
            },
            physics: {
                forceAtlas2Based: {
                    gravitationalConstant: -100,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08
                },
                maxVelocity: 50,
                solver: 'forceAtlas2Based',
                timestep: 0.35,
                stabilization: { iterations: 150 }
            },
            interaction: {
                hover: true,
                tooltipDelay: 200
            }
        };
        var network = new vis.Network(container, data, options);

        // Interactive Gating & Linguistic Search
        function searchNode() {
            var query = document.getElementById("searchInput").value.toLowerCase();
            
            var updates = [];
            if (!query) {
                // Reset all nodes
                nodesData.forEach(function(n) {
                    updates.push({
                        id: n.id,
                        opacity: 1.0,
                        borderWidth: 2,
                        size: 10
                    });
                });
                nodes.update(updates);
                return;
            }
            
            var matchedNodeId = null;
            nodesData.forEach(function(n) {
                if (n.label && n.label.toLowerCase().includes(query)) {
                    updates.push({
                        id: n.id,
                        opacity: 1.0,
                        borderWidth: 4,
                        size: 20
                    });
                    if (!matchedNodeId) {
                        matchedNodeId = n.id;
                    }
                } else {
                    updates.push({
                        id: n.id,
                        opacity: 0.1,
                        borderWidth: 2,
                        size: 10
                    });
                }
            });
            
            nodes.update(updates);
            
            if (matchedNodeId) {
                network.focus(matchedNodeId, {
                    scale: 1.2,
                    animation: {
                        duration: 1000,
                        easingFunction: 'easeInOutQuad'
                    }
                });
            }
        }
        
        // Add enter key listener for search
        document.getElementById("searchInput").addEventListener("keypress", function(event) {
            if (event.key === "Enter") {
                event.preventDefault();
                searchNode();
            }
        });
    </script>
</body>
</html>
"""

def generate_graph_html(db_path: str, output_path: str):
    """
    Reads nodes and edges from the SQLite database, assigns distinct hex colors
    based on community_id, serializes the data to JSON, and writes it to an HTML file.
    """
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("SELECT id, name, node_type, community_id FROM nodes")
    db_nodes = cur.fetchall()

    cur.execute("SELECT source_id, target_id, relationship_type, weight FROM edges")
    db_edges = cur.fetchall()

    conn.close()

    # Determine unique community IDs for color generation
    communities = {row[3] for row in db_nodes if row[3] is not None}
    
    # Generate distinct colors for each community using golden ratio
    community_colors = {}
    for i, c_id in enumerate(sorted(list(communities))):
        hue = (i * 0.618033988749895) % 1.0
        # Convert HSV to RGB, use pastel-ish high visibility colors
        r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.9)
        hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        community_colors[c_id] = hex_color

    vis_nodes = []
    for node_id, name, node_type, community_id in db_nodes:
        # Fallback color for unclustered nodes
        color = community_colors.get(community_id, "#888888")
        label = name if name else str(node_type)
        title = f"Name: {label}<br>Type: {node_type}<br>Community: {community_id}"
        
        vis_nodes.append({
            "id": node_id,
            "label": label,
            "title": title,
            "color": {
                "background": color,
                "border": "#ffffff"
            },
            "community_id": community_id
        })

    vis_edges = []
    for source_id, target_id, rel_type, weight in db_edges:
        vis_edges.append({
            "from": source_id,
            "to": target_id,
            "title": rel_type,
            "value": weight
        })

    # Serialize to JSON
    nodes_json = json.dumps(vis_nodes)
    edges_json = json.dumps(vis_edges)

    # Embed into HTML
    html_content = HTML_TEMPLATE.replace("__NODES_JSON__", nodes_json).replace("__EDGES_JSON__", edges_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Graph visualization saved to {output_path}")

