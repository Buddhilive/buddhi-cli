# BuddhiAI Server Backend

FastAPI backend for BuddhiAI.

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv)

### Installation

```bash
uv sync
```

### Running the Project

You can run the project using `uv run` in several ways:

#### 1. Using Uvicorn directly (Recommended for Development)

```bash
uv run uvicorn src.main:app --reload
```

#### 2. Running the main script

```bash
uv run python src/main.py
```

## Project Structure

- `src/main.py`: Entry point for the FastAPI application.
- `pyproject.toml`: Project configuration and dependencies.
- `.env`: Environment variables (copy from `.env.example` if available).
