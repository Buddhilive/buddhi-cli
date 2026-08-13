"""Second pass: turn raw import/call text into edges against the full node inventory.

This is explicitly heuristic / best-effort, not a semantic resolver:
- Imports resolve only for relative/same-project specifiers we can derive a
  file path from; everything else (external packages, stdlib, dynamic
  imports, C#/Swift namespaces) becomes a deduped `external:` node.
- Calls resolve only same-file exact-name matches and `self.`/`this.` calls
  within the enclosing class; cross-file ambiguous name matches are
  intentionally NOT auto-linked, to avoid false-positive edges on common
  names like `run`/`get`/`init`.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from buddhi.graph.builder import BuildContext, PendingCall, PendingImport
from buddhi.graph.model import CALLS, CLASS, FILE, FUNCTION, IMPORTS, METHOD, GraphEdge

_SELF_RECEIVERS = {"self", "this"}


def resolve(ctx: BuildContext) -> None:
    file_paths = {node.file_path for node in ctx.graph.nodes.values() if node.kind == FILE}
    class_methods: dict[str, dict[str, str]] = {}
    for node in ctx.graph.nodes.values():
        if node.kind == METHOD and node.parent_id:
            class_methods.setdefault(node.parent_id, {})[node.name] = node.id

    for imp in ctx.pending_imports:
        _resolve_import(ctx, imp, file_paths)

    for call in ctx.pending_calls:
        _resolve_call(ctx, call, class_methods)


def _candidate_exists(file_paths: set[str | None], *candidates: str) -> str | None:
    for c in candidates:
        if c in file_paths:
            return c
    return None


def _resolve_import(ctx: BuildContext, imp: PendingImport, file_paths: set[str | None]) -> None:
    target_rel: str | None = None

    if imp.language == "python":
        target_rel = _resolve_python_import(imp, file_paths)
    elif imp.language in ("javascript", "typescript", "tsx"):
        target_rel = _resolve_js_import(imp, file_paths)
    elif imp.language == "rust":
        target_rel = _resolve_rust_import(imp, file_paths)
    elif imp.language in ("java", "kotlin"):
        target_rel = _resolve_dotted_suffix_import(imp, file_paths)
    # go, csharp, swift: left external in this MVP (see module docstring)

    if target_rel is not None:
        edge = GraphEdge(source=imp.source_id, target=f"file:{target_rel}", kind=IMPORTS, resolved=True)
    else:
        external = ctx.graph.get_or_create_external(imp.path_text)
        edge = GraphEdge(source=imp.source_id, target=external.id, kind=IMPORTS, resolved=False)
    ctx.graph.add_edge(edge)


def _resolve_python_import(imp: PendingImport, file_paths: set[str | None]) -> str | None:
    text = imp.path_text
    importing_dir = PurePosixPath(imp.importing_file_rel).parent

    if text.startswith("."):
        dots = len(text) - len(text.lstrip("."))
        remainder = text[dots:]
        base = importing_dir
        for _ in range(dots - 1):
            base = base.parent
        module_path = base / remainder.replace(".", "/") if remainder else base
    else:
        module_path = PurePosixPath(text.replace(".", "/"))

    return _candidate_exists(
        file_paths,
        f"{module_path}.py",
        f"{module_path}/__init__.py",
    )


_JS_SUFFIXES = (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs")


def _resolve_js_import(imp: PendingImport, file_paths: set[str | None]) -> str | None:
    text = imp.path_text
    if not text.startswith("."):
        return None
    importing_dir = PurePosixPath(imp.importing_file_rel).parent
    base = (importing_dir / text).as_posix()
    base = str(PurePosixPath(base))

    candidates = [base] if PurePosixPath(base).suffix else []
    for suffix in _JS_SUFFIXES:
        candidates.append(f"{base}{suffix}")
    for suffix in _JS_SUFFIXES:
        candidates.append(f"{base}/index{suffix}")

    return _candidate_exists(file_paths, *candidates)


def _resolve_rust_import(imp: PendingImport, file_paths: set[str | None]) -> str | None:
    text = imp.path_text
    importing_dir = PurePosixPath(imp.importing_file_rel).parent

    if text.startswith("crate::") or text == "crate":
        remainder = text[len("crate::") :] if text != "crate" else ""
        base = PurePosixPath("src") / remainder.replace("::", "/") if remainder else PurePosixPath("src/lib")
    elif text.startswith("self::"):
        remainder = text[len("self::") :]
        base = importing_dir / remainder.replace("::", "/")
    elif text.startswith("super::"):
        remainder = text[len("super::") :]
        base = importing_dir.parent / remainder.replace("::", "/")
    else:
        return None

    return _candidate_exists(file_paths, f"{base}.rs", f"{base}/mod.rs")


def _resolve_dotted_suffix_import(imp: PendingImport, file_paths: set[str | None]) -> str | None:
    text = imp.path_text
    ext = ".java" if imp.language == "java" else ".kt"
    converted = text.replace(".", "/")
    suffix = f"/{converted}{ext}"
    matches = [fp for fp in file_paths if fp and fp.endswith(suffix)]
    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_call(
    ctx: BuildContext,
    call: PendingCall,
    class_methods: dict[str, dict[str, str]],
) -> None:
    target_id: str | None = None

    if call.receiver in _SELF_RECEIVERS and call.enclosing_class_id:
        target_id = class_methods.get(call.enclosing_class_id, {}).get(call.call_name)

    if target_id is None and call.receiver is None:
        symbol_index = ctx.file_symbol_index.get(call.importing_file_rel, {})
        candidate = symbol_index.get(call.call_name)
        if candidate is not None:
            node = ctx.graph.nodes.get(candidate)
            if node is not None and node.kind in (FUNCTION, METHOD, CLASS):
                target_id = candidate

    if target_id is not None:
        edge = GraphEdge(source=call.source_id, target=target_id, kind=CALLS, resolved=True)
    else:
        external_name = f"{call.receiver}.{call.call_name}" if call.receiver else call.call_name
        external = ctx.graph.get_or_create_external(external_name)
        edge = GraphEdge(source=call.source_id, target=external.id, kind=CALLS, resolved=False)
    ctx.graph.add_edge(edge)
