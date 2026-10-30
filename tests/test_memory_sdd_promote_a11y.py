from __future__ import annotations

from pathlib import Path

from buddhi.memory.sdd_promote import extract_a11y_decisions, promote_sdd_artifacts


def test_extract_a11y_decisions(tmp_path: Path) -> None:
    doc = tmp_path / "A11Y-DECISIONS.md"
    doc.write_text(
        """# Decisions
- **Destructive confirmation modal** → `role="alertdialog"`, initial focus on cancel. (2026-10-20)
- **Unstyled list** → `<ul role="list">` — Safari drops list semantics under list-style: none (gate: `aria-soup` · `role="list"`). (2026-10-21)
- **Skip Example** → example — replace with your project's first real decision (2026-10-01)
""",
        encoding="utf-8",
    )

    entries = extract_a11y_decisions(doc)
    assert len(entries) == 2
    assert entries[0][0] == "Destructive confirmation modal"
    assert "alertdialog" in entries[0][1]
    assert entries[0][2] == "2026-10-20"
    assert entries[1][0] == "Unstyled list"
    assert "Safari drops" in entries[1][1]


def test_promote_sdd_artifacts_with_a11y(tmp_path: Path) -> None:
    branch = "feature-ui"
    spec_dir = tmp_path / ".buddhi" / "specs" / branch
    spec_dir.mkdir(parents=True, exist_ok=True)

    (spec_dir / "spec.md").write_text(
        "# Feature Specification: UI Revamp\n\nSpec content", encoding="utf-8"
    )
    (spec_dir / "A11Y-DECISIONS.md").write_text(
        '- **Custom Dropdown** → `role="combobox"` with popup listbox. (2026-10-25)\n',
        encoding="utf-8",
    )

    res = promote_sdd_artifacts(workspace_root=tmp_path, branch=branch)
    assert res.spec_branch == branch
    # Should promote spec.md + A11Y decision
    node_ids = [n.frontmatter.id for n in res.promoted_nodes]
    assert "mem-sdd-ui-revamp" in node_ids
    assert "mem-decision-a11y-custom-dropdown" in node_ids
