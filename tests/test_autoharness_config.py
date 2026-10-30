from __future__ import annotations

from pathlib import Path

from buddhi.scripts.autoharness.config import (
    get_consolidate_every_n,
    get_disable_global,
    get_reflect_every_n,
    resolve_project_root,
)


def test_config_defaults(monkeypatch) -> None:
    monkeypatch.delenv("AUTOHARNESS_DISABLE_GLOBAL", raising=False)
    monkeypatch.delenv("AUTOHARNESS_REFLECT_EVERY_N", raising=False)
    monkeypatch.delenv("AUTOHARNESS_CONSOLIDATE_EVERY_N", raising=False)

    assert get_disable_global() is False
    assert get_reflect_every_n() == 50
    assert get_consolidate_every_n() == 250


def test_config_overrides(monkeypatch) -> None:
    monkeypatch.setenv("AUTOHARNESS_DISABLE_GLOBAL", "1")
    monkeypatch.setenv("AUTOHARNESS_REFLECT_EVERY_N", "20")
    monkeypatch.setenv("AUTOHARNESS_CONSOLIDATE_EVERY_N", "100")

    assert get_disable_global() is True
    assert get_reflect_every_n() == 20
    assert get_consolidate_every_n() == 100


def test_resolve_project_root(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AUTOHARNESS_PROJECT_ROOT", raising=False)
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    (tmp_path / ".git").mkdir()

    resolved = resolve_project_root(cwd=sub)
    assert resolved == tmp_path
