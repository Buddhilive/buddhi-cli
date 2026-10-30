from pathlib import Path

from buddhi.memory.migrate import migrate_legacy_memory


def test_migrate_legacy_memory(tmp_path: Path) -> None:
    memory_dir = tmp_path / ".agents" / "memory"
    memory_dir.mkdir(parents=True)

    # Legacy project conventions file with real entries and boilerplate
    (memory_dir / "project-conventions.md").write_text(
        "# Project Conventions\n\n"
        "No entries yet. Durable project conventions discovered while working here.\n\n"
        "- Always use forward slashes for cross-platform paths.\n"
        "- Never use bare except clauses.\n",
        encoding="utf-8",
    )

    # Legacy tech decisions file
    (memory_dir / "tech-decisions.md").write_text(
        "# Tech Decisions\n\n1. Adopt SQLite WAL mode for concurrency.\n",
        encoding="utf-8",
    )

    # Legacy file with only boilerplate
    (memory_dir / "user-preferences.md").write_text(
        "# User Preferences\n\nNo entries yet.\n",
        encoding="utf-8",
    )

    res = migrate_legacy_memory(tmp_path)
    assert res.migrated_count == 3
    assert len(res.backed_up_files) == 3

    # Check files renamed to .bak
    assert (memory_dir / "project-conventions.md.bak").is_file()
    assert (memory_dir / "tech-decisions.md.bak").is_file()
    assert not (memory_dir / "project-conventions.md").is_file()

    # Check OKF concept files created
    conventions_dir = memory_dir / "conventions"
    assert conventions_dir.is_dir()
    created_conventions = list(conventions_dir.glob("*.md"))
    # One index.md plus 2 concept files
    assert len(created_conventions) == 3

    # Check MEMORY.md synced
    memory_md = memory_dir / "MEMORY.md"
    assert memory_md.is_file()
    m_content = memory_md.read_text(encoding="utf-8")
    assert "Always use forward slashes" in m_content
    assert "Adopt SQLite WAL mode" in m_content

    # Idempotency check: rerun should migrate 0 files
    rerun = migrate_legacy_memory(tmp_path)
    assert rerun.migrated_count == 0
