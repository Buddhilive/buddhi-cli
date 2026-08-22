from pathlib import Path

from buddhi.docgen.planner import (
    build_docs_plan,
    content_hash,
    doc_path_for_node,
    read_existing_content_hash,
    topological_doc_order,
)
from buddhi.graph.model import CALLS, FUNCTION, CodeGraph, GraphEdge, GraphNode


def _fn(node_id: str, name: str, file_path: str = "mod.py") -> GraphNode:
    return GraphNode(
        id=node_id,
        kind=FUNCTION,
        name=name,
        qualified_name=name,
        file_path=file_path,
        snippet=f"def {name}(): pass",
        start_line=1,
        end_line=1,
    )


def test_topological_order_puts_callee_before_caller() -> None:
    graph = CodeGraph()
    helper = graph.add_node(_fn("f:helper", "helper"))
    caller = graph.add_node(_fn("f:caller", "caller"))
    graph.add_edge(GraphEdge(source=caller.id, target=helper.id, kind=CALLS))

    order = [n.id for n in topological_doc_order(graph)]

    assert order.index(helper.id) < order.index(caller.id)


def test_topological_order_handles_cycles_without_raising() -> None:
    graph = CodeGraph()
    a = graph.add_node(_fn("f:a", "a"))
    b = graph.add_node(_fn("f:b", "b"))
    graph.add_edge(GraphEdge(source=a.id, target=b.id, kind=CALLS))
    graph.add_edge(GraphEdge(source=b.id, target=a.id, kind=CALLS))

    order = topological_doc_order(graph)

    assert {n.id for n in order} == {a.id, b.id}


def test_content_hash_stable_and_sensitive_to_change() -> None:
    h1 = content_hash("def f(): pass")
    h2 = content_hash("def f(): pass")
    h3 = content_hash("def f(): return 1")

    assert h1 == h2
    assert h1 != h3


def test_doc_path_mirrors_source_layout() -> None:
    node = _fn("f:x", "helper", file_path="src/pkg/mod.py")

    path = doc_path_for_node(node)

    assert path == ".buddhi/docs/src/pkg/mod/helper.md"


def test_read_existing_content_hash_missing_file_returns_none(tmp_path: Path) -> None:
    assert read_existing_content_hash(tmp_path / "nope.md") is None


def test_read_existing_content_hash_parses_frontmatter(tmp_path: Path) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text(
        "---\nsources:\n  - id: src\n    content_hash: abc123\n---\n# Summary\n",
        encoding="utf-8",
    )

    assert read_existing_content_hash(doc) == "abc123"


def test_build_docs_plan_marks_unchanged_node_as_not_needing_generation(tmp_path: Path) -> None:
    graph = CodeGraph()
    graph.add_node(_fn("f:helper", "helper", file_path="mod.py"))

    plan = build_docs_plan(graph, tmp_path)
    assert plan[0].needs_generation is True

    doc_abs = tmp_path / plan[0].doc_path
    doc_abs.parent.mkdir(parents=True, exist_ok=True)
    doc_abs.write_text(
        f"---\nsources:\n  - id: src\n    content_hash: {plan[0].content_hash}\n---\n",
        encoding="utf-8",
    )

    plan2 = build_docs_plan(graph, tmp_path)
    assert plan2[0].needs_generation is False


def test_build_docs_plan_flags_changed_snippet_as_needing_regeneration(tmp_path: Path) -> None:
    graph = CodeGraph()
    node = graph.add_node(_fn("f:helper", "helper", file_path="mod.py"))

    plan = build_docs_plan(graph, tmp_path)
    doc_abs = tmp_path / plan[0].doc_path
    doc_abs.parent.mkdir(parents=True, exist_ok=True)
    doc_abs.write_text(
        f"---\nsources:\n  - id: src\n    content_hash: {plan[0].content_hash}\n---\n",
        encoding="utf-8",
    )

    node.snippet = "def helper(): return 42"
    plan2 = build_docs_plan(graph, tmp_path)
    assert plan2[0].needs_generation is True
