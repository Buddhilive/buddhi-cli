from __future__ import annotations

from buddhi.scripts.autoharness.lifecycle import evaluate_lifecycle
from buddhi.scripts.autoharness.models import SidecarData


def test_probation_retention() -> None:
    # Skill tenure < 100 -> must keep in probation
    skills = {"new-skill": SidecarData(created_by="agent", use=0, view=0, anchor=50)}
    decision = evaluate_lifecycle(skills, current_request_count=100, maturity_limit=100)
    assert "new-skill" in decision.keep
    assert len(decision.archive) == 0


def test_graduation_archive_when_zero_usage() -> None:
    # Skill tenure >= 100 with use=0 and view=0 -> must archive
    skills = {"stale-skill": SidecarData(created_by="agent", use=0, view=0, anchor=0)}
    decision = evaluate_lifecycle(skills, current_request_count=150, maturity_limit=100)
    assert "stale-skill" in decision.archive
    assert len(decision.keep) == 0


def test_graduation_retention_when_used() -> None:
    # Skill tenure >= 100 with use > 0 -> must keep
    skills = {"active-skill": SidecarData(created_by="agent", use=5, view=2, anchor=0)}
    decision = evaluate_lifecycle(skills, current_request_count=150, maturity_limit=100)
    assert "active-skill" in decision.keep
    assert len(decision.archive) == 0


def test_capacity_eviction_lowest_rate() -> None:
    # 3 active skills with capacity limit 2 -> lowest usage rate gets evicted
    skills = {
        "high-use": SidecarData(created_by="agent", use=10, anchor=0),
        "mid-use": SidecarData(created_by="agent", use=5, anchor=0),
        "low-use": SidecarData(created_by="agent", use=1, anchor=0),
    }
    decision = evaluate_lifecycle(
        skills, current_request_count=100, maturity_limit=50, capacity_limit=2
    )
    assert "low-use" in decision.archive
    assert "high-use" in decision.keep
    assert "mid-use" in decision.keep
