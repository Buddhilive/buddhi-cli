from pathlib import Path

from buddhi.discovery.walker import walk
from buddhi.graph.builder import build_graph
from buddhi.graph.model import CALLS, IMPORTS
from buddhi.graph.resolver import resolve


def _build(root: Path):
    walk_result = walk(root)
    ctx = build_graph(walk_result)
    resolve(ctx)
    return ctx


def test_relative_python_import_resolves_to_file_node(tmp_path: Path) -> None:
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("")
    (tmp_path / "pkg" / "helper.py").write_text("class Helper:\n    pass\n")
    (tmp_path / "main.py").write_text("from pkg.helper import Helper\n")

    ctx = _build(tmp_path)

    import_edges = [e for e in ctx.graph.edges if e.kind == IMPORTS]
    assert any(e.target == "file:pkg/helper.py" and e.resolved for e in import_edges)


def test_external_package_import_becomes_unresolved_external(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("import numpy\n")

    ctx = _build(tmp_path)

    import_edges = [e for e in ctx.graph.edges if e.kind == IMPORTS]
    assert len(import_edges) == 1
    assert import_edges[0].resolved is False
    assert import_edges[0].target == "external:numpy"


def test_same_file_call_resolves(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "def helper():\n    pass\n\ndef run():\n    helper()\n"
    )

    ctx = _build(tmp_path)

    call_edges = [e for e in ctx.graph.edges if e.kind == CALLS]
    resolved = [e for e in call_edges if e.resolved]
    assert any(e.target == "function:main.py::helper" for e in resolved)


def test_self_call_resolves_to_class_method(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "class Foo:\n"
        "    def bar(self):\n"
        "        pass\n"
        "    def baz(self):\n"
        "        self.bar()\n"
    )

    ctx = _build(tmp_path)

    call_edges = [e for e in ctx.graph.edges if e.kind == CALLS]
    assert any(e.resolved and e.target == "method:main.py::Foo.bar" for e in call_edges)


def test_unresolved_call_becomes_external(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def run():\n    unknown_thing()\n")

    ctx = _build(tmp_path)

    call_edges = [e for e in ctx.graph.edges if e.kind == CALLS]
    assert any(
        not e.resolved and e.target == "external:unknown_thing" for e in call_edges
    )


def test_resolve_cross_file_calls_with_named_imports() -> None:
    from buddhi.graph.builder import BuildContext, PendingCall, PendingImport
    from buddhi.graph.model import (
        CALLS,
        CONFIDENCE_EXTRACTED,
        FUNCTION,
        CodeGraph,
        GraphNode,
    )
    from buddhi.graph.resolver import resolve

    ctx = BuildContext(graph=CodeGraph())
    # File 1: helper.py with compute()
    ctx.graph.add_node(
        GraphNode(
            id="file:helper.py",
            kind="file",
            name="helper.py",
            qualified_name="helper.py",
            file_path="helper.py",
        )
    )
    ctx.graph.add_node(
        GraphNode(
            id="function:helper.py::compute",
            kind=FUNCTION,
            name="compute",
            qualified_name="compute",
            file_path="helper.py",
        )
    )

    # File 2: main.py imports compute from helper and calls it
    ctx.graph.add_node(
        GraphNode(
            id="file:main.py",
            kind="file",
            name="main.py",
            qualified_name="main.py",
            file_path="main.py",
        )
    )
    ctx.graph.add_node(
        GraphNode(
            id="function:main.py::run",
            kind=FUNCTION,
            name="run",
            qualified_name="run",
            file_path="main.py",
        )
    )

    ctx.pending_imports.append(
        PendingImport(
            source_id="file:main.py",
            importing_file_rel="main.py",
            language="python",
            path_text="helper",
            line=1,
            imported_names=["compute"],
        )
    )
    ctx.pending_calls.append(
        PendingCall(
            source_id="function:main.py::run",
            enclosing_class_id=None,
            importing_file_rel="main.py",
            call_name="compute",
            receiver=None,
            line=2,
        )
    )

    resolve(ctx)
    call_edges = [e for e in ctx.graph.edges if e.kind == CALLS]
    assert len(call_edges) == 1
    assert call_edges[0].target == "function:helper.py::compute"
    assert call_edges[0].resolved is True
    assert call_edges[0].confidence == CONFIDENCE_EXTRACTED
    assert call_edges[0].confidence_score >= 0.9


def test_resolve_inheritance_edges() -> None:
    from buddhi.graph.builder import BuildContext, PendingInheritance
    from buddhi.graph.model import (
        CLASS,
        CONFIDENCE_EXTRACTED,
        INHERITS,
        CodeGraph,
        GraphNode,
    )
    from buddhi.graph.resolver import resolve

    ctx = BuildContext(graph=CodeGraph())
    ctx.graph.add_node(
        GraphNode(
            id="class:models.py::Base",
            kind=CLASS,
            name="Base",
            qualified_name="Base",
            file_path="models.py",
        )
    )
    ctx.graph.add_node(
        GraphNode(
            id="class:models.py::Sub",
            kind=CLASS,
            name="Sub",
            qualified_name="Sub",
            file_path="models.py",
        )
    )

    ctx.pending_inheritances.append(
        PendingInheritance(
            source_class_id="class:models.py::Sub",
            importing_file_rel="models.py",
            language="python",
            base_name="Base",
            line=2,
        )
    )

    resolve(ctx)
    inh_edges = [e for e in ctx.graph.edges if e.kind == INHERITS]
    assert len(inh_edges) == 1
    assert inh_edges[0].source == "class:models.py::Sub"
    assert inh_edges[0].target == "class:models.py::Base"
    assert inh_edges[0].resolved is True
    assert inh_edges[0].confidence == CONFIDENCE_EXTRACTED
