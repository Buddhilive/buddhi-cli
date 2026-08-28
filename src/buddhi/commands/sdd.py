from __future__ import annotations

import sys

import typer

from buddhi.sdd.check_prerequisites import main as check_main
from buddhi.sdd.create_new_feature import main as create_main
from buddhi.sdd.resolve_template import main as resolve_template_main
from buddhi.sdd.setup_plan import main as setup_plan_main
from buddhi.sdd.setup_tasks import main as setup_tasks_main

sdd_app = typer.Typer(
    help="Spec-Driven Development (SDD) scripts and prerequisite checks.",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)


def _forward_args(ctx: typer.Context, command_name: str) -> list[str]:
    """Extract arguments passed to the specific subcommand from ctx.args or sys.argv."""
    if ctx.args:
        return list(ctx.args)
    argv = sys.argv[1:]
    try:
        idx = argv.index(command_name)
        return argv[idx + 1 :]
    except ValueError:
        return []


@sdd_app.command(
    name="create",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="Create a new feature directory, branch, and spec.md from template.",
)
def create(ctx: typer.Context) -> None:
    args = _forward_args(ctx, "create")
    exit_code = create_main(args)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@sdd_app.command(
    name="setup-plan",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="Set up plan.md for the active feature from the plan template.",
)
def setup_plan(ctx: typer.Context) -> None:
    args = _forward_args(ctx, "setup-plan")
    exit_code = setup_plan_main(args)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@sdd_app.command(
    name="setup-tasks",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="Check prerequisites and resolve template for tasks.md.",
)
def setup_tasks(ctx: typer.Context) -> None:
    args = _forward_args(ctx, "setup-tasks")
    exit_code = setup_tasks_main(args)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@sdd_app.command(
    name="check",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="Consolidated prerequisite checking for SDD feature workflows.",
)
def check(ctx: typer.Context) -> None:
    args = _forward_args(ctx, "check")
    exit_code = check_main(args)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@sdd_app.command(
    name="resolve-template",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
    help="Resolve and compose template content from the project template stack.",
)
def resolve_template_cmd(ctx: typer.Context) -> None:
    args = _forward_args(ctx, "resolve-template")
    exit_code = resolve_template_main(args)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)
