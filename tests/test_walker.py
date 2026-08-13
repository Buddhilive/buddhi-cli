from pathlib import Path

from buddhi.discovery.walker import walk


def test_walk_detects_language_by_extension(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.txt").write_text("not code\n")

    result = walk(tmp_path)

    rel_paths = {f.rel_path for f in result.files}
    assert rel_paths == {"a.py"}
    assert result.files[0].language == "python"


def test_walk_excludes_default_dirs(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "dep.py").write_text("x = 1\n")
    (tmp_path / "real.py").write_text("y = 2\n")

    result = walk(tmp_path)

    rel_paths = {f.rel_path for f in result.files}
    assert rel_paths == {"real.py"}


def test_walk_respects_gitignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("ignored/\n")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "skip.py").write_text("x = 1\n")
    (tmp_path / "keep.py").write_text("y = 2\n")

    result = walk(tmp_path)

    rel_paths = {f.rel_path for f in result.files}
    assert rel_paths == {"keep.py"}


def test_walk_skips_large_files(tmp_path: Path) -> None:
    big = tmp_path / "big.py"
    big.write_text("x = 1\n" * 100)

    result = walk(tmp_path, max_file_size=10)

    assert result.files == []
    assert result.skipped_too_large == ["big.py"]


def test_walk_counts_unsupported_grammar(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("x = 1\n")
    (tmp_path / "b.py").write_text("y = 2\n")

    result = walk(tmp_path, available_languages=set())

    assert result.files == []
    assert result.skipped_unsupported_grammar == {"python": 2}


def test_walk_on_empty_project(tmp_path: Path) -> None:
    result = walk(tmp_path)
    assert result.files == []
    assert result.directories == set()
