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

<p align="center">
   <img src="https://raw.githubusercontent.com/Buddhilive/buddhi-cli/refs/heads/main/public/icons/icon-128x128.png" alt="BuddhiAI Logo" />
</p>

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
- Add separate, dynamic agent workspace rule files inside `.agent/rules/`.
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
| `buddhi init` | Configures `.agent/rules/` rule files, `.agent/mcp_config.json`, and indexes the codebase. |
| `buddhi update` | Explicitly scans the workspace and updates the CodeGraph database. |
| `buddhi live` | Launches the FastAPI server and Streamlit chat UI concurrently. |
| `buddhi server` | Launches the FastAPI backend server only (no Streamlit UI). |
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

5. **`update_codegraph`**
   - Rebuilds and updates the SQLite symbol and call dependency database.
   - *Use case:* Call this tool immediately after every successful code change or implementation to keep the symbol graph fully up to date.

6. **`index_codebase`**
   - Re-builds/syncs the SQLite symbol and call dependency database.
   - *Use case:* Run at startup or after major edits to ensure symbol synchronization.

7. **`buddhi_run_command`**
   - Executes local terminal commands and utilizes local Gemma models to summarize and format stdout/stderr into token-saving JSON.
   - *Use case:* Compile, build, and test execution analysis.

8. **`buddhi_grep_search`**
   - Performs a token-efficient, regex-based text search over files in the workspace with AST tag enrichment.
   - *Use case:* Search for arbitrary strings or constants with AST boundaries tagged.

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

## PyPI Publishing Workflow

Buddhi utilizes a secure, modern, and verified PyPI publishing pipeline with support for both guided local releasing and automated GitHub Actions CI/CD releases.

### 1. Release Environment Setup

Release and validation tools (`twine` and `build`) are defined under the `dev` dependency group in `pyproject.toml`. To synchronize your environment and install these tools:

```bash
uv sync
```

---

### 2. Local Guided Releases

We provide an interactive, colorized publishing script `scripts/publish.py` to securely package and upload the codebase. The script automatically handles directory cleaning, standard PEP-517 packaging using the `build` module, metadata validation via `twine check`, and guides you through uploading.

To run a secure, verified **dry-run** build (highly recommended before releasing):
```bash
uv run python scripts/publish.py --dry-run
```

To upload the package to **TestPyPI** to staging/verification:
```bash
uv run python scripts/publish.py --test-pypi
```

To publish the package to **production PyPI**:
```bash
uv run python scripts/publish.py
```

#### Publisher Command Arguments:
* `--dry-run`: Cleans, builds, and runs `twine check` validation but skips PyPI upload.
* `--test-pypi`: Uploads package archives to TestPyPI (`https://test.pypi.org/`) instead of production.
* `--skip-build`: Skips cleaning and building; directly uploads the existing archives in `dist/`.

> [!TIP]
> **Authentication Recommendation:** When uploading, use PyPI API Tokens for authentication. Set username to `__token__` and password to your token string (starting with `pypi-`).

---

### 3. Automated CI/CD Releases

Automated publishing is handled securely via GitHub Actions using **OIDC Trusted Publishers** (zero-token authentication setup). 

Whenever you are ready to publish a new release:
1. Update the version field manually in `pyproject.toml` (e.g., `version = "1.0.0"`).
2. Commit and tag the release in git:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```
3. The GitHub Actions release workflow will automatically trigger, build the distributions, run metadata checks, and publish securely to PyPI under Trusted Publisher rules.

