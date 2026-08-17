"""CodeGraph -> a single interactive HTML visualization (Cytoscape.js via CDN)."""

from __future__ import annotations

import json
from pathlib import Path

from buddhi.graph.model import CodeGraph
from buddhi.persist.atomic import atomic_write_text
from buddhi.persist.json_writer import to_cytoscape_elements

CYTOSCAPE_CDN_URL = "https://unpkg.com/cytoscape@3.30.2/dist/cytoscape.min.js"

_KIND_COLORS = {
    "directory": "#6b7280",
    "file": "#3b82f6",
    "class": "#f59e0b",
    "function": "#10b981",
    "method": "#22c55e",
    "external": "#9ca3af",
}

_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>buddhi code graph — {root_label}</title>
<script src="{cdn_url}"></script>
<style>
  html, body {{ margin: 0; height: 100%; font-family: -apple-system, Segoe UI, sans-serif; }}
  #graph {{ position: absolute; top: 48px; left: 0; right: 0; bottom: 0; }}
  #toolbar {{
    height: 48px; display: flex; align-items: center; gap: 12px;
    padding: 0 12px; background: #111827; color: #f9fafb; box-sizing: border-box;
  }}
  #toolbar label {{ font-size: 13px; display: flex; align-items: center; gap: 4px; }}
  #toolbar select, #toolbar input {{ font-size: 13px; }}
  #stats {{ margin-left: auto; font-size: 12px; color: #9ca3af; }}
</style>
</head>
<body>
<div id="toolbar">
  <strong>buddhi</strong>
  <label>Filter kind:
    <select id="kindFilter">
      <option value="">all</option>
      <option value="class">class</option>
      <option value="function">function</option>
      <option value="method">method</option>
      <option value="file">file</option>
      <option value="external">external</option>
    </select>
  </label>
  <label>Search: <input id="search" placeholder="symbol name"></label>
  <span id="stats"></span>
</div>
<div id="graph"></div>
<script>
const GRAPH_DATA = {graph_json};
const KIND_COLORS = {kind_colors_json};

const cy = cytoscape({{
  container: document.getElementById('graph'),
  elements: GRAPH_DATA,
  style: [
    {{ selector: 'node', style: {{
        'label': 'data(label)', 'font-size': 9, 'color': '#111827',
        'background-color': ele => KIND_COLORS[ele.data('kind')] || '#94a3b8',
        'width': 18, 'height': 18, 'text-valign': 'bottom', 'text-margin-y': 2,
    }} }},
    {{ selector: ':parent', style: {{
        'background-opacity': 0.08, 'border-width': 1, 'border-color': '#94a3b8',
        'label': 'data(label)', 'font-size': 10, 'text-valign': 'top',
    }} }},
    {{ selector: 'edge', style: {{
        'width': 1, 'line-color': '#cbd5e1', 'target-arrow-color': '#cbd5e1',
        'target-arrow-shape': 'triangle', 'curve-style': 'bezier', 'opacity': 0.6,
    }} }},
    {{ selector: 'edge[kind = "calls"]', style: {{ 'line-color': '#f97316', 'target-arrow-color': '#f97316' }} }},
    {{ selector: 'edge[kind = "imports"]', style: {{ 'line-color': '#3b82f6', 'target-arrow-color': '#3b82f6' }} }},
    {{ selector: 'edge[kind = "contains"]', style: {{ 'display': 'none' }} }},
    {{ selector: '.highlighted', style: {{ 'background-color': '#ef4444', 'line-color': '#ef4444',
        'target-arrow-color': '#ef4444', 'z-index': 999 }} }},
  ],
  layout: {{ name: 'cose', animate: false, padding: 30 }},
}});

document.getElementById('stats').textContent =
  `${{GRAPH_DATA.nodes.length}} nodes, ${{GRAPH_DATA.edges.length}} edges`;

document.getElementById('kindFilter').addEventListener('change', (e) => {{
  const kind = e.target.value;
  if (!kind) {{ cy.elements().style('display', 'element'); return; }}
  cy.nodes().forEach(n => {{
    const show = n.data('kind') === kind || n.isParent();
    n.style('display', show ? 'element' : 'none');
  }});
  cy.edges().style('display', 'element');
}});

document.getElementById('search').addEventListener('input', (e) => {{
  const q = e.target.value.trim().toLowerCase();
  cy.elements().removeClass('highlighted');
  if (!q) return;
  cy.nodes().filter(n => (n.data('label') || '').toLowerCase().includes(q))
    .addClass('highlighted').closedNeighborhood().addClass('highlighted');
}});

cy.on('tap', 'node', (evt) => {{
  cy.elements().removeClass('highlighted');
  evt.target.closedNeighborhood().addClass('highlighted');
}});
</script>
</body>
</html>
"""


def write_html(graph: CodeGraph, path: Path, *, root_label: str) -> None:
    elements = to_cytoscape_elements(graph)
    html = _TEMPLATE.format(
        root_label=root_label,
        cdn_url=CYTOSCAPE_CDN_URL,
        graph_json=json.dumps(elements, separators=(",", ":")),
        kind_colors_json=json.dumps(_KIND_COLORS),
    )
    atomic_write_text(path, html)
