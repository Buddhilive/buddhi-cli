#!/usr/bin/env python3
"""Cross-platform repository analyzer for repo-to-skill generator.

Usage:
    python analyze_repo.py <target_path_or_url> [--json]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# If run within buddhi environment, import from buddhi; otherwise run self-contained fallback
try:
    from buddhi.skills.repo_to_skill import run_repo_to_skill
except ImportError:
    # Minimal fallback self-contained execution
    import json
    import re

    def run_repo_to_skill(target: str, json_mode: bool = False) -> int:
        p = Path(target).resolve()
        if not p.is_dir():
            print(f"Error: {p} is not a directory", file=sys.stderr)
            return 1
        readme = p / "README.md"
        title = p.name
        desc = ""
        if readme.is_file():
            txt = readme.read_text(encoding="utf-8", errors="replace")
            m = re.search(r"^#\s+(.+)$", txt, re.MULTILINE)
            if m:
                title = m.group(1)
            desc = txt[:200]
        data = {
            "name": p.name,
            "title": title,
            "description": desc,
            "is_cli": (p / "cli.py").is_file() or (p / "pyproject.toml").is_file(),
        }
        print(json.dumps(data, indent=2))
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze a repository for agent skill generation.")
    parser.add_argument("target", help="Local directory path or git clone URL")
    parser.add_argument("--json", action="store_true", help="Output analysis in JSON format")
    args = parser.parse_args()

    exit_code = run_repo_to_skill(args.target, json_mode=args.json)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
