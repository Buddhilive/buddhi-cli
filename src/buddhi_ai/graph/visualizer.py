import sqlite3
import json
import colorsys
import os

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Buddhi AI - CodeGraph Visualization</title>
    <!-- Tailwind CSS for modern layout -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- vis-network standalone bundle -->
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <!-- Outfit & JetBrains Mono Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Outfit', sans-serif;
            background-color: #0b0f19;
            color: #f1f5f9;
            background-image: radial-gradient(circle at 50% 50%, #1e293b 0%, #0b0f19 100%);
            overflow: hidden;
            height: 100vh;
            width: 100vw;
        }
        .glass {
            backdrop-filter: blur(16px);
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
        }
        .code-font {
            font-family: 'JetBrains Mono', monospace;
        }
        /* Custom scrollbar for docstrings */
        ::-webkit-scrollbar {
            width: 6px;
            height: 6px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(15, 23, 42, 0.3);
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(255, 255, 255, 0.1);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(255, 255, 255, 0.2);
        }
        #network-container {
            width: 100%;
            height: calc(100vh - 64px);
            position: absolute;
            top: 64px;
            left: 0;
            background-color: transparent;
        }
    </style>
</head>
<body class="relative flex flex-col">
    <!-- Header -->
    <header class="h-16 w-full flex items-center justify-between px-6 glass z-30 border-b border-white/5">
        <div class="flex items-center space-x-3">
            <!-- Icon -->
            <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
                <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-2 0c0 .993-.243 1.93-.675 2.751m-1.005-5.002A5.002 5.002 0 0110 5v5h5z" />
                </svg>
            </div>
            <div>
                <h1 class="text-lg font-bold bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent">Buddhi CodeGraph</h1>
                <p class="text-xs text-slate-400 font-medium" id="stats-indicator">Loading codebase stats...</p>
            </div>
        </div>

        <!-- Toolbar Controls -->
        <div class="flex items-center space-x-4">
            <!-- Autocomplete Search -->
            <div class="relative w-64">
                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <input type="text" id="search-input" placeholder="Search symbol..." class="w-full bg-slate-900/80 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-sky-500/80 focus:ring-1 focus:ring-sky-500/50 transition-all">
                <!-- Autocomplete Dropdown -->
                <div id="search-results" class="absolute left-0 right-0 mt-1 max-h-60 overflow-y-auto glass rounded-lg border border-white/10 hidden z-50"></div>
            </div>

            <!-- Physics Play/Pause Toggle -->
            <button id="physics-btn" class="flex items-center space-x-2 bg-slate-900/60 hover:bg-slate-800 border border-white/10 px-3 py-1.5 rounded-lg text-sm text-slate-200 hover:text-white transition-all">
                <span id="physics-btn-icon">
                    <!-- Pause Icon -->
                    <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
                </span>
                <span id="physics-indicator" class="text-xs font-semibold">Engine Active</span>
            </button>
        </div>
    </header>

    <!-- Network Canvas Container -->
    <div id="network-container"></div>

    <!-- Collapsible Side Inspector Drawer -->
    <div id="inspector-panel" class="absolute top-20 right-6 w-96 rounded-xl glass border border-white/10 p-5 flex flex-col z-20 transition-all duration-300 transform translate-x-0 max-h-[80vh] overflow-y-auto hidden">
        <div class="flex items-start justify-between border-b border-white/5 pb-3 mb-4">
            <div>
                <span id="inspector-type" class="text-[10px] tracking-wider uppercase font-bold px-2 py-0.5 rounded border border-white/10 mr-2">Method</span>
                <h2 id="inspector-name" class="text-base font-bold text-white mt-1.5 break-all">MyClass.my_method</h2>
            </div>
            <button onclick="hideNodeDetails()" class="text-slate-400 hover:text-white transition-colors">
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
            </button>
        </div>

        <!-- Attributes -->
        <div class="space-y-3.5 text-sm">
            <div>
                <span class="text-xs font-semibold text-slate-400">File Path:</span>
                <p id="inspector-file" class="code-font text-xs text-sky-400 bg-slate-950/40 p-2 rounded border border-white/5 mt-1 select-all break-all"></p>
            </div>
            <div class="flex justify-between text-xs text-slate-300 bg-slate-950/20 p-2.5 rounded border border-white/5">
                <div>
                    <span class="font-semibold text-slate-400">Lines:</span>
                    <span id="inspector-lines" class="code-font ml-1">10 - 45</span>
                </div>
                <div>
                    <span class="font-semibold text-slate-400">Community ID:</span>
                    <span id="inspector-community" class="code-font ml-1">3</span>
                </div>
            </div>
            <div>
                <span class="text-xs font-semibold text-slate-400">Description / Docstring:</span>
                <div id="inspector-doc" class="text-xs text-slate-300 bg-slate-950/50 p-3 rounded-lg border border-white/5 mt-1 max-h-48 overflow-y-auto whitespace-pre-wrap leading-relaxed italic">
                    No docstring available.
                </div>
            </div>
        </div>
    </div>

    <!-- Floating Interactive Legend Card (Bottom-Left) -->
    <div class="absolute bottom-6 left-6 p-4 rounded-xl glass border border-white/10 flex flex-col z-20 space-y-3 w-64 shadow-xl">
        <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5 pb-1.5">Interactive Legend</h3>
        
        <!-- Legend Items -->
        <div class="space-y-2">
            <!-- Modules Filter Toggle -->
            <label class="flex items-center justify-between cursor-pointer group hover:bg-white/5 p-1 rounded transition-all">
                <div class="flex items-center space-x-2.5">
                    <span class="w-3.5 h-3.5 rounded-full bg-slate-500 border border-slate-400 shadow-lg shadow-slate-500/30"></span>
                    <span class="text-xs text-slate-200 font-medium group-hover:text-white">Module (File)</span>
                </div>
                <input type="checkbox" id="filter-module" checked class="w-4 h-4 rounded text-sky-600 bg-slate-900 border-white/10 focus:ring-sky-500 focus:ring-offset-slate-900 focus:ring-2">
            </label>

            <!-- Classes Filter Toggle -->
            <label class="flex items-center justify-between cursor-pointer group hover:bg-white/5 p-1 rounded transition-all">
                <div class="flex items-center space-x-2.5">
                    <span class="w-3.5 h-3.5 rounded-full bg-teal-600 border border-teal-400 shadow-lg shadow-teal-500/30"></span>
                    <span class="text-xs text-slate-200 font-medium group-hover:text-white">Class</span>
                </div>
                <input type="checkbox" id="filter-class" checked class="w-4 h-4 rounded text-sky-600 bg-slate-900 border-white/10 focus:ring-sky-500 focus:ring-offset-slate-900 focus:ring-2">
            </label>

            <!-- Functions Filter Toggle -->
            <label class="flex items-center justify-between cursor-pointer group hover:bg-white/5 p-1 rounded transition-all">
                <div class="flex items-center space-x-2.5">
                    <span class="w-3.5 h-3.5 rounded-full bg-amber-600 border border-amber-400 shadow-lg shadow-amber-500/30"></span>
                    <span class="text-xs text-slate-200 font-medium group-hover:text-white">Function</span>
                </div>
                <input type="checkbox" id="filter-function" checked class="w-4 h-4 rounded text-sky-600 bg-slate-900 border-white/10 focus:ring-sky-500 focus:ring-offset-slate-900 focus:ring-2">
            </label>

            <!-- Methods Filter Toggle -->
            <label class="flex items-center justify-between cursor-pointer group hover:bg-white/5 p-1 rounded transition-all">
                <div class="flex items-center space-x-2.5">
                    <span class="w-3.5 h-3.5 rounded-full bg-emerald-600 border border-emerald-400 shadow-lg shadow-emerald-500/30"></span>
                    <span class="text-xs text-slate-200 font-medium group-hover:text-white">Method</span>
                </div>
                <input type="checkbox" id="filter-method" checked class="w-4 h-4 rounded text-sky-600 bg-slate-900 border-white/10 focus:ring-sky-500 focus:ring-offset-slate-900 focus:ring-2">
            </label>
        </div>
        
        <p class="text-[10px] text-slate-400 border-t border-white/5 pt-2">
            💡 Click checkboxes to toggle visibility. Click a node to view connections and isolate dependencies.
        </p>
    </div>

    <!-- Vis.js script logic -->
    <script type="text/javascript">
        // Embed the Raw Graph JSON Data directly here
        const graphData = __EMBEDDED_GRAPH_JSON__;
        
        // Node Type styling config
        const styles = {
            module: { color: '#475569', border: '#64748b', highlight: '#64748b' },
            class: { color: '#0d9488', border: '#14b8a6', highlight: '#14b8a6' },
            function: { color: '#d97706', border: '#f59e0b', highlight: '#f59e0b' },
            method: { color: '#059669', border: '#10b981', highlight: '#10b981' }
        };

        const allNodes = graphData.nodes.map(n => {
            const style = styles[n.type] || { color: '#3b82f6', border: '#60a5fa', highlight: '#60a5fa' };
            return {
                id: n.id,
                label: n.label,
                type: n.type,
                file_path: n.file_path,
                start_line: n.start_line,
                end_line: n.end_line,
                docstring: n.docstring || "",
                community_id: n.community_id || 0,
                color: {
                    background: style.color,
                    border: style.border,
                    highlight: {
                        background: style.highlight,
                        border: '#f8fafc'
                    },
                    hover: {
                        background: style.highlight,
                        border: '#f8fafc'
                    }
                }
            };
        });

        const allEdges = graphData.edges.map(e => ({
            from: e.from,
            to: e.to,
            type: e.title,
            color: { color: 'rgba(71, 85, 105, 0.4)', opacity: 0.4 }
        }));

        // Initialize Vis DataSets
        const nodesDataSet = new vis.DataSet(allNodes);
        const edgesDataSet = new vis.DataSet(allEdges);

        // Stats
        document.getElementById('stats-indicator').innerText = `Indexed: ${allNodes.length} symbols, ${allEdges.length} call edges`;

        // Canvas container
        const container = document.getElementById('network-container');
        const data = {
            nodes: nodesDataSet,
            edges: edgesDataSet
        };

        // Network UI config
        const options = {
            nodes: {
                shape: 'dot',
                size: 16,
                font: {
                    color: '#f8fafc',
                    size: 13,
                    face: 'Outfit',
                    strokeWidth: 2,
                    strokeColor: '#0b0f19'
                },
                borderWidth: 2
            },
            edges: {
                arrows: {
                    to: { enabled: true, scaleFactor: 0.7 }
                },
                color: {
                    inherit: false
                },
                smooth: {
                    type: 'cubicBezier',
                    forceDirection: 'none',
                    roundness: 0.6
                }
            },
            physics: {
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                    damping: 0.4
                },
                stabilization: {
                    enabled: true,
                    iterations: 200,
                    updateInterval: 25
                }
            },
            interaction: {
                hover: true,
                tooltipDelay: 300,
                selectable: true,
                selectConnectedEdges: true
            }
        };

        // Render network graph
        const network = new vis.Network(container, data, options);

        // Physics play/pause toggle controls
        let physicsRunning = true;
        const playSvg = '<svg class="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
        const pauseSvg = '<svg class="w-4 h-4 text-sky-400" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';

        document.getElementById('physics-btn').addEventListener('click', () => {
            physicsRunning = !physicsRunning;
            network.setOptions({ physics: { enabled: physicsRunning } });
            
            if (physicsRunning) {
                document.getElementById('physics-indicator').innerText = "Engine Active";
                document.getElementById('physics-btn-icon').innerHTML = pauseSvg;
            } else {
                document.getElementById('physics-indicator').innerText = "Paused (Frozen)";
                document.getElementById('physics-btn-icon').innerHTML = playSvg;
            }
        });

        // Auto freeze physics when settled (prevents lag and floating nodes on hover)
        network.on("stabilizationFinished", function () {
            network.setOptions({ physics: { enabled: false } });
            document.getElementById('physics-indicator').innerText = "Paused (Stabilized)";
            document.getElementById('physics-btn-icon').innerHTML = playSvg;
            physicsRunning = false;
        });

        // Filter Visibility logic
        const activeFilters = {
            module: true,
            class: true,
            function: true,
            method: true
        };

        function applyFilters() {
            const filteredNodes = allNodes.map(node => {
                const isTypeVisible = activeFilters[node.type];
                let opacity = 1.0;
                
                if (activeHighlight && clickedNode) {
                    const connectedNodes = network.getConnectedNodes(clickedNode);
                    const isSelf = node.id === clickedNode;
                    const isNeighbor = connectedNodes.includes(node.id);
                    opacity = (isSelf || isNeighbor) ? 1.0 : 0.2;
                }
                
                return {
                    ...node,
                    hidden: !isTypeVisible,
                    opacity: opacity
                };
            });
            nodesDataSet.update(filteredNodes);
        }

        ['module', 'class', 'function', 'method'].forEach(type => {
            document.getElementById(`filter-${type}`).addEventListener('change', (e) => {
                activeFilters[type] = e.target.checked;
                applyFilters();
            });
        });

        // Interactivity details showing
        let activeHighlight = false;
        let clickedNode = null;

        function highlightNode(nodeId) {
            clickedNode = nodeId;
            activeHighlight = true;
            
            // Find immediate connected nodes
            const connectedNodes = network.getConnectedNodes(clickedNode);
            
            // Dim everything except active and neighbors
            const updatedNodes = allNodes.map(node => {
                const isSelf = node.id === clickedNode;
                const isNeighbor = connectedNodes.includes(node.id);
                const opacity = (isSelf || isNeighbor) ? 1.0 : 0.2;
                const isTypeVisible = activeFilters[node.type];
                
                return {
                    ...node,
                    opacity: opacity,
                    hidden: !isTypeVisible,
                    font: {
                        ...node.font,
                        color: (isSelf || isNeighbor) ? '#f8fafc' : 'rgba(248, 250, 252, 0.2)'
                    }
                };
            });
            nodesDataSet.update(updatedNodes);

            // Dim non-connected edges
            const updatedEdges = allEdges.map(edge => {
                const isConnected = edge.from === clickedNode || edge.to === clickedNode;
                return {
                    ...edge,
                    color: isConnected ? { color: '#38bdf8', opacity: 1.0 } : { color: 'rgba(71, 85, 105, 0.1)', opacity: 0.1 }
                };
            });
            edgesDataSet.update(updatedEdges);

            showNodeDetails(clickedNode);
        }

        network.on("click", function(params) {
            if (params.nodes.length > 0) {
                highlightNode(params.nodes[0]);
            } else {
                resetHighlight();
            }
        });

        function resetHighlight() {
            activeHighlight = false;
            clickedNode = null;
            
            const updatedNodes = allNodes.map(node => {
                const isTypeVisible = activeFilters[node.type];
                return {
                    ...node,
                    opacity: 1.0,
                    hidden: !isTypeVisible,
                    font: {
                        ...node.font,
                        color: '#f8fafc'
                    }
                };
            });
            nodesDataSet.update(updatedNodes);

            const updatedEdges = allEdges.map(edge => ({
                ...edge,
                color: { color: 'rgba(71, 85, 105, 0.4)', opacity: 0.4 }
            }));
            edgesDataSet.update(updatedEdges);

            hideNodeDetails();
        }

        // Hide metadata Details Inspector panel
        function hideNodeDetails() {
            document.getElementById('inspector-panel').classList.add('hidden');
        }

        // Show metadata Details Inspector panel
        function showNodeDetails(nodeId) {
            const node = allNodes.find(n => n.id === nodeId);
            if (!node) return;

            document.getElementById('inspector-type').innerText = node.type;
            
            // Set type border/background color in panel
            const colors = {
                module: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
                class: 'border-teal-500/30 bg-teal-500/10 text-teal-300',
                function: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
                method: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
            };
            document.getElementById('inspector-type').className = `text-[10px] tracking-wider uppercase font-bold px-2 py-0.5 rounded border mr-2 ${colors[node.type] || ''}`;
            
            document.getElementById('inspector-name').innerText = node.label;
            document.getElementById('inspector-file').innerText = node.file_path || "N/A";
            document.getElementById('inspector-lines').innerText = (node.start_line && node.end_line) ? `${node.start_line} - ${node.end_line}` : "N/A";
            document.getElementById('inspector-community').innerText = node.community_id;
            
            const docElement = document.getElementById('inspector-doc');
            if (node.docstring) {
                docElement.innerText = node.docstring;
                docElement.classList.remove('italic', 'text-slate-400');
                docElement.classList.add('text-slate-200');
            } else {
                docElement.innerText = "No docstring available.";
                docElement.classList.add('italic', 'text-slate-400');
                docElement.classList.remove('text-slate-200');
            }

            document.getElementById('inspector-panel').classList.remove('hidden');
        }

        // Autocomplete Search features
        const searchInput = document.getElementById('search-input');
        const searchResults = document.getElementById('search-results');

        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            if (!query) {
                searchResults.classList.add('hidden');
                return;
            }

            const matches = allNodes.filter(node => 
                node.label.toLowerCase().includes(query) || 
                node.id.toLowerCase().includes(query)
            ).slice(0, 8); // Max 8 autocomplete elements

            if (matches.length === 0) {
                searchResults.innerHTML = '<div class="p-2.5 text-xs text-slate-400 italic">No matches found</div>';
            } else {
                searchResults.innerHTML = matches.map(node => `
                    <div data-node-id="${encodeURIComponent(node.id)}" class="search-item p-2.5 hover:bg-white/5 cursor-pointer flex flex-col border-b border-white/5 last:border-0 transition-colors">
                        <span class="text-sm font-semibold text-white truncate">${node.label}</span>
                        <span class="text-[10px] text-slate-400 truncate font-mono">${node.file_path || "N/A"}</span>
                    </div>
                `).join('');
            }
            searchResults.classList.remove('hidden');
        });

        // Close search results when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {
                searchResults.classList.add('hidden');
            }
        });

        // Add Event Delegation Listener for safe decoded navigation
        searchResults.addEventListener('click', (e) => {
            const item = e.target.closest('.search-item');
            if (item) {
                const nodeId = decodeURIComponent(item.dataset.nodeId);
                focusNode(nodeId);
            }
        });

        function focusNode(nodeId) {
            searchResults.classList.add('hidden');
            searchInput.value = "";
            
            // Enable physics briefly for animation if frozen
            network.setOptions({ physics: { enabled: true } });
            
            network.focus(nodeId, {
                scale: 1.2,
                animation: {
                    duration: 1000,
                    easingFunction: 'easeInOutQuad'
                }
            });

            setTimeout(() => {
                network.selectNodes([nodeId]);
                // Highlight the selected node and its connections
                highlightNode(nodeId);
                
                // Freeze again if physics was manually turned off
                if (!physicsRunning) {
                    network.setOptions({ physics: { enabled: false } });
                }
            }, 1000);
        }
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

    # Query with JOIN on files table to get metadata
    cur.execute('''
        SELECT n.id, n.name, n.node_type, n.community_id, 
               n.start_line, n.end_line, n.content, f.path 
        FROM nodes n 
        LEFT JOIN files f ON n.file_id = f.id
    ''')
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
    for node_id, name, node_type, community_id, start_line, end_line, content, file_path in db_nodes:
        # Fallback color for unclustered nodes
        color = community_colors.get(community_id, "#888888")
        label = name if name else str(node_type)
        title = f"Name: {label}<br>Type: {node_type}<br>Community: {community_id}"
        
        # Normalize node_type for UI styling (e.g. class_definition -> class)
        normalized_type = node_type
        if node_type and "class" in node_type:
            normalized_type = "class"
        elif node_type and "function" in node_type:
            normalized_type = "function"
        elif node_type and "method" in node_type:
            normalized_type = "method"
        elif node_type and "module" in node_type:
            normalized_type = "module"
        
        vis_nodes.append({
            "id": node_id,
            "label": label,
            "type": normalized_type,
            "file_path": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "docstring": content,
            "community_id": community_id,
            "color": {
                "background": color,
                "border": "#ffffff"
            }
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
    graph_json = json.dumps({
        "nodes": vis_nodes,
        "edges": vis_edges
    })

    # Embed into HTML
    html_content = HTML_TEMPLATE.replace("__EMBEDDED_GRAPH_JSON__", graph_json)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"Graph visualization saved to {output_path}")
