import typer

from buddhi.commands.docs import docs_app
from buddhi.commands.generate import generate
from buddhi.commands.init import init
from buddhi.commands.sdd import sdd_app

app = typer.Typer(help="buddhi - tree-sitter code graph generator.")
app.command(name="generate")(generate)
app.command(name="init")(init)
app.add_typer(docs_app, name="docs")
app.add_typer(sdd_app, name="sdd")


@app.callback()
def _root_callback() -> None:
    """buddhi - tree-sitter code graph generator."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
