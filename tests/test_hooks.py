"""
Tests for cli.hooks — enforcer script writing and Antigravity settings.json integration.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload(tool_name: str) -> str:
    """Serialize a minimal BeforeTool payload matching the Antigravity hook protocol."""
    return json.dumps({"tool_name": tool_name, "tool_input": {}})


def _run_enforcer(script: Path, tool_name: str) -> dict:
    """Execute the enforcer script with the given tool_name payload on stdin."""
    result = subprocess.run(
        [sys.executable, str(script)],
        input=_payload(tool_name),
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, f"Enforcer exited non-zero: {result.stderr}"
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# Enforcer script behaviour tests
# ---------------------------------------------------------------------------


class TestEnforcerScript:
    """Run the actual enforcer.py template to verify its stdin/stdout contract."""

    @pytest.fixture()
    def enforcer(self, tmp_path: Path) -> Path:
        """Install the enforcer script into a temp directory and return its path."""
        from cli.hooks.setup import write_enforcer_script

        return write_enforcer_script(tmp_path)

    def test_deny_run_command(self, enforcer: Path) -> None:
        response = _run_enforcer(enforcer, "run_command")
        assert response["permission"] == "deny"
        output = response["hookSpecificOutput"]
        assert output["permissionDecision"] == "deny"
        assert "buddhi_run_command" in output["message"]
        assert "run_command" in output["message"]

    def test_deny_grep_search(self, enforcer: Path) -> None:
        response = _run_enforcer(enforcer, "grep_search")
        assert response["permission"] == "deny"
        assert "buddhi_grep_search" in response["hookSpecificOutput"]["message"]

    def test_deny_view_file(self, enforcer: Path) -> None:
        response = _run_enforcer(enforcer, "view_file")
        assert response["permission"] == "deny"
        assert "buddhi_view_file" in response["hookSpecificOutput"]["message"]

    def test_allow_unknown_tool(self, enforcer: Path) -> None:
        response = _run_enforcer(enforcer, "write_file")
        assert response["permission"] == "allow"

    def test_allow_on_empty_stdin(self, enforcer: Path) -> None:
        """Enforcer must not crash or block on empty stdin — fail open."""
        result = subprocess.run(
            [sys.executable, str(enforcer)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        response = json.loads(result.stdout)
        assert response["permission"] == "allow"

    def test_allow_on_malformed_stdin(self, enforcer: Path) -> None:
        """Enforcer must not crash on invalid JSON — fail open."""
        result = subprocess.run(
            [sys.executable, str(enforcer)],
            input="not valid json {{{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        response = json.loads(result.stdout)
        assert response["permission"] == "allow"


# ---------------------------------------------------------------------------
# write_enforcer_script tests
# ---------------------------------------------------------------------------


class TestWriteEnforcerScript:
    def test_script_written_to_correct_path(self, tmp_path: Path) -> None:
        from cli.hooks.setup import write_enforcer_script

        result = write_enforcer_script(tmp_path)
        assert result == tmp_path / "enforcer.py"
        assert result.exists()

    def test_script_creates_parent_dir(self, tmp_path: Path) -> None:
        from cli.hooks.setup import write_enforcer_script

        deep = tmp_path / "a" / "b" / "hooks"
        write_enforcer_script(deep)
        assert (deep / "enforcer.py").exists()

    def test_script_is_valid_python(self, tmp_path: Path) -> None:
        from cli.hooks.setup import write_enforcer_script

        script = write_enforcer_script(tmp_path)
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(script)],
            capture_output=True,
        )
        assert result.returncode == 0, f"Syntax error in enforcer: {result.stderr.decode()}"


# ---------------------------------------------------------------------------
# install_antigravity_hooks tests
# ---------------------------------------------------------------------------


class TestInstallAntigravityHooks:
    @pytest.fixture()
    def fake_home(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
        """Redirect Path.home() to a temp dir so we never touch the real ~/.gemini."""
        monkeypatch.setattr(Path, "home", staticmethod(lambda: tmp_path))
        return tmp_path

    @pytest.fixture()
    def enforcer(self, tmp_path: Path) -> Path:
        from cli.hooks.setup import write_enforcer_script

        return write_enforcer_script(tmp_path / "hooks")

    # ------------------------------------------------------------------

    def test_settings_created_when_absent(
        self, fake_home: Path, enforcer: Path
    ) -> None:
        from cli.hooks.setup import install_antigravity_hooks

        install_antigravity_hooks(enforcer)

        settings_path = fake_home / ".gemini" / "settings.json"
        assert settings_path.exists()
        data = json.loads(settings_path.read_text())
        before_tool = data["hooks"]["BeforeTool"]
        # One entry per intercepted tool
        assert len(before_tool) == 3
        matchers = {e["matcher"] for e in before_tool}
        assert "^(run_command)$" in matchers
        assert "^(grep_search)$" in matchers
        assert "^(view_file)$" in matchers

    def test_settings_merged_with_existing_keys(
        self, fake_home: Path, enforcer: Path
    ) -> None:
        """Pre-existing top-level keys must be preserved after the merge."""
        from cli.hooks.setup import install_antigravity_hooks

        settings_path = fake_home / ".gemini" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {"theme": "dark", "fontSize": 14}
        settings_path.write_text(json.dumps(existing))

        install_antigravity_hooks(enforcer)

        data = json.loads(settings_path.read_text())
        assert data["theme"] == "dark"
        assert data["fontSize"] == 14
        assert "hooks" in data

    def test_existing_before_tool_entries_preserved(
        self, fake_home: Path, enforcer: Path
    ) -> None:
        """User's own BeforeTool entries must not be removed."""
        from cli.hooks.setup import install_antigravity_hooks

        settings_path = fake_home / ".gemini" / "settings.json"
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        existing = {
            "hooks": {
                "BeforeTool": [
                    {
                        "matcher": "^(my_custom_tool)$",
                        "hooks": [{"type": "command", "command": "my-script"}],
                    }
                ]
            }
        }
        settings_path.write_text(json.dumps(existing))

        install_antigravity_hooks(enforcer)

        data = json.loads(settings_path.read_text())
        before_tool = data["hooks"]["BeforeTool"]
        custom = [e for e in before_tool if e["matcher"] == "^(my_custom_tool)$"]
        assert len(custom) == 1, "User's existing BeforeTool entry was removed"

    def test_idempotent_no_duplicate_entries(
        self, fake_home: Path, enforcer: Path
    ) -> None:
        """Running install twice must not add duplicate hook entries."""
        from cli.hooks.setup import install_antigravity_hooks

        install_antigravity_hooks(enforcer)
        install_antigravity_hooks(enforcer)

        settings_path = fake_home / ".gemini" / "settings.json"
        data = json.loads(settings_path.read_text())
        before_tool = data["hooks"]["BeforeTool"]
        buddhi_entries = [e for e in before_tool if e.get("__buddhi") == "buddhi-hook-enforcer"]
        assert len(buddhi_entries) == 3, (
            f"Expected 3 buddhi entries after 2 installs, got {len(buddhi_entries)}"
        )
