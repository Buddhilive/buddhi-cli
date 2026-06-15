import logging
from pathlib import Path
from tree_sitter import Node, Parser
from buddhi_ai.parser.tree_sitter import LANGUAGE_MAP, load_languages

PLACEHOLDERS = {
    ".py": "# implementation hidden",
    ".js": "/* implementation hidden */",
    ".ts": "/* implementation hidden */",
    ".tsx": "/* implementation hidden */",
    ".go": "/* implementation hidden */",
    ".rs": "/* implementation hidden */",
    ".java": "/* implementation hidden */",
    ".cs": "/* implementation hidden */",
    ".swift": "/* implementation hidden */",
    ".kt": "/* implementation hidden */",
    ".hs": "-- implementation hidden",
}


def get_placeholder(ext: str) -> bytes:
    return PLACEHOLDERS.get(ext.lower(), "/* implementation hidden */").encode("utf-8")


def is_block_node(node_type: str) -> bool:
    nt = node_type.lower()
    return nt in ("block", "compound_statement", "statement_block")


def prune_signatures(filepath: str, code: bytes) -> str:
    """Returns the code with internal block logic replaced by placeholders."""
    load_languages()
    path = Path(filepath)
    ext = path.suffix.lower()
    
    if ext not in LANGUAGE_MAP:
        return code.decode("utf-8", errors="replace")
        
    parser = Parser(LANGUAGE_MAP[ext])
    tree = parser.parse(code)
    
    if tree.root_node.has_error:
        logging.warning(f"Syntax error detected in {filepath}, falling back to raw code.")
        return code.decode("utf-8", errors="replace")
        
    blocks_to_replace = []
    
    def walk(node: Node):
        if is_block_node(node.type):
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
    """
    Extracts module linkages (imports) and API surface boundaries (exports, top-level classes).
    """
    load_languages()
    path = Path(filepath)
    ext = path.suffix.lower()
    
    if ext not in LANGUAGE_MAP:
        return code.decode("utf-8", errors="replace")
        
    parser = Parser(LANGUAGE_MAP[ext])
    tree = parser.parse(code)
    
    if tree.root_node.has_error:
        logging.warning(f"Syntax error detected in {filepath}, falling back to raw code.")
        return code.decode("utf-8", errors="replace")
        
    output_parts = []
    
    for node in tree.root_node.children:
        nt = node.type.lower()
        if "import" in nt or "require" in nt:
            output_parts.append(code[node.start_byte:node.end_byte].decode("utf-8", errors="replace"))
        elif "class" in nt or "export" in nt or "interface" in nt or "function" in nt:
            # We want the signature of these top-level entities, so we prune their blocks
            # Since node indices are absolute to the file, we can just run a mini pruning on this node's bounds.
            node_code = code[node.start_byte:node.end_byte]
            node_tree = parser.parse(node_code)
            
            blocks = []
            def walk_node(n: Node):
                if is_block_node(n.type):
                    blocks.append((n.start_byte, n.end_byte))
                    return
                for child in n.children:
                    walk_node(child)
            
            walk_node(node_tree.root_node)
            blocks.sort(key=lambda x: x[0], reverse=True)
            
            placeholder = get_placeholder(ext)
            mutated_node = bytearray(node_code)
            for start, end in blocks:
                if ext == ".py":
                    replacement = b"\n    " + placeholder + b"\n"
                else:
                    replacement = b" { " + placeholder + b" }"
                mutated_node[start:end] = replacement
                
            output_parts.append(mutated_node.decode("utf-8", errors="replace"))
            
    return "\n\n".join(output_parts)
