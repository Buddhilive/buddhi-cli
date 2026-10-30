import json
from pathlib import Path

from buddhi.mcp.tools.memory import execute_buddhi_memory


def test_execute_buddhi_memory_tool(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    code_file = ws / "handler.py"
    code_file.write_text("def handle_request(): pass\n", encoding="utf-8")

    # 1. Action: remember
    res = execute_buddhi_memory(
        action="remember",
        title="Async Handlers",
        summary="All API handlers must be async.",
        body="Detailed body note.",
        kind="convention",
        scope="project",
        path_globs=["handler.py"],
        sources=["handler.py#L1-L1"],
        root_path=ws,
    )
    data = json.loads(res)
    assert data["status"] == "success"
    node_id = data["id"]
    assert "mem-convention-async-handlers" in node_id

    # 2. Action: status
    status_raw = execute_buddhi_memory(action="status", root_path=ws)
    status_data = json.loads(status_raw)
    assert status_data["total_nodes"] == 1
    assert status_data["budget"]["is_valid"]

    # 3. Action: search with path glob match
    search_match = execute_buddhi_memory(
        action="search",
        query="async",
        active_files=["handler.py"],
        root_path=ws,
    )
    s_data = json.loads(search_match)
    assert s_data["count"] == 1

    # Search with non-matching path
    search_nomatch = execute_buddhi_memory(
        action="search",
        query="async",
        active_files=["other.py"],
        root_path=ws,
    )
    s_nomatch = json.loads(search_nomatch)
    assert s_nomatch["count"] == 0

    # 4. Action: read
    read_out = execute_buddhi_memory(
        action="read",
        node_id=node_id,
        root_path=ws,
    )
    assert "All API handlers must be async." in read_out
    assert "# Summary" in read_out
