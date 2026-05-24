# Buddhi AI

Buddhi AI is an AI inference server and web interface. The backend is powered by FastAPI and LiteRT-LM, providing an OpenAI-compatible API. The frontend is built with Streamlit.

## Tech Stack

- **Backend:** Python, FastAPI, LiteRT-LM, Uvicorn
- **Frontend:** Streamlit
- **Package Management:** `uv` (Python)

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+**: Recommended to use [uv](https://github.com/astral-sh/uv) for dependency management.

## Setup & Quick Start

### 1. Backend Setup

The backend uses `uv` for managing dependencies.

```bash
# Clone the repository and navigate to the project directory
# Install dependencies and the CLI tool using uv
uv sync
```

### 2. Download the Model

The project includes a custom CLI tool, `buddhi`, to manage the server and models. First, download the required model:

```bash
# Downloads the gemma-4-E4B-it.litertlm model from HuggingFace
buddhi setup
```

### 3. Start the Server and UI

```bash
# Starts the backend server and Streamlit UI concurrently
buddhi live
```

- API endpoint: `http://127.0.0.1:58421/v1`
- Health check: `http://127.0.0.1:58421/health`
- Streamlit UI: `http://127.0.0.1:58422`

## Development Workflow

### Backend

The backend code is located in the `server/` directory, while the CLI logic is in the `cli/` directory.

- **Main Server Entry:** `server/main.py`
- **API Routes:** `server/api/routes/`
- **CLI Entry:** `cli/main.py`

When adding new dependencies to the backend, use `uv`:
```bash
uv add <package_name>
```

### Frontend

The frontend is a Streamlit application located in the `ui/` directory.

- **Main App:** `ui/app.py`

## PyPI Publishing

To build and publish this CLI tool to PyPI:

1. **Build the package:**
   ```bash
   uv build
   ```

2. **Publish to PyPI:**
   ```bash
   uv publish
   ```
