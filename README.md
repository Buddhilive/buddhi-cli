# Buddhi AI Server

A starter Python CLI app using [Textual](https://textual.textualize.io/) and [uv](https://github.com/astral-sh/uv).

## Getting Started

### Prerequisites

You need `uv` installed. If you don't have it, install it via:

On Windows:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

On Linux/macOS:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

Initialize the project dependencies using `uv`:

```bash
uv sync
```

### Running the App

You can run the application directly using `uv`:

```bash
uv run buddhi-ai
```

### Development

To run the textual app with developer tools and live reload enabled:

```bash
uv run textual run --dev src/buddhi_ai_server/app.py
```

## Publishing to PyPI

This project is configured to be easily publishable. First, build the package using `uv build`:

```bash
uv build
```

Then, you can publish the built wheels to PyPI:

```bash
uv publish
```
