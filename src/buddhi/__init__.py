from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("buddhi-ai")
except PackageNotFoundError:
    try:
        __version__ = version("buddhi")
    except PackageNotFoundError:
        __version__ = "1.0.0"

from buddhi.cli import main

__all__ = ["__version__", "main"]
