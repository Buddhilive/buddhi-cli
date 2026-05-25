# Buddhi AI

Buddhi AI is a local AI inference server, interactive web interface, and Model Context Protocol (MCP) server designed to supercharge developer workspaces.

The backend is powered by FastAPI and LiteRT-LM, providing an ultra-fast, OpenAI-compatible local API endpoint. The frontend is built with Streamlit. Additionally, Buddhi integrates a highly-optimized MCP server (`CodeGraph`) that compiles your codebase into an AST & call-graph SQLite database for token-saving workspace exploration and command execution.

## Tech Stack

- **Backend:** Python, FastAPI, LiteRT-LM, Uvicorn
- **Frontend:** Streamlit
- **Code Graph & MCP:** SQLite, FastMCP (StdIO transport)
- **Package Management:** `uv` (Python)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**: Recommended to use [uv](https://github.com/astral-sh/uv) for fast, reliable dependency management.

---

## Setup & Quick Start

### 1. Backend Setup

Clone the repository and install all dependencies:

```bash
uv sync
```

### 2. Download the Model

Buddhi AI downloads models locally to the user's home directory (`~/.buddhi/models/`) to preserve space and enable shared reuse. Run the setup command:

```bash
# Downloads the gemma-4-E4B-it.litertlm model from HuggingFace
buddhi setup
```

### 3. Initialize the Workspace (MCP Server Integration)

Configure your active development environment (such as Cursor or Antigravity) to use the Buddhi MCP server by initializing the workspace:

```bash
buddhi init
```

This command will:
- Add dynamic agent workspace instruction block to `AGENTS.md`.
- Create or update `.agent/mcp_config.json` registering `buddhi-mcp`.
- Re-index your codebase AST structures and call graph automatically into SQLite.

### 4. Start the Server and UI

To run both the backend server and Streamlit interface concurrently:

```bash
buddhi live
```

- **Inference API endpoint:** `http://127.0.0.1:58421/v1`
- **Health check:** `http://127.0.0.1:58421/health`
- **Streamlit UI:** `http://127.0.0.1:58422`

---

## CLI Reference

Buddhi provides a CLI command suite:

| Command | Description |
|---------|-------------|
| `buddhi setup` | Downloads the local edge inference model. |
| `buddhi init` | Configures `AGENTS.md` and `.agent/mcp_config.json` and indexes the codebase. |
| `buddhi live` | Launches the FastAPI server and Streamlit chat UI concurrently. |
| `buddhi mcp` | Starts the FastMCP server over StdIO transport. |

---

## CodeGraph MCP Tools

The `buddhi mcp` server exposes highly optimized tools that save context tokens during AI agent interactions:

1. **`get_codebase_summary`**
   - Retrieves all classes, files, and main modules grouped by functional community clusters.
   - *Use case:* Faster high-level codebase understanding upon startup.

2. **`find_relevant_symbols`**
   - Performs exact semantic search (FTS5 SQLite search) over symbol names and AST docstrings.
   - *Use case:* Pinpoint specific functions/classes without messy, line-by-line grep output.

3. **`get_symbol_implementation`**
   - Retrieves exact source code for a symbol with a built-in guardrail: if the implementation exceeds 150 lines, it returns only the signature, docstring, and method outlines to prevent context window blowout.
   - *Use case:* Safely inspect class or method implementations.

4. **`trace_impact_radius`**
   - Recursively traces upstream call graph chains up to 3 levels deep starting at a specific symbol.
   - *Use case:* Identify the blast-radius before modifying/refactoring code.

5. **`index_codebase`**
   - Re-builds/syncs the SQLite symbol and call dependency database.
   - *Use case:* Run after making significant modifications to files.

6. **`execute_command_optimized`**
   - Executes local terminal commands and utilizes local Gemma models to summarize and format stdout/stderr into token-saving JSON.
   - *Use case:* Compile, build, and test execution analysis.

---

## Development Workflow

### Backend & CLI

- **Main Server Entry:** `server/main.py`
- **API Routes:** `server/api/routes/`
- **CLI Entry:** `cli/main.py`
- **MCP Server Entry:** `mcp/server.py`

### Frontend

- **Main App:** `ui/app.py`

---

## PyPI Publishing

To build and publish the `buddhi` CLI tool to PyPI:

1. **Build the package:**
   ```bash
   uv build
   ```

2. **Publish to PyPI:**
   ```bash
   uv publish
   ```
