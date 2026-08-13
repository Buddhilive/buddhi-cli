from pathlib import Path

from buddhi.util.fsutil import ensure_buddhi_dirs


def test_creates_buddhi_and_graphs_dirs(tmp_path: Path) -> None:
    graphs_dir = ensure_buddhi_dirs(tmp_path)

    assert (tmp_path / ".buddhi").is_dir()
    assert graphs_dir == tmp_path / ".buddhi" / "graphs"
    assert graphs_dir.is_dir()


def test_creates_gitignore_with_graphs_content(tmp_path: Path) -> None:
    ensure_buddhi_dirs(tmp_path)

    gitignore = tmp_path / ".buddhi" / ".gitignore"
    assert gitignore.read_text(encoding="utf-8") == "graphs/\n"


def test_does_not_overwrite_existing_gitignore(tmp_path: Path) -> None:
    buddhi_dir = tmp_path / ".buddhi"
    buddhi_dir.mkdir()
    gitignore = buddhi_dir / ".gitignore"
    gitignore.write_text("custom content\n", encoding="utf-8")

    ensure_buddhi_dirs(tmp_path)

    assert gitignore.read_text(encoding="utf-8") == "custom content\n"


def test_idempotent_on_rerun(tmp_path: Path) -> None:
    ensure_buddhi_dirs(tmp_path)
    ensure_buddhi_dirs(tmp_path)  # should not raise

    assert (tmp_path / ".buddhi" / "graphs").is_dir()
