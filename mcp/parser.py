import ast
import importlib
import os
import sys

# Try importing tree-sitter to use if successfully compiled/installed
HAS_TREE_SITTER = False
try:
    import tree_sitter
    HAS_TREE_SITTER = True
except ImportError:
    pass

# Language-to-Module Mapping for tree-sitter packages pre-installed locally
LANG_MAP = {
    "py": ("tree_sitter_python", "language"),
    "js": ("tree_sitter_javascript", "language"),
    "jsx": ("tree_sitter_javascript", "language"),
    "ts": ("tree_sitter_typescript", "language_typescript"),
    "tsx": ("tree_sitter_typescript", "language_tsx"),
    "go": ("tree_sitter_go", "language"),
    "java": ("tree_sitter_java", "language"),
    "rs": ("tree_sitter_rust", "language"),
    "c": ("tree_sitter_c", "language"),
    "h": ("tree_sitter_c", "language"),
    "cpp": ("tree_sitter_cpp", "language"),
    "cc": ("tree_sitter_cpp", "language"),
    "cxx": ("tree_sitter_cpp", "language"),
    "hpp": ("tree_sitter_cpp", "language"),
    "hxx": ("tree_sitter_cpp", "language"),
    "hh": ("tree_sitter_cpp", "language"),
    "rb": ("tree_sitter_ruby", "language"),
    "cs": ("tree_sitter_c_sharp", "language"),
    "kt": ("tree_sitter_kotlin", "language"),
    "kts": ("tree_sitter_kotlin", "language"),
    "swift": ("tree_sitter_swift", "language"),
    "php": ("tree_sitter_php", "language"),
    "sh": ("tree_sitter_bash", "language"),
    "bash": ("tree_sitter_bash", "language"),
    "dart": ("tree_sitter_dart", "language"),
    "scala": ("tree_sitter_scala", "language"),
    "sc": ("tree_sitter_scala", "language"),
    "ex": ("tree_sitter_elixir", "language"),
    "exs": ("tree_sitter_elixir", "language"),
    "zig": ("tree_sitter_zig", "language"),
}

# Tree-sitter Symbol Query Patterns for each supported language
QUERIES = {
    "rs": """
        (function_item name: (identifier) @name) @def
        (struct_item name: (type_identifier) @name) @def
        (enum_item name: (type_identifier) @name) @def
        (trait_item name: (type_identifier) @name) @def
        (impl_item type: (type_identifier) @name) @def
        (type_item name: (type_identifier) @name) @def
        (const_item name: (identifier) @name) @def
    """,
    "ts": """
        (function_declaration name: (identifier) @name) @def
        (class_declaration name: (type_identifier) @name) @def
        (abstract_class_declaration name: (type_identifier) @name) @def
        (interface_declaration name: (type_identifier) @name) @def
        (type_alias_declaration name: (type_identifier) @name) @def
        (method_definition name: (property_identifier) @name) @def
        (variable_declarator name: (identifier) @name value: (arrow_function)) @def
    """,
    "tsx": """
        (function_declaration name: (identifier) @name) @def
        (class_declaration name: (type_identifier) @name) @def
        (abstract_class_declaration name: (type_identifier) @name) @def
        (interface_declaration name: (type_identifier) @name) @def
        (type_alias_declaration name: (type_identifier) @name) @def
        (method_definition name: (property_identifier) @name) @def
        (variable_declarator name: (identifier) @name value: (arrow_function)) @def
    """,
    "js": """
        (function_declaration name: (identifier) @name) @def
        (class_declaration name: (identifier) @name) @def
        (method_definition name: (property_identifier) @name) @def
        (variable_declarator name: (identifier) @name value: (arrow_function)) @def
    """,
    "jsx": """
        (function_declaration name: (identifier) @name) @def
        (class_declaration name: (identifier) @name) @def
        (method_definition name: (property_identifier) @name) @def
        (variable_declarator name: (identifier) @name value: (arrow_function)) @def
    """,
    "py": """
        (function_definition name: (identifier) @name) @def
        (class_definition name: (identifier) @name) @def
    """,
    "go": """
        (function_declaration name: (identifier) @name) @def
        (method_declaration name: (field_identifier) @name) @def
        (type_spec name: (type_identifier) @name) @def
    """,
    "java": """
        (method_declaration name: (identifier) @name) @def
        (class_declaration name: (identifier) @name) @def
        (interface_declaration name: (identifier) @name) @def
        (enum_declaration name: (identifier) @name) @def
        (constructor_declaration name: (identifier) @name) @def
    """,
    "c": """
        (function_definition declarator: (function_declarator declarator: (identifier) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (type_definition declarator: (type_identifier) @name) @def
    """,
    "h": """
        (function_definition declarator: (function_declarator declarator: (identifier) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (type_definition declarator: (type_identifier) @name) @def
    """,
    "cpp": """
        (function_definition declarator: (function_declarator declarator: (_) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (class_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (namespace_definition name: (identifier) @name) @def
    """,
    "cc": """
        (function_definition declarator: (function_declarator declarator: (_) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (class_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (namespace_definition name: (identifier) @name) @def
    """,
    "cxx": """
        (function_definition declarator: (function_declarator declarator: (_) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (class_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (namespace_definition name: (identifier) @name) @def
    """,
    "hpp": """
        (function_definition declarator: (function_declarator declarator: (_) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (class_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (namespace_definition name: (identifier) @name) @def
    """,
    "hxx": """
        (function_definition declarator: (function_declarator declarator: (_) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (class_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (namespace_definition name: (identifier) @name) @def
    """,
    "hh": """
        (function_definition declarator: (function_declarator declarator: (_) @name)) @def
        (struct_specifier name: (type_identifier) @name) @def
        (class_specifier name: (type_identifier) @name) @def
        (enum_specifier name: (type_identifier) @name) @def
        (namespace_definition name: (identifier) @name) @def
    """,
    "rb": """
        (method name: (identifier) @name) @def
        (singleton_method name: (identifier) @name) @def
        (class name: (_) @name) @def
        (module name: (_) @name) @def
    """,
    "cs": """
        (method_declaration name: (identifier) @name) @def
        (class_declaration name: (identifier) @name) @def
        (interface_declaration name: (identifier) @name) @def
        (struct_declaration name: (identifier) @name) @def
        (enum_declaration name: (identifier) @name) @def
        (record_declaration name: (identifier) @name) @def
        (namespace_declaration name: (identifier) @name) @def
    """,
    "kt": """
        (function_declaration name: (identifier) @name) @def
        (class_declaration name: (identifier) @name) @def
        (object_declaration name: (identifier) @name) @def
    """,
    "kts": """
        (function_declaration name: (identifier) @name) @def
        (class_declaration name: (identifier) @name) @def
        (object_declaration name: (identifier) @name) @def
    """,
    "swift": """
        (function_declaration name: (simple_identifier) @name) @def
        (class_declaration name: (type_identifier) @name) @def
        (protocol_declaration name: (type_identifier) @name) @def
        (protocol_function_declaration name: (simple_identifier) @name) @def
    """,
    "php": """
        (function_definition name: (name) @name) @def
        (class_declaration name: (name) @name) @def
        (interface_declaration name: (name) @name) @def
        (trait_declaration name: (name) @name) @def
        (method_declaration name: (name) @name) @def
    """,
    "sh": """
        (function_definition name: (word) @name) @def
    """,
    "bash": """
        (function_definition name: (word) @name) @def
    """,
    "dart": """
        (class_declaration name: (identifier) @name) @def
        (enum_declaration name: (identifier) @name) @def
        (mixin_declaration (identifier) @name) @def
        (type_alias (type_identifier) @name) @def
    """,
    "scala": """
        (class_definition name: (identifier) @name) @def
        (object_definition name: (identifier) @name) @def
        (trait_definition name: (identifier) @name) @def
        (enum_definition name: (identifier) @name) @def
        (function_definition name: (identifier) @name) @def
        (type_definition name: (type_identifier) @name) @def
    """,
    "sc": """
        (class_definition name: (identifier) @name) @def
        (object_definition name: (identifier) @name) @def
        (trait_definition name: (identifier) @name) @def
        (enum_definition name: (identifier) @name) @def
        (function_definition name: (identifier) @name) @def
        (type_definition name: (type_identifier) @name) @def
    """,
    "ex": """
        (call
          target: (identifier) @_keyword
          (arguments (alias) @name)
          (#any-of? @_keyword "defmodule" "defprotocol")) @def

        (call
          target: (identifier) @_keyword
          (arguments
            [
              (identifier) @name
              (call target: (identifier) @name)
              (binary_operator left: (call target: (identifier) @name) operator: "when")
            ])
          (#any-of? @_keyword "def" "defp" "defmacro" "defmacrop")) @def
    """,
    "exs": """
        (call
          target: (identifier) @_keyword
          (arguments (alias) @name)
          (#any-of? @_keyword "defmodule" "defprotocol")) @def

        (call
          target: (identifier) @_keyword
          (arguments
            [
              (identifier) @name
              (call target: (identifier) @name)
              (binary_operator left: (call target: (identifier) @name) operator: "when")
            ])
          (#any-of? @_keyword "def" "defp" "defmacro" "defmacrop")) @def
    """,
    "zig": """
        (function_declaration name: (identifier) @name) @def
    """,
}


def get_tree_sitter_language(ext):
    """Dynamic loader for tree-sitter language bindings from local packages."""
    if ext not in LANG_MAP:
        return None
    module_name, func_name = LANG_MAP[ext]
    try:
        module = importlib.import_module(module_name)
        capsule = getattr(module, func_name)()
        return tree_sitter.Language(capsule)
    except Exception as e:
        print(f"[Parser Warning] Failed to load tree-sitter for '{ext}': {e}", file=sys.stderr, flush=True)
        return None

def to_str(node) -> str:
    """Safely decodes tree-sitter node text to a string."""
    if node is None or node.text is None:
        return ""
    return str(node.text, "utf-8", errors="replace")


class ASTParser:
    """AST Parser that parses source code files to extract structural symbols,
    imports, and call occurrences across multiple languages.
    """

    def __init__(self, workspace_root):
        self.workspace_root = os.path.abspath(workspace_root)

    def parse_file(self, rel_path):
        """Parses a file and returns its symbols, imports, and unresolved call references."""
        abs_path = os.path.join(self.workspace_root, rel_path)
        if not os.path.exists(abs_path):
            return {"symbols": [], "imports": {}, "calls": []}

        ext = os.path.splitext(rel_path)[1].lower().lstrip(".")

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                source = f.read()
        except Exception:
            return {"symbols": [], "imports": {}, "calls": []}

        # Flawless legacy Python parsing using native standard AST engine
        if ext == "py":
            return self._parse_with_standard_ast(source, rel_path)

        # Multi-language Tree-sitter parsing
        if HAS_TREE_SITTER:
            try:
                lang = get_tree_sitter_language(ext)
                if lang:
                    return self._parse_with_tree_sitter(source, rel_path, ext, lang)
            except Exception as e:
                print(f"[Parser Warning] Error parsing {rel_path} with tree-sitter: {e}", file=sys.stderr, flush=True)

        return {"symbols": [], "imports": {}, "calls": []}

    def _parse_with_standard_ast(self, source, rel_path):
        """Extracts modules, classes, functions, docstrings, imports, and calls using python's ast module."""
        symbols = []
        imports = {}
        calls = []

        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError:
            return {"symbols": [], "imports": {}, "calls": []}

        # 1. Parse Module level
        module_doc = ast.get_docstring(tree) or ""
        lines = source.splitlines()
        symbols.append({
            "id": f"{rel_path}",
            "name": os.path.basename(rel_path),
            "type": "module",
            "file_path": rel_path,
            "start_line": 1,
            "end_line": len(lines) if lines else 1,
            "docstring": module_doc
        })

        # Track parent hierarchy to build unique symbol IDs
        class ParentVisitor(ast.NodeVisitor):
            def __init__(self, rel_path, symbols, imports, calls):
                self.rel_path = rel_path
                self.symbols = symbols
                self.imports = imports
                self.calls = calls
                self.current_class = None

            def visit_Import(self, node):
                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    self.imports[asname] = {
                        "module": name,
                        "name": "",  # Whole module
                        "type": "global"
                    }

            def visit_ImportFrom(self, node):
                module = node.module or ""
                # Handle relative imports (e.g. from .db import x)
                level = node.level
                if level > 0:
                    # Map relative to file path
                    parts = self.rel_path.split(os.sep)
                    parent_parts = parts[:-level]
                    if parent_parts:
                        module = ".".join(parent_parts) + (f".{module}" if module else "")

                for alias in node.names:
                    name = alias.name
                    asname = alias.asname or name
                    self.imports[asname] = {
                        "module": module,
                        "name": name,
                        "type": "local"
                    }

            def visit_ClassDef(self, node):
                class_name = node.name
                class_id = f"{self.rel_path}::{class_name}"
                doc = ast.get_docstring(node) or ""

                self.symbols.append({
                    "id": class_id,
                    "name": class_name,
                    "type": "class",
                    "file_path": self.rel_path,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": doc
                })

                # Traverse class body with class context
                old_class = self.current_class
                self.current_class = class_id
                self.generic_visit(node)
                self.current_class = old_class

            def visit_FunctionDef(self, node):
                self._handle_function(node)

            def visit_AsyncFunctionDef(self, node):
                self._handle_function(node)

            def _handle_function(self, node):
                func_name = node.name
                doc = ast.get_docstring(node) or ""

                if self.current_class:
                    func_id = f"{self.current_class}.{func_name}"
                    func_type = "method"
                else:
                    func_id = f"{self.rel_path}::{func_name}"
                    func_type = "function"

                self.symbols.append({
                    "id": func_id,
                    "name": func_name,
                    "type": func_type,
                    "file_path": self.rel_path,
                    "start_line": node.lineno,
                    "end_line": getattr(node, "end_lineno", node.lineno),
                    "docstring": doc
                })

                # Find calls inside this function
                caller_id = func_id

                class CallVisitor(ast.NodeVisitor):
                    def __init__(self, caller_id, calls):
                        self.caller_id = caller_id
                        self.calls = calls

                    def visit_Call(self, node):
                        func = node.func
                        if isinstance(func, ast.Name):
                            # Direct function call: e.g. foo()
                            self.calls.append({
                                "caller": self.caller_id,
                                "name": func.id,
                                "type": "direct"
                            })
                        elif isinstance(func, ast.Attribute):
                            # Method/attr call: e.g. obj.method() or self.method()
                            if isinstance(func.value, ast.Name) and func.value.id == "self":
                                self.calls.append({
                                    "caller": self.caller_id,
                                    "name": func.attr,
                                    "type": "self_method"
                                })
                            else:
                                self.calls.append({
                                    "caller": self.caller_id,
                                    "name": func.attr,
                                    "type": "attr_method"
                                })
                        self.generic_visit(node)

                CallVisitor(caller_id, self.calls).visit(node)

        visitor = ParentVisitor(rel_path, symbols, imports, calls)
        visitor.visit(tree)
        return {"symbols": symbols, "imports": imports, "calls": calls}

    def _parse_with_tree_sitter(self, source, rel_path, ext, lang):
        """Universal Multi-language Tree-sitter implementation.
        Extracts structural symbols, imports, and calls for 18+ languages.
        """
        parser = tree_sitter.Parser(lang)
        tree = parser.parse(bytes(source, "utf8"))

        symbols = []
        imports = {}
        calls = []

        # 1. Module Level
        lines = source.splitlines()
        symbols.append({
            "id": f"{rel_path}",
            "name": os.path.basename(rel_path),
            "type": "module",
            "file_path": rel_path,
            "start_line": 1,
            "end_line": len(lines) if lines else 1,
            "docstring": ""
        })

        # 2. Extract Symbols using precise query patterns
        query_str = QUERIES.get(ext)
        if query_str:
            try:
                query = tree_sitter.Query(lang, query_str)
                cursor = tree_sitter.QueryCursor(query)
                matches = cursor.matches(tree.root_node)

                for _, match_captures in matches:
                    def_nodes = match_captures.get("def", [])
                    name_nodes = match_captures.get("name", [])

                    if def_nodes and name_nodes:
                        d_node = def_nodes[0]
                        n_node = name_nodes[0]

                        sym_name = to_str(n_node)
                        sym_type = "function"

                        if "class" in d_node.type or d_node.type in (
                            "struct_item", "interface_declaration", "trait_item", "type_spec",
                            "enum_declaration", "record_declaration", "object_declaration"
                        ):
                            sym_type = "class"
                        elif "method" in d_node.type:
                            sym_type = "method"

                        # Resolve parent hierarchy (nested methods/classes)
                        parent = d_node.parent
                        parent_class = None
                        while parent:
                            if "class" in parent.type or parent.type in (
                                "struct_item", "interface_declaration", "trait_item", "type_spec"
                            ):
                                for child in parent.children:
                                    if child.type in ("identifier", "type_identifier"):
                                        parent_class = to_str(child)
                                        break
                                break
                            parent = parent.parent

                        if parent_class:
                            sym_id = f"{rel_path}::{parent_class}.{sym_name}"
                            if sym_type == "function":
                                sym_type = "method"
                        else:
                            sym_id = f"{rel_path}::{sym_name}"

                        # Sibling Comment Docstring lookup
                        docstring = ""
                        sibling = d_node.prev_sibling
                        if sibling and "comment" in sibling.type:
                            docstring = to_str(sibling).strip()

                        symbols.append({
                            "id": sym_id,
                            "name": sym_name,
                            "type": sym_type,
                            "file_path": rel_path,
                            "start_line": d_node.start_point[0] + 1,
                            "end_line": d_node.end_point[0] + 1,
                            "docstring": docstring
                        })
            except Exception as e:
                print(f"[Parser Warning] Error matching symbol queries for {rel_path}: {e}", file=sys.stderr, flush=True)

        # Helper to find caller symbol wrapping a given line
        def get_caller_id(node_line):
            best_symbol = symbols[0]
            best_range = (int(best_symbol["start_line"]), int(best_symbol["end_line"]))
            for sym in symbols[1:]:
                start = int(sym["start_line"])
                end = int(sym["end_line"])
                if start <= node_line <= end:
                    if (end - start) < (best_range[1] - best_range[0]):
                        best_symbol = sym
                        best_range = (start, end)
            return best_symbol["id"]

        # Recursive helper to find all descendants by type without using walk()
        def find_descendant_by_type(n, target_type):
            if n.type == target_type:
                return n
            for child in n.children:
                res = find_descendant_by_type(child, target_type)
                if res:
                    return res
            return None

        def find_all_by_type(n, target_type, results=None):
            if results is None:
                results = []
            if n.type == target_type:
                results.append(n)
            for child in n.children:
                find_all_by_type(child, target_type, results)
            return results

        # 3. Recursive AST Traversal to extract Imports and Call Sites
        def traverse(node):
            node_type = node.type

            # --- IMPORTS EXTRACTION ---
            if node_type in ("import_statement", "import_declaration"):
                # JS / TS / Go / Java / Scala / Dart
                src_node = None
                for child in node.children:
                    if child.type == "string" or "string_literal" in child.type:
                        src_node = child
                        break
                if not src_node:
                    for child in node.children:
                        src_node = find_descendant_by_type(child, "string")
                        if not src_node:
                            for t in ("string_literal", "interpreted_string_literal"):
                                src_node = find_descendant_by_type(child, t)
                                if src_node:
                                    break
                        if src_node:
                            break
                if src_node:
                    src_val = to_str(src_node).strip("'\"")
                    specifiers = find_all_by_type(node, "import_specifier")
                    for spec in specifiers:
                        for ident in spec.children:
                            if ident.type == "identifier":
                                name_val = to_str(ident)
                                imports[name_val] = {
                                    "module": src_val,
                                    "name": name_val,
                                    "type": "local"
                                }
                                break

                if ext == "java":
                    for child in node.children:
                        if child.type == "scoped_identifier":
                            full_path = to_str(child)
                            name_val = full_path.split(".")[-1]
                            imports[name_val] = {
                                "module": full_path,
                                "name": name_val,
                                "type": "global"
                            }
                elif ext == "go":
                    specs = find_all_by_type(node, "import_spec")
                    for spec in specs:
                        for literal in spec.children:
                            if literal.type == "interpreted_string_literal":
                                src_val = to_str(literal).strip("'\"")
                                alias = None
                                for alias_node in spec.children:
                                    if alias_node.type == "package_identifier":
                                        alias = to_str(alias_node)
                                        break
                                name_val = alias or src_val.split("/")[-1]
                                imports[name_val] = {
                                    "module": src_val,
                                    "name": "",  # Whole module
                                    "type": "global"
                                }

            elif node_type == "use_declaration":
                # Rust imports
                for child in node.children:
                    if child.type in ("scoped_identifier", "identifier"):
                        full_path = to_str(child)
                        name_val = full_path.split("::")[-1]
                        imports[name_val] = {
                            "module": full_path,
                            "name": name_val,
                            "type": "global"
                        }

            elif node_type == "preproc_include":
                # C / C++ includes
                for child in node.children:
                    if child.type in ("string_literal", "system_lib_string"):
                        src_val = to_str(child).strip("'\"<>")
                        name_val = os.path.basename(src_val).split(".")[0]
                        imports[name_val] = {
                            "module": src_val,
                            "name": "",  # Whole module
                            "type": "global"
                        }

            # --- CALL OCCURRENCES EXTRACTION ---
            if "call" in node_type or node_type in ("method_invocation", "new_expression", "object_creation_expression"):
                if node.children:
                    callee_node = node.children[0]
                    call_info = None

                    # Simple direct: foo()
                    if callee_node.type in ("identifier", "type_identifier", "name"):
                        call_info = {
                            "name": to_str(callee_node),
                            "type": "direct"
                        }
                    # Member/field call: obj.method()
                    elif callee_node.type in ("member_expression", "selector_expression", "attribute", "field_access", "navigation_expression"):
                        if len(callee_node.children) >= 2:
                            receiver_node = callee_node.children[0]
                            method_node = callee_node.children[-1]
                            receiver_text = to_str(receiver_node).strip()
                            method_name = to_str(method_node).strip()

                            call_info = {
                                "name": method_name,
                                "type": "self_method" if receiver_text in ("self", "this") else "attr_method"
                            }
                    # Traversal Fallback
                    else:
                        for child in reversed(callee_node.children):
                            if child.type in ("identifier", "property_identifier", "field_identifier", "name"):
                                call_info = {
                                    "name": to_str(child),
                                    "type": "attr_method"
                                }
                                break

                    if call_info:
                        caller_id = get_caller_id(node.start_point[0] + 1)
                        calls.append({
                            "caller": caller_id,
                            "name": call_info["name"],
                            "type": call_info["type"]
                        })

            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return {"symbols": symbols, "imports": imports, "calls": calls}
