"""CodeGraph -> a single interactive HTML visualization (vis-network via CDN).

Ported from the richer vis-network visualizer this project had in an earlier
iteration (glass UI, autocomplete search, node inspector, per-kind legend,
physics toggle, click-to-highlight), rewired onto the current `CodeGraph` model:
nodes carry `kind` (directory/file/class/function/method/external) instead of a
raw tree-sitter node type, and community coloring comes from
`graph.clustering.assign_communities` instead of a SQLite-stored community_id.
"""

from __future__ import annotations

import colorsys
import json
from pathlib import Path

from buddhi.graph.model import (
    CALLS,
    CLASS,
    CONTAINS,
    FUNCTION,
    IMPORTS,
    INHERITS,
    METHOD,
    CodeGraph,
)
from buddhi.persist.atomic import atomic_write_text

VIS_NETWORK_CDN_URL = "https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"

_CLUSTERABLE_KINDS = (CLASS, FUNCTION, METHOD)

_KIND_COLORS = {
    "directory": {"background": "#475569", "border": "#64748b"},
    "file": {"background": "#0369a1", "border": "#38bdf8"},
    "class": {"background": "#0d9488", "border": "#14b8a6"},
    "function": {"background": "#d97706", "border": "#f59e0b"},
    "method": {"background": "#059669", "border": "#10b981"},
    "external": {"background": "#57534e", "border": "#a8a29e"},
}

_KIND_LABELS = [
    ("directory", "Directory"),
    ("file", "File"),
    ("class", "Class"),
    ("function", "Function"),
    ("method", "Method"),
    ("external", "External"),
]

_EDGE_COLORS = {
    CALLS: "#f97316",
    IMPORTS: "#3b82f6",
    INHERITS: "#a855f7",
}


def _community_color(community_id: int) -> dict[str, str]:
    hue = (community_id * 0.618033988749895) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.6, 0.9)
    background = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    return {"background": background, "border": "#f8fafc"}


def _node_color(kind: str, community_id: int | None) -> dict[str, str]:
    if kind in _CLUSTERABLE_KINDS and community_id is not None:
        return _community_color(community_id)
    return _KIND_COLORS.get(kind, {"background": "#3b82f6", "border": "#60a5fa"})


def _build_vis_data(graph: CodeGraph) -> dict:
    nodes = []
    for node in graph.nodes.values():
        color = _node_color(node.kind, node.community_id)
        nodes.append(
            {
                "id": node.id,
                "label": node.name,
                "kind": node.kind,
                "qualified_name": node.qualified_name,
                "file_path": node.file_path,
                "start_line": node.start_line,
                "end_line": node.end_line,
                "snippet": node.snippet,
                "community_id": node.community_id,
                "color": {
                    "background": color["background"],
                    "border": color["border"],
                    "highlight": {"background": color["background"], "border": "#f8fafc"},
                    "hover": {"background": color["background"], "border": "#f8fafc"},
                },
            }
        )

    edges = []
    for edge in graph.edges:
        if edge.kind == CONTAINS:
            continue
        edges.append(
            {
                "from": edge.source,
                "to": edge.target,
                "kind": edge.kind,
                "color": {"color": _EDGE_COLORS.get(edge.kind, "#64748b"), "opacity": 0.5},
            }
        )

    return {"nodes": nodes, "edges": edges}


_LEGEND_ITEM = """
            <label class="flex items-center justify-between cursor-pointer group hover:bg-white/5 p-1 rounded transition-all">
                <div class="flex items-center space-x-2.5">
                    <span class="w-3.5 h-3.5 rounded-full" style="background:{color}"></span>
                    <span class="text-xs text-slate-200 font-medium group-hover:text-white">{label}</span>
                </div>
                <input type="checkbox" data-kind="{kind}" checked class="filter-kind w-4 h-4 rounded text-sky-600 bg-slate-900 border-white/10 focus:ring-sky-500 focus:ring-offset-slate-900 focus:ring-2">
            </label>"""


def _legend_html() -> str:
    return "".join(
        _LEGEND_ITEM.format(color=_KIND_COLORS[kind]["background"], label=label, kind=kind)
        for kind, label in _KIND_LABELS
    )


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Buddhi AI Code Graph — {root_label}</title>
<script src="https://cdn.tailwindcss.com"></script>
<script type="text/javascript" src="{cdn_url}"></script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
    body {{
        font-family: 'Outfit', sans-serif;
        background-color: #0b0f19;
        color: #f1f5f9;
        background-image: radial-gradient(circle at 50% 50%, #1e293b 0%, #0b0f19 100%);
        overflow: hidden;
        height: 100vh;
        width: 100vw;
        margin: 0;
    }}
    .glass {{
        backdrop-filter: blur(16px);
        background: rgba(15, 23, 42, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5);
    }}
    .code-font {{ font-family: 'JetBrains Mono', monospace; }}
    ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
    ::-webkit-scrollbar-track {{ background: rgba(15, 23, 42, 0.3); }}
    ::-webkit-scrollbar-thumb {{ background: rgba(255, 255, 255, 0.1); border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: rgba(255, 255, 255, 0.2); }}
    #network-container {{
        width: 100%; height: calc(100vh - 64px);
        position: absolute; top: 64px; left: 0; background-color: transparent;
    }}
</style>
</head>
<body class="relative flex flex-col">
<header class="h-16 w-full flex items-center justify-between px-6 glass z-30 border-b border-white/5">
    <div class="flex items-center space-x-3">
        <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-sky-500/20">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-2 0c0 .993-.243 1.93-.675 2.751m-1.005-5.002A5.002 5.002 0 0110 5v5h5z" />
            </svg>
        </div>
        <div>
            <h1 class="text-lg font-bold bg-gradient-to-r from-slate-100 to-slate-300 bg-clip-text text-transparent">Buddhi AI Code Graph</h1>
            <p class="text-xs text-slate-400 font-medium" id="stats-indicator">Loading {root_label}...</p>
        </div>
    </div>
    <div class="flex items-center space-x-4">
        <div class="relative w-64">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
            </div>
            <input type="text" id="search-input" placeholder="Search symbol..." class="w-full bg-slate-900/80 border border-white/10 rounded-lg pl-9 pr-3 py-1.5 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:border-sky-500/80 focus:ring-1 focus:ring-sky-500/50 transition-all">
            <div id="search-results" class="absolute left-0 right-0 mt-1 max-h-60 overflow-y-auto glass rounded-lg border border-white/10 hidden z-50"></div>
        </div>
        <button id="physics-btn" class="flex items-center space-x-2 bg-slate-900/60 hover:bg-slate-800 border border-white/10 px-3 py-1.5 rounded-lg text-sm text-slate-200 hover:text-white transition-all">
            <span id="physics-btn-icon"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg></span>
            <span id="physics-indicator" class="text-xs font-semibold">Engine Active</span>
        </button>
    </div>
</header>

<div id="network-container"></div>

<div id="inspector-panel" class="absolute top-20 right-6 w-96 rounded-xl glass border border-white/10 p-5 flex flex-col z-20 transition-all duration-300 max-h-[80vh] overflow-y-auto hidden">
    <div class="flex items-start justify-between border-b border-white/5 pb-3 mb-4">
        <div>
            <span id="inspector-kind" class="text-[10px] tracking-wider uppercase font-bold px-2 py-0.5 rounded border border-white/10 mr-2"></span>
            <h2 id="inspector-name" class="text-base font-bold text-white mt-1.5 break-all"></h2>
        </div>
        <button onclick="hideNodeDetails()" class="text-slate-400 hover:text-white transition-colors">
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
        </button>
    </div>
    <div class="space-y-3.5 text-sm">
        <div>
            <span class="text-xs font-semibold text-slate-400">File Path:</span>
            <p id="inspector-file" class="code-font text-xs text-sky-400 bg-slate-950/40 p-2 rounded border border-white/5 mt-1 select-all break-all"></p>
        </div>
        <div class="flex justify-between text-xs text-slate-300 bg-slate-950/20 p-2.5 rounded border border-white/5">
            <div><span class="font-semibold text-slate-400">Lines:</span> <span id="inspector-lines" class="code-font ml-1"></span></div>
            <div><span class="font-semibold text-slate-400">Community:</span> <span id="inspector-community" class="code-font ml-1"></span></div>
        </div>
        <div>
            <span class="text-xs font-semibold text-slate-400">Source:</span>
            <div id="inspector-snippet" class="code-font text-xs text-slate-300 bg-slate-950/50 p-3 rounded-lg border border-white/5 mt-1 max-h-64 overflow-y-auto whitespace-pre-wrap leading-relaxed"></div>
        </div>
    </div>
</div>

<div class="absolute bottom-6 left-6 p-4 rounded-xl glass border border-white/10 flex flex-col z-20 space-y-3 w-64 shadow-xl">
    <h3 class="text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-white/5 pb-1.5">Interactive Legend</h3>
    <div class="space-y-2">{legend_html}
    </div>
    <p class="text-[10px] text-slate-400 border-t border-white/5 pt-2">
        Click checkboxes to toggle visibility. Click a node to view connections and isolate dependencies.
    </p>
</div>

<script type="text/javascript">
const graphData = {graph_json};

const allNodes = graphData.nodes;
const allEdges = graphData.edges.map((e, i) => ({{ id: i, ...e }}));

const nodesDataSet = new vis.DataSet(allNodes);
const edgesDataSet = new vis.DataSet(allEdges);

const communityCount = new Set(allNodes.map(n => n.community_id).filter(c => c !== null && c !== undefined)).size;
document.getElementById('stats-indicator').innerText =
    `${{allNodes.length}} symbols, ${{allEdges.length}} edges, ${{communityCount}} communities`;

const container = document.getElementById('network-container');
const data = {{ nodes: nodesDataSet, edges: edgesDataSet }};

const options = {{
    nodes: {{
        shape: 'dot', size: 16,
        font: {{ color: '#f8fafc', size: 13, face: 'Outfit', strokeWidth: 2, strokeColor: '#0b0f19' }},
        borderWidth: 2,
    }},
    edges: {{
        arrows: {{ to: {{ enabled: true, scaleFactor: 0.7 }} }},
        color: {{ inherit: false }},
        smooth: {{ type: 'cubicBezier', forceDirection: 'none', roundness: 0.6 }},
    }},
    physics: {{
        solver: 'forceAtlas2Based',
        forceAtlas2Based: {{ gravitationalConstant: -50, centralGravity: 0.01, springLength: 100, springConstant: 0.08, damping: 0.4 }},
        stabilization: {{ enabled: true, iterations: 200, updateInterval: 25 }},
    }},
    interaction: {{ hover: true, tooltipDelay: 300, selectable: true, selectConnectedEdges: true }},
}};

const network = new vis.Network(container, data, options);

let physicsRunning = true;
const playSvg = '<svg class="w-4 h-4 text-emerald-400" fill="currentColor" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';
const pauseSvg = '<svg class="w-4 h-4 text-sky-400" fill="currentColor" viewBox="0 0 24 24"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>';

document.getElementById('physics-btn').addEventListener('click', () => {{
    physicsRunning = !physicsRunning;
    network.setOptions({{ physics: {{ enabled: physicsRunning }} }});
    document.getElementById('physics-indicator').innerText = physicsRunning ? "Engine Active" : "Paused (Frozen)";
    document.getElementById('physics-btn-icon').innerHTML = physicsRunning ? pauseSvg : playSvg;
}});

network.on("stabilizationFinished", function () {{
    network.setOptions({{ physics: {{ enabled: false }} }});
    document.getElementById('physics-indicator').innerText = "Paused (Stabilized)";
    document.getElementById('physics-btn-icon').innerHTML = playSvg;
    physicsRunning = false;
}});

const activeFilters = {{}};
document.querySelectorAll('.filter-kind').forEach(cb => {{ activeFilters[cb.dataset.kind] = true; }});

let activeHighlight = false;
let clickedNode = null;

function applyFilters() {{
    const updated = allNodes.map(node => ({{ ...node, hidden: !activeFilters[node.kind] }}));
    nodesDataSet.update(updated);
}}

document.querySelectorAll('.filter-kind').forEach(cb => {{
    cb.addEventListener('change', (e) => {{
        activeFilters[e.target.dataset.kind] = e.target.checked;
        applyFilters();
    }});
}});

function highlightNode(nodeId) {{
    clickedNode = nodeId;
    activeHighlight = true;
    const connectedNodes = network.getConnectedNodes(clickedNode);

    const updatedNodes = allNodes.map(node => {{
        const isSelf = node.id === clickedNode;
        const isNeighbor = connectedNodes.includes(node.id);
        const opacity = (isSelf || isNeighbor) ? 1.0 : 0.15;
        return {{
            ...node,
            hidden: !activeFilters[node.kind],
            opacity: opacity,
            font: {{ color: (isSelf || isNeighbor) ? '#f8fafc' : 'rgba(248, 250, 252, 0.15)' }},
        }};
    }});
    nodesDataSet.update(updatedNodes);

    const updatedEdges = allEdges.map(edge => {{
        const isConnected = edge.from === clickedNode || edge.to === clickedNode;
        return {{
            ...edge,
            color: isConnected
                ? {{ color: '#38bdf8', opacity: 1.0 }}
                : {{ color: 'rgba(100, 116, 139, 0.08)', opacity: 0.08 }},
        }};
    }});
    edgesDataSet.update(updatedEdges);

    showNodeDetails(clickedNode);
}}

function resetHighlight() {{
    activeHighlight = false;
    clickedNode = null;
    const updatedNodes = allNodes.map(node => ({{
        ...node, hidden: !activeFilters[node.kind], opacity: 1.0, font: {{ color: '#f8fafc' }},
    }}));
    nodesDataSet.update(updatedNodes);
    edgesDataSet.update(allEdges);
    hideNodeDetails();
}}

network.on("click", function (params) {{
    if (params.nodes.length > 0) {{
        highlightNode(params.nodes[0]);
    }} else {{
        resetHighlight();
    }}
}});

function hideNodeDetails() {{
    document.getElementById('inspector-panel').classList.add('hidden');
}}

const kindBadgeClasses = {{
    directory: 'border-slate-500/30 bg-slate-500/10 text-slate-300',
    file: 'border-sky-500/30 bg-sky-500/10 text-sky-300',
    class: 'border-teal-500/30 bg-teal-500/10 text-teal-300',
    function: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    method: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    external: 'border-stone-500/30 bg-stone-500/10 text-stone-300',
}};

function showNodeDetails(nodeId) {{
    const node = allNodes.find(n => n.id === nodeId);
    if (!node) return;

    const badge = document.getElementById('inspector-kind');
    badge.innerText = node.kind;
    badge.className = `text-[10px] tracking-wider uppercase font-bold px-2 py-0.5 rounded border mr-2 ${{kindBadgeClasses[node.kind] || ''}}`;

    document.getElementById('inspector-name').innerText = node.qualified_name || node.label;
    document.getElementById('inspector-file').innerText = node.file_path || "N/A";
    document.getElementById('inspector-lines').innerText =
        (node.start_line && node.end_line) ? `${{node.start_line}} - ${{node.end_line}}` : "N/A";
    document.getElementById('inspector-community').innerText =
        (node.community_id === null || node.community_id === undefined) ? "N/A" : node.community_id;

    const snippetEl = document.getElementById('inspector-snippet');
    snippetEl.innerText = node.snippet || "No source available.";

    document.getElementById('inspector-panel').classList.remove('hidden');
}}

const searchInput = document.getElementById('search-input');
const searchResults = document.getElementById('search-results');

searchInput.addEventListener('input', (e) => {{
    const query = e.target.value.toLowerCase().trim();
    if (!query) {{ searchResults.classList.add('hidden'); return; }}

    const matches = allNodes.filter(node =>
        (node.label || '').toLowerCase().includes(query) ||
        node.id.toLowerCase().includes(query)
    ).slice(0, 8);

    if (matches.length === 0) {{
        searchResults.innerHTML = '<div class="p-2.5 text-xs text-slate-400 italic">No matches found</div>';
    }} else {{
        searchResults.innerHTML = matches.map(node => `
            <div data-node-id="${{encodeURIComponent(node.id)}}" class="search-item p-2.5 hover:bg-white/5 cursor-pointer flex flex-col border-b border-white/5 last:border-0 transition-colors">
                <span class="text-sm font-semibold text-white truncate">${{node.label}}</span>
                <span class="text-[10px] text-slate-400 truncate font-mono">${{node.file_path || "N/A"}}</span>
            </div>
        `).join('');
    }}
    searchResults.classList.remove('hidden');
}});

document.addEventListener('click', (e) => {{
    if (!searchInput.contains(e.target) && !searchResults.contains(e.target)) {{
        searchResults.classList.add('hidden');
    }}
}});

searchResults.addEventListener('click', (e) => {{
    const item = e.target.closest('.search-item');
    if (item) {{
        focusNode(decodeURIComponent(item.dataset.nodeId));
    }}
}});

function focusNode(nodeId) {{
    searchResults.classList.add('hidden');
    searchInput.value = "";
    network.setOptions({{ physics: {{ enabled: true }} }});
    network.focus(nodeId, {{ scale: 1.2, animation: {{ duration: 1000, easingFunction: 'easeInOutQuad' }} }});

    setTimeout(() => {{
        network.selectNodes([nodeId]);
        highlightNode(nodeId);
        if (!physicsRunning) {{
            network.setOptions({{ physics: {{ enabled: false }} }});
        }}
    }}, 1000);
}}
</script>
</body>
</html>
"""


def write_html(graph: CodeGraph, path: Path, *, root_label: str) -> None:
    vis_data = _build_vis_data(graph)
    html = _TEMPLATE.format(
        root_label=root_label,
        cdn_url=VIS_NETWORK_CDN_URL,
        legend_html=_legend_html(),
        graph_json=json.dumps(vis_data, separators=(",", ":")),
    )
    atomic_write_text(path, html)
