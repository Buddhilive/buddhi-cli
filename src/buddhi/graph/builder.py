"""Orchestrates walking, per-file extraction, and containment-graph assembly.

Import/call/inheritance *resolution* happens in a later pass (`graph.resolver`)
once every file's symbols are known project-wide. This module builds nodes,
containment edges, and collects the raw import/call/inheritance records resolver.py needs.
"""

from __future__ import annotations

import datetime
import json
from dataclasses import dataclass, field
from pathlib import Path

from buddhi.discovery.walker import DiscoveredFile, WalkResult
from buddhi.graph.cache import (
    compute_sha256,
    deserialize_extraction_payload,
    serialize_extraction_payload,
)
from buddhi.graph.extractor import ExtractedFile, RawDefinition, extract_file
from buddhi.graph.model import (
    CLASS,
    CONFIDENCE_EXTRACTED,
    CONTAINS,
    CONTEXT_CONTAINS,
    DIRECTORY,
    FILE,
    METHOD,
    CodeGraph,
    GraphEdge,
    GraphNode,
    dir_node_id,
    file_node_id,
    symbol_node_id,
)
from buddhi.languages.registry import get_spec

_SELF_RECEIVERS = {"self", "this"}
_SNIPPET_MAX_CHARS = 4000


@dataclass
class PendingImport:
    source_id: str
    importing_file_rel: str
    language: str
    path_text: str
    line: int
    imported_names: list[str] = field(default_factory=list)


@dataclass
class PendingCall:
    source_id: str
    enclosing_class_id: str | None
    importing_file_rel: str
    call_name: str
    receiver: str | None
    line: int


@dataclass
class PendingInheritance:
    source_class_id: str
    importing_file_rel: str
    language: str
    base_name: str
    line: int


@dataclass
class _DefRecord:
    node_id: str
    kind: str
    start_byte: int
    end_byte: int
    class_scope_id: str | None


@dataclass
class BuildContext:
    graph: CodeGraph = field(default_factory=CodeGraph)
    pending_imports: list[PendingImport] = field(default_factory=list)
    pending_calls: list[PendingCall] = field(default_factory=list)
    pending_inheritances: list[PendingInheritance] = field(default_factory=list)
    file_symbol_index: dict[str, dict[str, str]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)
    extract_cache_entries: list[tuple[str, str, str, str, str]] = field(
        default_factory=list
    )


def build_graph(
    walk_result: WalkResult,
    existing_cache: dict[str, tuple[str, str, str, str]] | None = None,
) -> BuildContext:
    ctx = BuildContext()
    _add_directory_nodes(ctx, walk_result)

    files_parsed = 0
    files_failed = 0
    cache_hits = 0
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    for discovered in walk_result.files:
        spec = get_spec(discovered.language)
        if spec is None:
            files_failed += 1
            ctx.warnings.append(
                f"no grammar available for {discovered.language}: {discovered.rel_path}"
            )
            continue

        try:
            source = discovered.abs_path.read_bytes()
        except OSError as exc:
            files_failed += 1
            ctx.warnings.append(f"could not read {discovered.rel_path}: {exc}")
            continue

        file_sha = compute_sha256(source)
        extracted: ExtractedFile | None = None

        if existing_cache and discovered.rel_path in existing_cache:
            c_sha, c_lang, c_payload, c_updated = existing_cache[discovered.rel_path]
            if c_sha == file_sha and c_lang == discovered.language:
                try:
                    payload_dict = deserialize_extraction_payload(c_payload)
                    extracted = ExtractedFile.from_dict(payload_dict)
                    cache_hits += 1
                    ctx.extract_cache_entries.append(
                        (discovered.rel_path, c_sha, c_lang, c_payload, c_updated)
                    )
                except (json.JSONDecodeError, KeyError, ValueError, TypeError):
                    extracted = None

        if extracted is None:
            try:
                extracted = extract_file(source, spec)
                payload_json = serialize_extraction_payload(extracted.to_dict())
                ctx.extract_cache_entries.append(
                    (
                        discovered.rel_path,
                        file_sha,
                        discovered.language,
                        payload_json,
                        now_iso,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                files_failed += 1
                ctx.warnings.append(f"failed to parse {discovered.rel_path}: {exc}")
                continue

        if extracted.parse_had_errors:
            ctx.warnings.append(
                f"parsed with syntax errors (best-effort): {discovered.rel_path}"
            )

        files_parsed += 1
        _integrate_file(discovered, extracted, ctx, source)

    ctx.stats["files_parsed"] = files_parsed
    ctx.stats["files_failed"] = files_failed
    ctx.stats["cache_hits"] = cache_hits
    ctx.stats["node_count"] = len(ctx.graph.nodes)
    return ctx


def _make_snippet(source: bytes, start_byte: int, end_byte: int) -> str:
    text = source[start_byte:end_byte].decode("utf-8", errors="replace")
    if len(text) > _SNIPPET_MAX_CHARS:
        return text[:_SNIPPET_MAX_CHARS] + "\n… (truncated)"
    return text


def _add_directory_nodes(ctx: BuildContext, walk_result: WalkResult) -> None:
    for dir_rel in sorted(walk_result.directories):
        parent_rel = Path(dir_rel).parent.as_posix()
        parent_id = dir_node_id(parent_rel) if parent_rel != "." else None
        node = ctx.graph.add_node(
            GraphNode(
                id=dir_node_id(dir_rel),
                kind=DIRECTORY,
                name=Path(dir_rel).name,
                qualified_name=dir_rel,
                parent_id=parent_id,
            )
        )
        if parent_id:
            ctx.graph.add_edge(
                GraphEdge(
                    source=parent_id,
                    target=node.id,
                    kind=CONTAINS,
                    confidence=CONFIDENCE_EXTRACTED,
                    confidence_score=1.0,
                    context=CONTEXT_CONTAINS,
                )
            )


def _integrate_file(
    discovered: DiscoveredFile,
    extracted: ExtractedFile,
    ctx: BuildContext,
    source: bytes,
) -> None:
    graph = ctx.graph
    rel_path = discovered.rel_path
    parent_dir = Path(rel_path).parent.as_posix()
    parent_id = dir_node_id(parent_dir) if parent_dir != "." else None

    file_id = file_node_id(rel_path)
    graph.add_node(
        GraphNode(
            id=file_id,
            kind=FILE,
            name=Path(rel_path).name,
            qualified_name=rel_path,
            file_path=rel_path,
            language=discovered.language,
            parent_id=parent_id,
        )
    )
    if parent_id:
        graph.add_edge(
            GraphEdge(
                source=parent_id,
                target=file_id,
                kind=CONTAINS,
                confidence=CONFIDENCE_EXTRACTED,
                confidence_score=1.0,
                context=CONTEXT_CONTAINS,
            )
        )

    symbol_index: dict[str, str] = {}
    used_ids: dict[str, tuple[str, int]] = {}
    def_records: list[_DefRecord] = []
    class_byte_to_id: dict[int, str] = {}

    stack: list[tuple[RawDefinition, str, str, str | None]] = []

    def make_node_id(kind: str, qualified_name: str, start_line: int) -> str:
        base_id = symbol_node_id(kind, rel_path, qualified_name)
        prior = used_ids.get(base_id)
        if prior is None:
            used_ids[base_id] = (rel_path, start_line)
            return base_id
        if prior == (rel_path, start_line):
            return base_id
        return f"{base_id}:L{start_line}"

    for defn in extracted.definitions:
        while stack and stack[-1][0].end_byte <= defn.start_byte:
            stack.pop()

        if defn.receiver_type:
            local_name = f"{defn.receiver_type}.{defn.local_name}"
            kind = METHOD if defn.kind == "function" else defn.kind
        else:
            local_name = defn.local_name
            kind = defn.kind

        if stack:
            _parent_defn, parent_node_id, parent_qualified, parent_class_scope = stack[
                -1
            ]
            qualified_name = f"{parent_qualified}.{local_name}"
            node_parent_id = parent_node_id
            if kind == "function":
                kind = "method"
            class_scope_for_children = parent_class_scope
        else:
            qualified_name = local_name
            node_parent_id = file_id
            class_scope_for_children = None

        node_id = make_node_id(kind, qualified_name, defn.start_line)

        if kind == CLASS:
            class_scope_for_children = node_id
            class_byte_to_id[defn.start_byte] = node_id

        graph.add_node(
            GraphNode(
                id=node_id,
                kind=kind,
                name=defn.local_name,
                qualified_name=qualified_name,
                file_path=rel_path,
                language=discovered.language,
                start_line=defn.start_line,
                end_line=defn.end_line,
                parent_id=node_parent_id,
                snippet=_make_snippet(source, defn.start_byte, defn.end_byte),
            )
        )
        graph.add_edge(
            GraphEdge(
                source=node_parent_id,
                target=node_id,
                kind=CONTAINS,
                confidence=CONFIDENCE_EXTRACTED,
                confidence_score=1.0,
                context=CONTEXT_CONTAINS,
            )
        )

        symbol_index[defn.local_name] = node_id
        if defn.receiver_type:
            symbol_index[local_name] = node_id

        own_class_scope = class_scope_for_children
        def_records.append(
            _DefRecord(
                node_id=node_id,
                kind=kind,
                start_byte=defn.start_byte,
                end_byte=defn.end_byte,
                class_scope_id=own_class_scope,
            )
        )
        stack.append((defn, node_id, qualified_name, own_class_scope))

    ctx.file_symbol_index[rel_path] = symbol_index

    for imp in extracted.imports:
        ctx.pending_imports.append(
            PendingImport(
                source_id=file_id,
                importing_file_rel=rel_path,
                language=discovered.language,
                path_text=imp.path_text,
                line=imp.start_line,
                imported_names=list(imp.imported_names),
            )
        )

    for inh in extracted.inheritances:
        class_id = class_byte_to_id.get(inh.class_start_byte)
        if class_id:
            ctx.pending_inheritances.append(
                PendingInheritance(
                    source_class_id=class_id,
                    importing_file_rel=rel_path,
                    language=discovered.language,
                    base_name=inh.base_name,
                    line=inh.start_line,
                )
            )

    for call in extracted.calls:
        best: _DefRecord | None = None
        for rec in def_records:
            in_range = rec.start_byte <= call.node_start_byte < rec.end_byte
            is_callable = rec.kind in ("function", METHOD)
            if (
                in_range
                and is_callable
                and (best is None or rec.start_byte > best.start_byte)
            ):
                best = rec
        source_id = best.node_id if best is not None else file_id
        enclosing_class_id = best.class_scope_id if best is not None else None

        ctx.pending_calls.append(
            PendingCall(
                source_id=source_id,
                enclosing_class_id=enclosing_class_id,
                importing_file_rel=rel_path,
                call_name=call.name,
                receiver=call.receiver,
                line=call.start_line,
            )
        )
