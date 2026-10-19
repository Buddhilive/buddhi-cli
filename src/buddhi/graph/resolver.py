"""Second pass: turn raw import/call/inheritance text into edges with confidence tiers.

Resolves:
- Imports: relative/same-project file paths.
- Inherits: class/interface/trait extensions mapped to internal or external types.
- Calls: same-file calls, self/this class methods, cross-file calls via explicit imports,
  and unique project-wide non-noise symbols.
"""

from __future__ import annotations

from pathlib import PurePosixPath

from buddhi.graph.builder import (
    BuildContext,
    PendingCall,
    PendingImport,
    PendingInheritance,
)
from buddhi.graph.model import (
    CALLS,
    CLASS,
    CONFIDENCE_AMBIGUOUS,
    CONFIDENCE_EXTRACTED,
    CONFIDENCE_INFERRED,
    CONTEXT_CALL,
    CONTEXT_IMPORT,
    CONTEXT_INHERIT,
    FILE,
    FUNCTION,
    IMPORTS,
    INHERITS,
    METHOD,
    GraphEdge,
)

_SELF_RECEIVERS = {"self", "this"}
_COMMON_NOISE_NAMES = {
    "get",
    "set",
    "run",
    "init",
    "start",
    "stop",
    "close",
    "open",
    "read",
    "write",
    "main",
    "execute",
    "handle",
    "process",
    "update",
    "create",
    "delete",
    "render",
    "call",
    "build",
    "format",
    "check",
    "setup",
    "tearDown",
    "setUp",
    "test",
}


def resolve(ctx: BuildContext) -> None:
    file_paths = {
        node.file_path for node in ctx.graph.nodes.values() if node.kind == FILE
    }

    file_exports: dict[str, dict[str, str]] = {}
    global_symbols: dict[str, list[str]] = {}
    class_methods: dict[str, dict[str, str]] = {}

    for node in ctx.graph.nodes.values():
        if node.file_path and node.kind in (FUNCTION, METHOD, CLASS):
            file_exports.setdefault(node.file_path, {})[node.name] = node.id
            global_symbols.setdefault(node.name, []).append(node.id)
            if node.qualified_name != node.name:
                file_exports[node.file_path][node.qualified_name] = node.id
                global_symbols.setdefault(node.qualified_name, []).append(node.id)

        if node.kind == METHOD and node.parent_id:
            class_methods.setdefault(node.parent_id, {})[node.name] = node.id

    file_imports_map: dict[str, list[str]] = {}
    named_imports_map: dict[str, dict[str, str]] = {}

    for imp in ctx.pending_imports:
        target_rel = _resolve_import(ctx, imp, file_paths)
        if target_rel:
            file_imports_map.setdefault(imp.importing_file_rel, []).append(target_rel)
            if imp.imported_names:
                for sym_name in imp.imported_names:
                    named_imports_map.setdefault(imp.importing_file_rel, {})[
                        sym_name
                    ] = target_rel

    for inh in ctx.pending_inheritances:
        _resolve_inheritance(
            ctx, inh, file_exports, file_imports_map, named_imports_map, global_symbols
        )

    for call in ctx.pending_calls:
        _resolve_call(
            ctx,
            call,
            class_methods,
            file_exports,
            file_imports_map,
            named_imports_map,
            global_symbols,
        )


def _candidate_exists(file_paths: set[str | None], *candidates: str) -> str | None:
    for c in candidates:
        if c in file_paths:
            return c
    return None


def _resolve_import(
    ctx: BuildContext, imp: PendingImport, file_paths: set[str | None]
) -> str | None:
    target_rel: str | None = None

    if imp.language == "python":
        target_rel = _resolve_python_import(imp, file_paths)
    elif imp.language in ("javascript", "typescript", "tsx"):
        target_rel = _resolve_js_import(imp, file_paths)
    elif imp.language == "rust":
        target_rel = _resolve_rust_import(imp, file_paths)
    elif imp.language in ("java", "kotlin"):
        target_rel = _resolve_dotted_suffix_import(imp, file_paths)
    elif imp.language in ("go", "csharp", "swift"):
        target_rel = _resolve_package_or_namespace_import(imp, file_paths)

    if target_rel is not None:
        edge = GraphEdge(
            source=imp.source_id,
            target=f"file:{target_rel}",
            kind=IMPORTS,
            resolved=True,
            confidence=CONFIDENCE_EXTRACTED,
            confidence_score=1.0,
            context=CONTEXT_IMPORT,
        )
    else:
        external = ctx.graph.get_or_create_external(imp.path_text)
        edge = GraphEdge(
            source=imp.source_id,
            target=external.id,
            kind=IMPORTS,
            resolved=False,
            confidence=CONFIDENCE_AMBIGUOUS,
            confidence_score=0.2,
            context=CONTEXT_IMPORT,
        )
    ctx.graph.add_edge(edge)
    return target_rel


def _resolve_python_import(
    imp: PendingImport, file_paths: set[str | None]
) -> str | None:
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
        base = (
            PurePosixPath("src") / remainder.replace("::", "/")
            if remainder
            else PurePosixPath("src/lib")
        )
    elif text.startswith("self::"):
        remainder = text[len("self::") :]
        base = importing_dir / remainder.replace("::", "/")
    elif text.startswith("super::"):
        remainder = text[len("super::") :]
        base = importing_dir.parent / remainder.replace("::", "/")
    else:
        return None

    return _candidate_exists(file_paths, f"{base}.rs", f"{base}/mod.rs")


def _resolve_dotted_suffix_import(
    imp: PendingImport, file_paths: set[str | None]
) -> str | None:
    text = imp.path_text
    ext = ".java" if imp.language == "java" else ".kt"
    converted = text.replace(".", "/")
    suffix = f"/{converted}{ext}"
    matches = [fp for fp in file_paths if fp and fp.endswith(suffix)]
    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_package_or_namespace_import(
    imp: PendingImport, file_paths: set[str | None]
) -> str | None:
    text = imp.path_text.strip("/")
    last_seg = text.split("/")[-1].split(".")[-1]
    matches = [
        fp
        for fp in file_paths
        if fp
        and (
            PurePosixPath(fp).parent.name == last_seg
            or PurePosixPath(fp).stem == last_seg
        )
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def _resolve_inheritance(
    ctx: BuildContext,
    inh: PendingInheritance,
    file_exports: dict[str, dict[str, str]],
    file_imports_map: dict[str, list[str]],
    named_imports_map: dict[str, dict[str, str]],
    global_symbols: dict[str, list[str]],
) -> None:
    target_id: str | None = None
    confidence = CONFIDENCE_EXTRACTED
    conf_score = 1.0

    raw_base = inh.base_name.split(".")[-1]

    # 1. Same-file base class
    same_file_defs = file_exports.get(inh.importing_file_rel, {})
    if inh.base_name in same_file_defs:
        target_id = same_file_defs[inh.base_name]
    elif raw_base in same_file_defs:
        target_id = same_file_defs[raw_base]

    # 2. Named import from another file
    if target_id is None:
        target_file = named_imports_map.get(inh.importing_file_rel, {}).get(raw_base)
        if target_file and target_file in file_exports:
            target_id = file_exports[target_file].get(raw_base)
            confidence = CONFIDENCE_EXTRACTED
            conf_score = 0.95

    # 3. File imports from another module
    if target_id is None:
        for imported_file in file_imports_map.get(inh.importing_file_rel, []):
            if (
                imported_file in file_exports
                and raw_base in file_exports[imported_file]
            ):
                target_id = file_exports[imported_file][raw_base]
                confidence = CONFIDENCE_EXTRACTED
                conf_score = 0.90
                break

    # 4. Global symbol unique match
    if target_id is None and raw_base in global_symbols:
        candidates = global_symbols[raw_base]
        if len(candidates) == 1:
            target_id = candidates[0]
            confidence = CONFIDENCE_INFERRED
            conf_score = 0.75

    if target_id is not None:
        edge = GraphEdge(
            source=inh.source_class_id,
            target=target_id,
            kind=INHERITS,
            resolved=True,
            confidence=confidence,
            confidence_score=conf_score,
            context=CONTEXT_INHERIT,
        )
    else:
        ext = ctx.graph.get_or_create_external(inh.base_name)
        edge = GraphEdge(
            source=inh.source_class_id,
            target=ext.id,
            kind=INHERITS,
            resolved=False,
            confidence=CONFIDENCE_AMBIGUOUS,
            confidence_score=0.2,
            context=CONTEXT_INHERIT,
        )
    ctx.graph.add_edge(edge)


def _resolve_call(
    ctx: BuildContext,
    call: PendingCall,
    class_methods: dict[str, dict[str, str]],
    file_exports: dict[str, dict[str, str]],
    file_imports_map: dict[str, list[str]],
    named_imports_map: dict[str, dict[str, str]],
    global_symbols: dict[str, list[str]],
) -> None:
    target_id: str | None = None
    confidence = CONFIDENCE_EXTRACTED
    conf_score = 1.0

    # 1. self/this method call
    if call.receiver in _SELF_RECEIVERS and call.enclosing_class_id:
        target_id = class_methods.get(call.enclosing_class_id, {}).get(call.call_name)
        if target_id:
            confidence = CONFIDENCE_EXTRACTED
            conf_score = 1.0

    # 2. Same-file function or class constructor call
    if target_id is None and call.receiver is None:
        symbol_index = ctx.file_symbol_index.get(call.importing_file_rel, {})
        candidate = symbol_index.get(call.call_name)
        if candidate is not None:
            node = ctx.graph.nodes.get(candidate)
            if node is not None and node.kind in (FUNCTION, METHOD, CLASS):
                target_id = candidate
                confidence = CONFIDENCE_EXTRACTED
                conf_score = 1.0

    # 3. Explicit named import match: `from pkg.mod import helper` -> `helper()`
    if target_id is None and call.receiver is None:
        target_file = named_imports_map.get(call.importing_file_rel, {}).get(
            call.call_name
        )
        if target_file and target_file in file_exports:
            target_id = file_exports[target_file].get(call.call_name)
            if target_id:
                confidence = CONFIDENCE_EXTRACTED
                conf_score = 0.95

    # 4. Module-qualified call: `mod.helper()` where `mod` is an imported file or alias
    if target_id is None and call.receiver:
        for imported_file in file_imports_map.get(call.importing_file_rel, []):
            imp_stem = PurePosixPath(imported_file).stem
            if (
                imp_stem == call.receiver or call.receiver == imp_stem.replace("_", "")
            ) and (
                imported_file in file_exports
                and call.call_name in file_exports[imported_file]
            ):
                target_id = file_exports[imported_file][call.call_name]
                confidence = CONFIDENCE_EXTRACTED
                conf_score = 0.90
                break

    # 5. Receiver is an imported class or type constructor/static method
    if target_id is None and call.receiver:
        target_file = named_imports_map.get(call.importing_file_rel, {}).get(
            call.receiver
        )
        if target_file and target_file in file_exports:
            qname = f"{call.receiver}.{call.call_name}"
            target_id = file_exports[target_file].get(qname) or file_exports[
                target_file
            ].get(call.call_name)
            if target_id:
                confidence = CONFIDENCE_INFERRED
                conf_score = 0.80

    # 6. Globally unique project symbol (non-noise)
    if (
        target_id is None
        and call.receiver is None
        and call.call_name not in _COMMON_NOISE_NAMES
        and call.call_name in global_symbols
    ):
        candidates = global_symbols[call.call_name]
        if len(candidates) == 1:
            target_id = candidates[0]
            confidence = CONFIDENCE_INFERRED
            conf_score = 0.65
        elif len(candidates) > 1:
            # Check if exactly one shares directory prefix
            imp_dir = PurePosixPath(call.importing_file_rel).parent
            dir_matches = [
                cid
                for cid in candidates
                if ctx.graph.nodes.get(cid)
                and PurePosixPath(ctx.graph.nodes[cid].file_path or "").parent
                == imp_dir
            ]
            if len(dir_matches) == 1:
                target_id = dir_matches[0]
                confidence = CONFIDENCE_AMBIGUOUS
                conf_score = 0.40

    if target_id is not None:
        edge = GraphEdge(
            source=call.source_id,
            target=target_id,
            kind=CALLS,
            resolved=True,
            confidence=confidence,
            confidence_score=conf_score,
            context=CONTEXT_CALL,
        )
    else:
        external_name = (
            f"{call.receiver}.{call.call_name}" if call.receiver else call.call_name
        )
        external = ctx.graph.get_or_create_external(external_name)
        edge = GraphEdge(
            source=call.source_id,
            target=external.id,
            kind=CALLS,
            resolved=False,
            confidence=CONFIDENCE_AMBIGUOUS,
            confidence_score=0.2,
            context=CONTEXT_CALL,
        )
    ctx.graph.add_edge(edge)
