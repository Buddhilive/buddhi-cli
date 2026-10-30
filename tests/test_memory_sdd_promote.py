from pathlib import Path

from buddhi.memory.sdd_promote import promote_sdd_artifacts


def test_promote_sdd_artifacts(tmp_path: Path) -> None:
    specs_dir = tmp_path / ".buddhi" / "specs" / "001-test-feature"
    specs_dir.mkdir(parents=True)

    (specs_dir / "spec.md").write_text(
        "# Feature Specification: User Authentication\n\nDetails...",
        encoding="utf-8",
    )
    (specs_dir / "choices.md").write_text(
        "### [SOUND]: Use Argon2id for Password Hashing\n"
        "Argon2id provides memory-hard security against GPU cracking.\n\n"
        "### [UNSOUND]: Store Plaintext Tokens\n"
        "Rejected because unsafe.\n",
        encoding="utf-8",
    )

    res = promote_sdd_artifacts(tmp_path, branch="001-test-feature")
    assert res.spec_branch == "001-test-feature"
    # Should promote: 1 sound choice + 1 sdd-rationale
    assert len(res.promoted_nodes) == 2

    # Verify decision node created in .agents/memory/decisions/
    decision_file = (
        tmp_path
        / ".agents"
        / "memory"
        / "decisions"
        / "mem-decision-use-argon2id-for-password-hashing.md"
    )
    assert decision_file.is_file()
    assert "Argon2id provides memory-hard security" in decision_file.read_text(
        encoding="utf-8"
    )

    # Verify sdd-rationale node created in .agents/memory/sdd/
    sdd_file = (
        tmp_path / ".agents" / "memory" / "sdd" / "mem-sdd-user-authentication.md"
    )
    assert sdd_file.is_file()
