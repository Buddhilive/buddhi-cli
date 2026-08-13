"""Parse a single file with tree-sitter and extract nodes + containment/import/call info."""

from __future__ import annotations

from dataclasses import dataclass, field

import tree_sitter as ts

from buddhi.languages.registry import LanguageSpec

# capture names that mark a "definition" (a node that becomes a graph symbol node)
_DEFINITION_KIND_MAP = {
    "definition.class": "class",
    "definition.impl": "class",
    "definition.extension": "class",
    "definition.function": "function",
    "definition.method": "method",
}


@dataclass
class RawDefinition:
    node: object  # tree_sitter.Node
    kind: str
    local_name: str
    receiver_type: str | None = None
    start_line: int = 0
    end_line: int = 0
    start_byte: int = 0
    end_byte: int = 0


@dataclass
class RawImport:
    path_text: str
    start_line: int = 0


@dataclass
class RawCall:
    name: str
    receiver: str | None
    node_start_byte: int
    start_line: int = 0


@dataclass
class ExtractedFile:
    definitions: list[RawDefinition] = field(default_factory=list)
    imports: list[RawImport] = field(default_factory=list)
    calls: list[RawCall] = field(default_factory=list)
    parse_had_errors: bool = False


def _node_text(node: ts.Node) -> str:
    return (node.text or b"").decode("utf-8", errors="replace")


def _clean_receiver_type(text: str) -> str:
    return text.lstrip("*&").strip()


def _clean_import_text(text: str) -> str:
    text = text.strip()
    if len(text) >= 2 and text[0] in "\"'" and text[-1] == text[0]:
        text = text[1:-1]
    return text


def extract_file(source: bytes, spec: LanguageSpec) -> ExtractedFile:
    parser = ts.Parser(spec.language)
    tree = parser.parse(source)

    cursor = ts.QueryCursor(spec.query)
    matches = cursor.matches(tree.root_node)

    definitions: dict[int, RawDefinition] = {}  # keyed by def node start_byte
    imports: list[RawImport] = []
    calls: dict[int, RawCall] = {}  # keyed by call node start_byte, prefer richer match

    for _pattern_index, captures in matches:
        def_capture_name = next(
            (name for name in captures if name in _DEFINITION_KIND_MAP), None
        )
        if def_capture_name is not None:
            def_node = captures[def_capture_name][0]
            name_nodes = captures.get("name")
            if not name_nodes:
                continue
            local_name = _node_text(name_nodes[0])
            receiver_nodes = captures.get("receiver.type")
            receiver_type = (
                _clean_receiver_type(_node_text(receiver_nodes[0])) if receiver_nodes else None
            )
            kind = _DEFINITION_KIND_MAP[def_capture_name]
            existing = definitions.get(def_node.start_byte)
            candidate = RawDefinition(
                node=def_node,
                kind=kind,
                local_name=local_name,
                receiver_type=receiver_type,
                start_line=def_node.start_point[0] + 1,
                end_line=def_node.end_point[0] + 1,
                start_byte=def_node.start_byte,
                end_byte=def_node.end_byte,
            )
            # Prefer the richer match (the one carrying a receiver_type) when a
            # node matches more than one pattern (e.g. Kotlin extension functions).
            if existing is None or (receiver_type and not existing.receiver_type):
                definitions[def_node.start_byte] = candidate
            continue

        if "import" in captures and "import.path" in captures:
            path_node = captures["import.path"][0]
            imports.append(
                RawImport(
                    path_text=_clean_import_text(_node_text(path_node)),
                    start_line=path_node.start_point[0] + 1,
                )
            )
            continue

        if "call" in captures and "call.name" in captures:
            call_node = captures["call"][0]
            name_text = _node_text(captures["call.name"][0])
            receiver_nodes = captures.get("call.receiver")
            receiver_text = _node_text(receiver_nodes[0]) if receiver_nodes else None
            existing_call = calls.get(call_node.start_byte)
            candidate_call = RawCall(
                name=name_text,
                receiver=receiver_text,
                node_start_byte=call_node.start_byte,
                start_line=call_node.start_point[0] + 1,
            )
            if existing_call is None or (receiver_text and not existing_call.receiver):
                calls[call_node.start_byte] = candidate_call

    return ExtractedFile(
        definitions=sorted(definitions.values(), key=lambda d: d.start_byte),
        imports=imports,
        calls=list(calls.values()),
        parse_had_errors=tree.root_node.has_error,
    )
