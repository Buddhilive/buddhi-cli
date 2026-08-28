from __future__ import annotations

import logging
from pathlib import Path
import tree_sitter as ts

from buddhi.discovery.walker import EXTENSION_TO_LANGUAGE
from buddhi.languages.registry import get_spec

PLACEHOLDERS = {
    ".py": "# implementation hidden",
    ".js": "/* implementation hidden */",
    ".jsx": "/* implementation hidden */",
    ".mjs": "/* implementation hidden */",
    ".cjs": "/* implementation hidden */",
    ".ts": "/* implementation hidden */",
    ".tsx": "/* implementation hidden */",
    ".go": "/* implementation hidden */",
    ".rs": "/* implementation hidden */",
    ".java": "/* implementation hidden */",
    ".cs": "/* implementation hidden */",
    ".swift": "/* implementation hidden */",
    ".kt": "/* implementation hidden */",
    ".kts": "/* implementation hidden */",
}


def get_placeholder(ext: str) -> bytes:
    return PLACEHOLDERS.get(ext.lower(), "/* implementation hidden */").encode("utf-8")


def is_block_node(node_type: str) -> bool:
    nt = node_type.lower()
    return nt in ("block", "compound_statement", "statement_block")


def is_callable_parent(parent_type: str | None) -> bool:
    if not parent_type:
        return False
    pt = parent_type.lower()
    return (
        "function" in pt
        or "method" in pt
        or "constructor" in pt
        or "arrow" in pt
        or "lambda" in pt
        or "closure" in pt
    )


def prune_signatures(filepath: str, code: bytes) -> str:
    """Returns the code with internal block logic replaced by placeholders."""
    path = Path(filepath)
    ext = path.suffix.lower()
    lang_id = EXTENSION_TO_LANGUAGE.get(ext)
    if not lang_id:
        return code.decode("utf-8", errors="replace")

    spec = get_spec(lang_id)
    if not spec:
        return code.decode("utf-8", errors="replace")

    parser = ts.Parser(spec.language)
    tree = parser.parse(code)

    if tree.root_node.has_error:
        logging.warning("Syntax error detected in %s, falling back to raw code.", filepath)
        return code.decode("utf-8", errors="replace")

    blocks_to_replace: list[tuple[int, int]] = []

    def walk(node: ts.Node) -> None:
        # If this is a block node belonging to a function/method/callable, prune it
        parent = node.parent
        parent_type = parent.type if parent else None

        if is_block_node(node.type):
            if is_callable_parent(parent_type):
                blocks_to_replace.append((node.start_byte, node.end_byte))
                return
            # If parent is a class, we want to walk its children to prune methods inside
            if parent_type and "class" in parent_type.lower():
                for child in node.children:
                    walk(child)
                return
            # For general top-level or control flow blocks inside functions
            blocks_to_replace.append((node.start_byte, node.end_byte))
            return

        for child in node.children:
            walk(child)

    walk(tree.root_node)

    # Sort blocks by start byte descending to replace without shifting earlier offsets
    blocks_to_replace.sort(key=lambda x: x[0], reverse=True)

    placeholder = get_placeholder(ext)
    mutated_code = bytearray(code)

    for start, end in blocks_to_replace:
        if ext == ".py":
            replacement = b"\n    " + placeholder + b"\n"
        else:
            replacement = b" { " + placeholder + b" }"

        mutated_code[start:end] = replacement

    return mutated_code.decode("utf-8", errors="replace")


def extract_map(filepath: str, code: bytes) -> str:
    """Extracts module linkages (imports) and API surface boundaries (exports, top-level classes)."""
    path = Path(filepath)
    ext = path.suffix.lower()
    lang_id = EXTENSION_TO_LANGUAGE.get(ext)
    if not lang_id:
        return code.decode("utf-8", errors="replace")

    spec = get_spec(lang_id)
    if not spec:
        return code.decode("utf-8", errors="replace")

    parser = ts.Parser(spec.language)
    tree = parser.parse(code)

    if tree.root_node.has_error:
        logging.warning("Syntax error detected in %s, falling back to raw code.", filepath)
        return code.decode("utf-8", errors="replace")

    output_parts: list[str] = []

    for node in tree.root_node.children:
        nt = node.type.lower()
        if "import" in nt or "require" in nt:
            output_parts.append(code[node.start_byte:node.end_byte].decode("utf-8", errors="replace"))
        elif "class" in nt or "export" in nt or "interface" in nt or "function" in nt:
            node_code = code[node.start_byte:node.end_byte]
            pruned_node = prune_signatures(filepath, node_code)
            output_parts.append(pruned_node)

    return "\n\n".join(output_parts)
