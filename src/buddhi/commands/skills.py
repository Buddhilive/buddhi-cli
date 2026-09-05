from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from buddhi.skills.installer import install_skill
from buddhi.skills.registry import get_skill, list_skills
from buddhi.util.fsutil import BuddhiFsError

console = Console()
err_console = Console(stderr=True)

skills_app = typer.Typer(
    name="skills",
    help="Manage and execute custom agent skills.",
    invoke_without_command=True,
    no_args_is_help=False,
)


def _render_skills_table() -> None:
    """Print formatted table of all registered custom skills."""
    skills = list_skills()
    table = Table(
        title="Available Custom Agent Skills",
        show_header=True,
        header_style="bold cyan",
        box=None,
    )
    table.add_column("Skill", style="bold green")
    table.add_column("CLI Flag", style="bold yellow")
    table.add_column("Description", style="white")

    for s in skills:
        table.add_row(s.name, s.flag, s.description)

    console.print(table)
    console.print(
        "\n[dim]To install a skill, run: [bold]buddhi skills <flag>[/bold] "
        "(e.g., [bold cyan]buddhi skills --repo-to-skill[/bold cyan])[/dim]"
    )


@skills_app.callback(invoke_without_command=True)
def skills_main(
    ctx: typer.Context,
    repo_to_skill: bool = typer.Option(
        False,
        "--repo-to-skill",
        help="Add the Antigravity-optimized repo-to-skill agent skill.",
    ),
    path: Path = typer.Option(  # noqa: B008
        Path("."),
        "-p",
        "--path",
        help="Target project root directory.",
    ),

    force: bool = typer.Option(
        False,
        "-f",
        "--force",
        help="Overwrite existing skill files if already present.",
    ),
) -> None:
    """Manage custom agent skills for Google Antigravity harnesses."""
    if ctx.invoked_subcommand is not None:
        return

    # Check if any skill install flag was passed
    install_targets: list[str] = []
    if repo_to_skill:
        install_targets.append("repo-to-skill")

    # If no flags passed, list all available custom skills
    if not install_targets:
        _render_skills_table()
        return

    target_root = path.resolve()
    for skill_name in install_targets:
        entry = get_skill(skill_name)
        if entry is None:
            err_console.print(f"[red]error:[/red] unknown skill: '{skill_name}'")
            raise typer.Exit(code=1)

        try:
            report = install_skill(entry, target_root, force=force)
        except BuddhiFsError as exc:
            err_console.print(f"[red]error:[/red] {exc}")
            raise typer.Exit(code=1) from exc

        if report.skipped:
            console.print(
                f"[yellow]warning:[/yellow] skill '{entry.name}' already exists at {report.target_dir}. "
                "Skipping. Use [bold]--force[/bold] to overwrite."
            )
        else:
            action_desc = "updated" if report.overwritten else "added"
            console.print(
                f"[bold green]done[/bold green] {action_desc} skill [cyan]{entry.name}[/cyan] "
                f"at {report.target_dir}"
            )
            for f in report.created:
                console.print(f"  wrote: {f}")


@skills_app.command(name="run", help="Run a registered skill script.")
def run_skill(
    skill_name: str = typer.Argument(..., help="Name of the skill (e.g. 'repo-to-skill')."),
    target: str = typer.Argument(..., help="Target repository path or URL."),
    json_mode: bool = typer.Option(False, "--json", help="Emit structured output in JSON format."),
) -> None:
    """Execute helper scripts associated with a custom agent skill."""
    entry = get_skill(skill_name)
    if entry is None:
        err_console.print(f"[red]error:[/red] unknown skill: '{skill_name}'")
        raise typer.Exit(code=1)

    try:
        exit_code = entry.execute_runner(target, json_mode=json_mode)
        if exit_code != 0:
            raise typer.Exit(code=exit_code)
    except Exception as exc:
        err_console.print(f"[red]error:[/red] execution failed for skill '{skill_name}': {exc}")
        raise typer.Exit(code=1) from exc
