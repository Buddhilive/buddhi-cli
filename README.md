# Buddhi AI CLI

<p align="center">
<a href="https://pypi.org/project/buddhi-ai/">
    <img src="https://img.shields.io/pypi/v/buddhi-ai?style=flat-square&logo=pypi" alt="PyPI Version" />
  </a>
  <a href="https://pypi.org/project/buddhi-ai/">
    <img src="https://img.shields.io/pypi/dm/buddhi-ai?style=flat-square" alt="PyPI Downloads" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/github/license/Buddhilive/buddhi-cli?style=flat-square" alt="License" />
  </a>
  <img src="https://img.shields.io/badge/MCP-Compatible-green?style=flat-square" alt="MCP Compatible" />
</p>

Buddhi AI CLI (`buddhi-ai`) is a powerful command-line tool designed to map structural entities and filter boilerplate in your codebase. Built on top of AST parsing (Tree-sitter) and graph analysis (igraph), Buddhi AI creates a topology-driven retrieval pipeline. It also seamlessly integrates with the Model Context Protocol (MCP) to provide intelligent code search, reading, and shell execution capabilities for AI agents.

## Key Features

- **Structural Code Mapping**: Uses Tree-sitter to parse source code into an Abstract Syntax Tree (AST) and maps it into a graph database (SQLite).
- **Boilerplate Filtering**: Employs Shannon entropy thresholds to filter out boilerplate lines and highlight critical code paths.
- **Topology-Driven Search**: Community-aware search that traverses neighborhoods and includes bridge nodes instead of standard keyword-only retrieval.
- **Dynamic File Reading**: Reads files using dynamic compression, AST pruning, and bounce prevention logic to prevent prompt thrashing.
- **Compressed Shell Execution**: Executes shell commands and returns compressed, token-efficient output (with noise eradication and structural deduplication).
- **MCP Integration**: Fully exposes search, read, and shell tools via the FastMCP server.

## Architecture & Tech Stack

- **Python 3.10+**: Core language.
- **Tree-sitter**: Used for parsing various programming languages into ASTs.
- **igraph**: Handles complex graph-based topological searches and structural abstraction.
- **FastMCP**: Provides the Model Context Protocol server interface.
- **uv**: Dependency management and build backend.

## Prerequisites

- **Python**: 3.10 or higher.
- (Recommended) **uv**: For fast Python package resolution and virtual environment management.

## Installation

### From Source (Using `uv`)

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd buddhi-cli
   ```

2. Sync dependencies using `uv` (or install via `pip`):
   ```bash
   uv sync
   ```

3. Activate the virtual environment:
   ```bash
   source .venv/bin/activate
   ```
   *(On Windows, use `.venv\Scripts\activate`)*

### From Source (Using `pip`)

Alternatively, install it in editable mode:
```bash
pip install -e .
```

---

## Usage

### 1. The `buddhi` CLI

Before using the tools, you need to initialize the project directory and scan the codebase.

```bash
buddhi init [OPTIONS]
```

**Options:**
- `--entropy-threshold <FLOAT>`: Shannon entropy threshold for filtering boilerplate lines. Default is `3.0`.

This will parse your workspace and create the Buddhi graph database at `.buddhi/graph.db`.

### 2. The MCP Server (`buddhi-mcp`)

Start the FastMCP server over standard input/output (StdIO):

```bash
buddhi-mcp [OPTIONS]
```

**Options:**
- `--db-path <PATH>`: Explicit path to the `.buddhi/graph.db` database. Overrides the auto-detection traversing upwards from the current working directory.

#### Available MCP Tools

Once the server is running, the following tools are exposed via the Model Context Protocol:

- **`buddhi_search(query, top_n=3, mode="full", include_bridges=True, budget=8000)`**
  Search the codebase using Buddhi's topology-driven retrieval. Replace keyword-only searches with community-aware context-optimized results.

- **`buddhi_read(filepath, mode="auto", task_intent=None, budget=4000)`**
  Read a file with dynamic compression, AST pruning, and bounce prevention. Mode options include `'auto'`, `'full'`, `'signatures'`, `'map'`, or `'entropy'`.

- **`buddhi_shell(command, timeout=60, budget=8000, raw=False, cwd=None)`**
  Execute a shell command and return compressed, token-efficient output through a 4-phase pipeline (noise eradication, domain abstraction, deduplication, and Compact Response Protocol).

## Development & Contributing

- **Linting & Formatting**: Handled via `ruff` and `mypy` (defined in `pyproject.toml` dependency groups).
- **Testing**: Handled via `pytest`.

To run tests:
```bash
pytest tests/
```

### Testing the CLI Locally

To test the CLI tool locally as if it were in production without publishing to PyPI:

**Option 1: Global Installation (Recommended)**
Install the built `.whl` file globally using `uv tool install`:
```bash
uv build
uv tool install dist/buddhi_ai-<version>-py3-none-any.whl --force
```
To uninstall later:
```bash
uv tool uninstall buddhi-ai
```

**Option 2: Editable Mode**
For active development, install the tool in editable mode so changes to the source code are reflected immediately:
```bash
uv tool install -e .
```
To uninstall:
```bash
uv tool uninstall buddhi-ai
```
