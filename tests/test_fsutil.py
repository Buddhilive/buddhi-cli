from pathlib import Path

from buddhi.util.fsutil import ensure_buddhi_dirs, sync_template_tree


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


def test_sync_template_tree_copies_non_md_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Create non-.md files
    (src_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")
    (src_dir / "script.py").write_text("print('hello')", encoding="utf-8")

    report = sync_template_tree(src_dir, dest_dir)

    # Check that non-.md files were copied
    assert (dest_dir / "config.json").exists()
    assert (dest_dir / "script.py").exists()
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == '{"key": "value"}'
    assert (dest_dir / "script.py").read_text(encoding="utf-8") == "print('hello')"
    assert len(report.created) == 2
    assert len(report.kept_existing) == 0


def test_sync_template_tree_copies_both_md_and_non_md_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Create both .md and non-.md files
    (src_dir / "readme.md").write_text("# README", encoding="utf-8")
    (src_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")
    (src_dir / "script.py").write_text("print('hello')", encoding="utf-8")

    report = sync_template_tree(src_dir, dest_dir)

    # Check that all files were copied
    assert (dest_dir / "readme.md").exists()
    assert (dest_dir / "config.json").exists()
    assert (dest_dir / "script.py").exists()
    assert (dest_dir / "readme.md").read_text(encoding="utf-8") == "# README"
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == '{"key": "value"}'
    assert (dest_dir / "script.py").read_text(encoding="utf-8") == "print('hello')"
    assert len(report.created) == 3
    assert len(report.kept_existing) == 0


def test_sync_template_tree_preserves_existing_non_md_files(tmp_path: Path) -> None:
    src_dir = tmp_path / "src"
    dest_dir = tmp_path / "dest"
    src_dir.mkdir()
    dest_dir.mkdir()

    # Pre-create a destination file with custom content
    (dest_dir / "config.json").write_text("custom content", encoding="utf-8")

    # Create the same file in source with different content
    (src_dir / "config.json").write_text('{"key": "value"}', encoding="utf-8")

    report = sync_template_tree(src_dir, dest_dir)

    # Check that the existing file was preserved and not overwritten
    assert (dest_dir / "config.json").read_text(encoding="utf-8") == "custom content"
    assert len(report.created) == 0
    assert len(report.kept_existing) == 1
    assert (dest_dir / "config.json") in report.kept_existing
