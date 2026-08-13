import typer

from buddhi.commands.generate import generate

app = typer.Typer(help="buddhi - tree-sitter code graph generator.")
app.command(name="generate")(generate)


@app.callback()
def _root_callback() -> None:
    """buddhi - tree-sitter code graph generator."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
