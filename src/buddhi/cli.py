import typer

from buddhi.commands.docs import docs_app
from buddhi.commands.generate import generate
from buddhi.commands.graph_cmd import graph_app
from buddhi.commands.init import init
from buddhi.commands.mcp import mcp_cmd
from buddhi.commands.memory import memory_app
from buddhi.commands.scripts import scripts_app
from buddhi.commands.sdd import sdd_app
from buddhi.commands.skills import skills_app

app = typer.Typer(help="buddhi - tree-sitter code graph generator.")
app.command(name="generate")(generate)
app.command(name="init")(init)
app.command(name="mcp")(mcp_cmd)
app.add_typer(docs_app, name="docs")
app.add_typer(graph_app, name="graph")
app.add_typer(memory_app, name="memory")
app.add_typer(scripts_app, name="scripts")
app.add_typer(sdd_app, name="sdd")
app.add_typer(skills_app, name="skills")


@app.callback()
def _root_callback() -> None:
    """buddhi - tree-sitter code graph generator."""


def main() -> None:
    app()


if __name__ == "__main__":
    main()
