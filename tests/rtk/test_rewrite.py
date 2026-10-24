from __future__ import annotations

from buddhi.scripts.rtk.rewrite import evaluate_rewrite


def test_rewrite_simple_git_status() -> None:
    decision = evaluate_rewrite("git status")
    assert decision.action == "rewrite"
    assert "buddhi scripts rtk run -- git status" in decision.rewritten_command


def test_rewrite_pytest_command() -> None:
    decision = evaluate_rewrite("pytest tests/ -v")
    assert decision.action == "rewrite"
    assert "buddhi scripts rtk run --" in decision.rewritten_command


def test_skip_already_wrapped_command() -> None:
    decision = evaluate_rewrite("buddhi scripts rtk run -- git status")
    assert decision.action == "skip"
    assert decision.reason == "already_wrapped"


def test_skip_compound_commands() -> None:
    # Pipes
    d1 = evaluate_rewrite("git status | grep modified")
    assert d1.action == "skip"
    assert d1.reason == "compound_or_pipe"

    # Redirections
    d2 = evaluate_rewrite("pytest > output.txt")
    assert d2.action == "skip"
    assert d2.reason == "compound_or_pipe"

    # And/Or chains
    d3 = evaluate_rewrite("git add . && git commit -m 'fix'")
    assert d3.action == "skip"
    assert d3.reason == "compound_or_pipe"


def test_skip_unmatched_quiet_command() -> None:
    # Commands like mkdir, cd, mv don't produce verbose token-consuming output
    decision = evaluate_rewrite("mkdir new_folder")
    assert decision.action == "skip"
    assert decision.reason == "no_rewrite_candidate"
