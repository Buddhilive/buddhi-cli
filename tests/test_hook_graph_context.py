import json
import subprocess
import sys
from pathlib import Path


def test_graph_context_hook_session_start(tmp_path: Path) -> None:
    hook_script = Path("src/buddhi/templates/agents/hooks/graph_context.py").resolve()
    payload = json.dumps({"hook_event_name": "SessionStart"})
    res = subprocess.run(
        [sys.executable, str(hook_script)],
        input=payload,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        check=False,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert isinstance(data, dict)


def test_graph_context_hook_pre_tool_use_fail_open(tmp_path: Path) -> None:
    hook_script = Path("src/buddhi/templates/agents/hooks/graph_context.py").resolve()
    payload = json.dumps(
        {"tool_name": "view_file", "tool_input": {"file_path": "non_existent.py"}}
    )
    res = subprocess.run(
        [sys.executable, str(hook_script)],
        input=payload,
        text=True,
        capture_output=True,
        cwd=tmp_path,
        check=False,
    )
    assert res.returncode == 0
    data = json.loads(res.stdout.strip())
    assert data.get("decision") == "allow"
