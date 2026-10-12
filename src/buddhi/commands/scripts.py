from __future__ import annotations

import typer
from rich.console import Console

from buddhi.scripts.antislop_mode import configure_mode
from buddhi.scripts.contrast import run_contrast_check
from buddhi.scripts.contrast import selftest as contrast_selftest

console = Console()
err_console = Console(stderr=True)

scripts_app = typer.Typer(
    name="scripts",
    help="Utility scripts and tools.",
    invoke_without_command=False,
    no_args_is_help=True,
)


@scripts_app.command(name="contrast")
def contrast(
    color_a: str | None = typer.Argument(
        None, help="First color as hex or named color (black/white)."
    ),
    color_b: str | None = typer.Argument(
        None, help="Second color as hex or named color (black/white)."
    ),
    selftest: bool = typer.Option(
        False, "--selftest", help="Run self-test against the reference table."
    ),
) -> None:
    """Check WCAG 2.x contrast ratio between two colors."""
    if selftest:
        code, msg = contrast_selftest()
        if code == 0:
            console.print(msg)
        else:
            err_console.print(msg)
        raise typer.Exit(code=code)

    if color_a is None or color_b is None:
        err_console.print("usage: buddhi scripts contrast <hex1> <hex2> | --selftest")
        raise typer.Exit(code=2)

    try:
        result = run_contrast_check(color_a, color_b)
    except ValueError as exc:
        err_console.print(f"error: {exc}")
        raise typer.Exit(code=2)

    console.print(result.formatted_text)
    raise typer.Exit(code=result.exit_code)


@scripts_app.command(name="antislop-mode")
def antislop_mode(
    mode: str | None = typer.Argument(
        None, help="Set global antislop mode: 'during', 'after', or 'ask'."
    ),
) -> None:
    """View or configure the global antislop usage mode."""
    try:
        output = configure_mode(mode)
    except ValueError as exc:
        err_console.print(f"error: {exc}")
        raise typer.Exit(code=1)

    console.print(output)
