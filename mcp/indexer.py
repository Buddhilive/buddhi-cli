import os
from db import CodeGraphDB
from parser import ASTParser
from graph import CodeGraphAnalyzer

SKIP_DIRS = {
    ".venv", "venv", "env", ".git", ".github", ".mypy_cache", ".ruff_cache",
    ".buddhi", "node_modules", "__pycache__", "build", "dist", "buddhi_ai.egg-info"
}


class CodeIndexer:
    def __init__(self, workspace_root=None, db_path=None):
        if not workspace_root:
            workspace_root = os.getcwd()
        self.workspace_root = os.path.abspath(workspace_root)
        self.db = CodeGraphDB(db_path)
        self.parser = ASTParser(self.workspace_root)

    def scan_files(self):
        """Walks the workspace root and collects all relative file paths of python files."""
        py_files = []
        for root, dirs, files in os.walk(self.workspace_root):
            # Prune skipped directories in-place
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.workspace_root)
                    py_files.append(rel_path)
        return py_files

    def index_codebase(self):
        """Runs the complete two-pass indexing and clustering pipeline."""
        self.db.clear_database()
        py_files = self.scan_files()

        # PASS 1: Parse AST structure and build nodes
        all_symbols = []
        file_imports = {}  # rel_path -> imports dict
        unresolved_calls = []  # List of (caller_id, callee_name, type, file)

        for rel_path in py_files:
            parse_result = self.parser.parse_file(rel_path)
            symbols = parse_result["symbols"]
            imports = parse_result["imports"]
            calls = parse_result["calls"]

            all_symbols.extend(symbols)
            file_imports[rel_path] = imports

            # Keep track of calls to resolve in Pass 2
            for call in calls:
                unresolved_calls.append({
                    "caller": call["caller"],
                    "name": call["name"],
                    "type": call["type"],
                    "file_path": rel_path
                })

        # Insert nodes into database first so reference resolution can query them
        self.db.insert_nodes(all_symbols)

        # Create quick mapping of symbol_name -> list of node IDs for fast resolution lookups
        name_to_nodes = {}
        id_to_node = {}
        for symbol in all_symbols:
            name = symbol["name"]
            id_to_node[symbol["id"]] = symbol
            if name not in name_to_nodes:
                name_to_nodes[name] = []
            name_to_nodes[name].append(symbol)

        # PASS 2: Reference Resolution (Edges)
        edges = []
        for call in unresolved_calls:
            caller_id = call["caller"]
            callee_name = call["name"]
            call_type = call["type"]
            file_path = call["file_path"]

            target_id = None

            # A. Self method calls (self.foo())
            if call_type == "self_method":
                # caller is of format "file_path::ClassName.method_name"
                if "::" in caller_id and "." in caller_id:
                    class_part = caller_id.split(".")[0]  # "file_path::ClassName"
                    candidate_id = f"{class_part}.{callee_name}"
                    if candidate_id in id_to_node:
                        target_id = candidate_id

            # B. Local call within same file (foo())
            if not target_id:
                candidate_id = f"{file_path}::{callee_name}"
                if candidate_id in id_to_node:
                    target_id = candidate_id

            # C. Imported symbols (from cli.main import setup_model)
            if not target_id and file_path in file_imports:
                imports = file_imports[file_path]
                if callee_name in imports:
                    import_info = imports[callee_name]
                    # import_info is like {"module": "cli.main", "name": "setup_model"}
                    target_module = import_info["module"]
                    target_name = import_info["name"]

                    # Convert module dots to path parts (e.g. cli.main -> cli/main.py)
                    module_rel_py = target_module.replace(".", "/") + ".py"
                    
                    if target_name:
                        # e.g., from cli.main import setup_model
                        candidate_id = f"{module_rel_py}::{target_name}"
                        if candidate_id in id_to_node:
                            target_id = candidate_id
                    else:
                        # e.g., import cli.main -> target_name is None
                        candidate_id = f"{module_rel_py}"
                        if candidate_id in id_to_node:
                            target_id = candidate_id

            # D. Namespace traversal fallback (e.g. obj.method() where we match method globally)
            if not target_id:
                if callee_name in name_to_nodes:
                    candidates = name_to_nodes[callee_name]
                    # If exactly one unique class/function/method exists globally, make link
                    if len(candidates) == 1:
                        target_id = candidates[0]["id"]
                    else:
                        # Prioritize nodes in the same directory or close files
                        for cand in candidates:
                            cand_dir = os.path.dirname(cand["file_path"])
                            file_dir = os.path.dirname(file_path)
                            if cand_dir == file_dir:
                                target_id = cand["id"]
                                break

            # If resolved, add edge
            if target_id and target_id != caller_id:
                edges.append({
                    "source": caller_id,
                    "target": target_id,
                    "type": "calls"
                })

        # Insert edges into database
        self.db.insert_edges(edges)

        # PASS 3: Graph Clustering & Communities
        nodes_in_db = self.db.get_all_nodes()
        edges_in_db = self.db.get_all_edges()

        analyzer = CodeGraphAnalyzer()
        community_mappings = analyzer.compute_communities(nodes_in_db, edges_in_db)
        
        # Save communities back to database
        self.db.update_communities(community_mappings)

        return len(nodes_in_db), len(edges_in_db)
