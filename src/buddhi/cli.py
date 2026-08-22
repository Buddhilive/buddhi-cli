import typer

from buddhi.commands.docs import docs_app
from buddhi.commands.generate import generate
from buddhi.commands.init import init

app = typer.Typer(help="buddhi - tree-sitter code graph generator.")
app.command(name="generate")(generate)
app.command(name="init")(init)
app.add_typer(docs_app, name="docs")


@app.callback()
def _root_callback() -> None:
    """buddhi - tree-sitter code graph generator."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
