import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
from tree_sitter import Language, Parser, Node

# Language bindings
try:
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_go
    import tree_sitter_rust
    import tree_sitter_java
    import tree_sitter_c_sharp
    import tree_sitter_swift
    import tree_sitter_kotlin
    import tree_sitter_haskell
except ImportError as e:
    logging.warning(f"Missing some tree-sitter language bindings: {e}")

# Mapping of file extensions to Language objects
LANGUAGE_MAP: Dict[str, Any] = {}


def load_languages():
    if LANGUAGE_MAP:
        return

    try:
        LANGUAGE_MAP[".py"] = Language(tree_sitter_python.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".js"] = Language(tree_sitter_javascript.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".ts"] = Language(tree_sitter_typescript.language_typescript())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".tsx"] = Language(tree_sitter_typescript.language_tsx())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".go"] = Language(tree_sitter_go.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".rs"] = Language(tree_sitter_rust.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".java"] = Language(tree_sitter_java.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".cs"] = Language(tree_sitter_c_sharp.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".swift"] = Language(tree_sitter_swift.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".kt"] = Language(tree_sitter_kotlin.language())
    except NameError:
        pass

    try:
        LANGUAGE_MAP[".hs"] = Language(tree_sitter_haskell.language())
    except NameError:
        pass


def is_structural_node(node_type: str) -> bool:
    """Check if a node type represents a high-level structural entity."""
    structural_keywords = [
        "class",
        "function",
        "method",
        "interface",
        "struct",
        "impl",
        "trait",
        "enum",
        "type_declaration",
    ]
    nt = node_type.lower()
    return any(kw in nt for kw in structural_keywords)


def extract_name(node: Node, source_bytes: bytes) -> str:
    """Attempt to extract the name of a structural node."""
    # Often the first child of type 'identifier' or 'type_identifier' is the name
    for child in node.children:
        if "identifier" in child.type.lower() or "name" in child.type.lower():
            return source_bytes[child.start_byte : child.end_byte].decode(
                "utf-8", errors="replace"
            )
    return "anonymous"


def walk_tree(
    node: Node,
    source_bytes: bytes,
    nodes_list: List[Dict],
    parent_id: Optional[int] = None,
) -> None:
    """
    Recursively walk the tree to find structural nodes.
    We capture top-level structural entities and discard children structural entities
    (internal method definitions) to avoid noise, as requested.
    """
    if is_structural_node(node.type):
        name = extract_name(node, source_bytes)
        node_content = source_bytes[node.start_byte : node.end_byte].decode(
            "utf-8", errors="replace"
        )

        node_data = {
            "type": node.type,
            "name": name,
            "content": node_content,
            "start_line": node.start_point[0] + 1,
            "end_line": node.end_point[0] + 1,
        }
        nodes_list.append(node_data)

        # We STOP traversing children to discard internal structural nodes
        # as requested ("discard the structural children nodes representing localized internal method definitions")
        return

    # Continue traversing if this isn't a structural node
    for child in node.children:
        walk_tree(child, source_bytes, nodes_list, parent_id)


def parse_file(filepath: Path) -> List[Dict]:
    """Parse a file and return its structural nodes."""
    load_languages()

    ext = filepath.suffix.lower()
    if ext not in LANGUAGE_MAP:
        return []

    language = LANGUAGE_MAP[ext]
    parser = Parser(language)

    with open(filepath, "rb") as f:
        source_bytes = f.read()

    tree = parser.parse(source_bytes)
    nodes_list: List[Dict] = []

    walk_tree(tree.root_node, source_bytes, nodes_list)

    return nodes_list

def extract_file_references(filepath: Path) -> Dict[str, List[str]]:
    """
    Pass 2: Extract identifiers (function calls, variable usage) and imports
    from the given file using tree-sitter. Returns a dict with 'identifiers' and 'imports'.
    """
    load_languages()
    ext = filepath.suffix.lower()
    if ext not in LANGUAGE_MAP:
        return {"identifiers": [], "imports": []}

    language = LANGUAGE_MAP[ext]
    parser = Parser(language)
    
    with open(filepath, "rb") as f:
        source_bytes = f.read()
        
    tree = parser.parse(source_bytes)
    
    identifiers = set()
    imports = set()
    
    def walk_refs(node: Node):
        nt = node.type.lower()
        
        # Very broad heuristic for polyglot identifiers
        if "identifier" in nt or nt == "name":
            name = source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="ignore")
            # Filter out trivially short or common non-semantic keywords
            if len(name) > 2 and name not in {"self", "this", "True", "False", "None"}:
                identifiers.add(name)
                
        # Broad heuristic for polyglot imports (import_statement, import_from_statement, etc.)
        if "import" in nt:
            # For simplicity, extract all identifiers inside the import statement
            for child in node.children:
                if "identifier" in child.type.lower() or child.type == "dotted_name":
                    imp = source_bytes[child.start_byte:child.end_byte].decode("utf-8", errors="ignore")
                    if imp and imp != "import" and imp != "from":
                        imports.add(imp)
                        
        for child in node.children:
            walk_refs(child)

    walk_refs(tree.root_node)
    
    return {
        "identifiers": list(identifiers),
        "imports": list(imports)
    }
