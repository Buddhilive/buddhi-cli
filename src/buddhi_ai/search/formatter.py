"""
U-Curve attention layout, delimiter serialization, and content mode extraction.

Implements the "Lost-in-the-Middle" positional optimization by placing
high-salience items at the top/bottom and low-salience items in the middle.
"""
from dataclasses import dataclass
from typing import List

from buddhi_ai.parser.entropy import calculate_entropy


# Salience tier ordering (lower = higher priority)
_TIER_PRIORITY = {"anchor": 0, "community": 1, "bridge": 2}

# Shannon entropy threshold for line-level filtering
_ENTROPY_THRESHOLD = 3.0


@dataclass
class SearchResult:
    """A single node in the search result set."""
    node_id: int
    name: str
    file_path: str
    content: str
    start_line: int
    end_line: int
    community_id: int
    salience_tier: str       # "anchor" | "community" | "bridge"
    node_type: str
    edge_weight_sum: float = 0.0  # sum of incident edge weights (for Tier 3 ranking)
    mode: str = "full"       # current rendering mode for this node


def extract_signature(content: str, node_type: str) -> str:
    """Extract only the signature from a function or class definition.

    Strips the body while preserving the declaration line(s),
    parameters, return type annotations, and docstrings.
    """
    if not content:
        return content

    lines = content.split("\n")

    # For function-like nodes: find the end of the signature (the line with ':')
    # and optionally include the docstring
    nt = node_type.lower()
    if "function" in nt or "method" in nt:
        sig_lines: List[str] = []
        found_colon = False
        for line in lines:
            sig_lines.append(line)
            if not found_colon and line.rstrip().endswith(":"):
                found_colon = True
                # Check for docstring immediately after
                continue
            if found_colon:
                stripped = line.strip()
                # Include docstring lines
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    sig_lines.append(line)
                    # If single-line docstring, stop
                    if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                        break
                    # Multi-line: consume until closing
                    for remaining in lines[len(sig_lines):]:
                        sig_lines.append(remaining)
                        if '"""' in remaining or "'''" in remaining:
                            break
                break

        if sig_lines:
            return "\n".join(sig_lines)

    # For class-like nodes: keep the class line + docstring
    if "class" in nt:
        sig_lines = []
        found_colon = False
        for line in lines:
            sig_lines.append(line)
            if not found_colon and line.rstrip().endswith(":"):
                found_colon = True
                continue
            if found_colon:
                stripped = line.strip()
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    sig_lines.append(line)
                    if stripped.count('"""') >= 2 or stripped.count("'''") >= 2:
                        break
                    for remaining in lines[len(sig_lines):]:
                        sig_lines.append(remaining)
                        if '"""' in remaining or "'''" in remaining:
                            break
                break

        if sig_lines:
            return "\n".join(sig_lines)

    # Fallback: return first line only
    return lines[0] if lines else content


def extract_map_entry(result: SearchResult) -> str:
    """Return a compact one-liner for map mode."""
    return f"{result.name} ({result.node_type}) — {result.file_path}:L{result.start_line}-L{result.end_line}"


def filter_low_entropy_lines(content: str, threshold: float = _ENTROPY_THRESHOLD) -> str:
    """Remove lines with Shannon entropy below the threshold.

    Drops boilerplate lines (debug logs, comment banners, padding arrays)
    while preserving information-dense code.
    """
    if not content:
        return content

    lines = content.split("\n")
    filtered: List[str] = []

    for line in lines:
        stripped = line.strip()
        # Always keep blank lines (structural separators) and short lines
        if not stripped or len(stripped) < 10:
            filtered.append(line)
            continue

        entropy = calculate_entropy(stripped)
        if entropy >= threshold:
            filtered.append(line)

    return "\n".join(filtered)


def render_content(result: SearchResult) -> str:
    """Render node content according to its current mode."""
    if result.mode == "map":
        return extract_map_entry(result)

    if result.mode == "signatures":
        content = extract_signature(result.content, result.node_type)
    else:
        content = result.content

    # Apply entropy filtering for full and signatures modes
    return filter_low_entropy_lines(content)


def u_curve_sort(nodes: List[SearchResult]) -> List[SearchResult]:
    """Reorder nodes using U-Curve positional optimization.

    Places high-salience items at the top and bottom of the list,
    with low-salience items in the middle "dead zone" to exploit
    the LLM "Lost-in-the-Middle" attention pattern.

    Layout:
        Top:    anchor nodes (highest salience)
        Middle: bridge nodes (lowest salience — attention dead zone)
        Bottom: community structural boundaries
    """
    if not nodes:
        return nodes

    # Sort by salience tier priority
    anchors = [n for n in nodes if n.salience_tier == "anchor"]
    community = [n for n in nodes if n.salience_tier == "community"]
    bridges = [n for n in nodes if n.salience_tier == "bridge"]

    # U-Curve: top = anchors, middle = bridges, bottom = community
    return anchors + bridges + community


def serialize_context(nodes: List[SearchResult]) -> str:
    """Serialize search results into delimited text with boundary markers.

    Output format:
        --- START SYMBOL: path/to/file::func_name (L10-L45) ---
        <rendered content>
        --- END SYMBOL ---
    """
    if not nodes:
        return ""

    blocks: List[str] = []

    for result in nodes:
        header = f"--- START SYMBOL: {result.file_path}::{result.name} (L{result.start_line}-L{result.end_line}) ---"
        content = render_content(result)
        footer = "--- END SYMBOL ---"
        blocks.append(f"{header}\n{content}\n{footer}")

    return "\n\n".join(blocks)
