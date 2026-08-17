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
    (tmp_path / "main.py").write_text("def helper():\n    pass\n\ndef run():\n    helper()\n")

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
    assert any(
        e.resolved and e.target == "method:main.py::Foo.bar" for e in call_edges
    )


def test_unresolved_call_becomes_external(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text("def run():\n    unknown_thing()\n")

    ctx = _build(tmp_path)

    call_edges = [e for e in ctx.graph.edges if e.kind == CALLS]
    assert any(
        not e.resolved and e.target == "external:unknown_thing" for e in call_edges
    )
