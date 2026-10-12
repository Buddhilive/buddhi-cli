from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

MODES: list[str] = ["during", "after", "ask"]


def resolve_settings_path(
    platform: str | None = None,
    env: dict[str, str] | None = None,
    home: str | None = None,
) -> Path:
    plt = platform or sys.platform
    environ = os.environ if env is None else env
    user_home = Path.home() if home is None else Path(home)

    if plt == "win32":
        appdata = environ.get("APPDATA")
        base = Path(appdata) if appdata else user_home / ".config"
    else:
        base = user_home / ".config"
    return base / "antislop" / "settings.json"


settings_path: Path = resolve_settings_path()


def read_settings(file: Path | None = None) -> dict[str, Any]:
    target = file if file is not None else settings_path
    if not target.exists():
        return {}
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Cannot read {target}: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError(f"Expected a JSON object in {target}")  # noqa: TRY004
    return data


def configure_mode(mode: str | None = None, file: Path | None = None) -> str:
    target = file if file is not None else settings_path
    if mode is not None and mode not in MODES:
        raise ValueError(f"Invalid mode in {target}. Set --mode during, after, or ask.")

    try:
        settings = read_settings(target)
    except ValueError as exc:
        raise ValueError(f"{exc} Fix or delete it to start over.") from exc

    if mode is not None:
        settings["mode"] = mode
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")

    resolved_mode = settings.get("mode") or "ask"
    if resolved_mode not in MODES:
        raise ValueError(f"Invalid mode in {target}. Set --mode during, after, or ask.")

    default_indicator = " (default)" if "mode" not in settings else ""
    return f"antislop global mode: {resolved_mode}{default_indicator}\n{target}"
