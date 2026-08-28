from __future__ import annotations

__all__ = ["main", "mcp"]


def __getattr__(name: str):
    if name in ("main", "mcp"):
        from buddhi.mcp.server import main, mcp

        return {"main": main, "mcp": mcp}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
