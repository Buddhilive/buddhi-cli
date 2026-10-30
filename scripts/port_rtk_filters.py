"""Utility script to convert upstream rtk-ai/rtk Apache-2.0 TOML filters to declarative JSON.

Reads from temp/rtk/src/filters/*.toml and writes to src/buddhi/scripts/rtk/builtin_filters/*.json
with full Apache-2.0 attribution and license provenance.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import tomli

UPSTREAM_DIR = Path("temp/rtk/src/filters")
TARGET_DIR = Path("src/buddhi/scripts/rtk/builtin_filters")

CUSTOM_MANAGED_FILTERS = {
    "git-status",
    "git-diff",
    "git-log",
    "pytest",
    "ruff",
    "mypy",
    "uv",
    "npm",
    "cargo",
    "docker",
}


def port_filters() -> int:
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    count = 0

    for toml_path in sorted(UPSTREAM_DIR.glob("*.toml")):
        with open(toml_path, "rb") as f:
            data = tomli.load(f)

        filters_sec = data.get("filters", {})
        tests_sec = data.get("tests", {})

        for filter_name, filter_info in filters_sec.items():
            if not isinstance(filter_info, dict):
                continue

            if filter_name in CUSTOM_MANAGED_FILTERS:
                # Keep customized high-priority core filter definition
                continue

            test_cases = tests_sec.get(filter_name, [])

            match_cmd = filter_info.get("match_command", "")
            strip_lines = filter_info.get("strip_lines_matching", [])
            keep_lines = filter_info.get("keep_lines_matching", [])
            match_output = filter_info.get("match_output", [])

            # Check regex validity
            for p in [match_cmd] + strip_lines + keep_lines:
                if p:
                    try:
                        re.compile(p)
                    except re.error as e:
                        print(f"Warning: regex error in {toml_path.name}: {p} -> {e}")

            json_data = {
                "name": filter_name,
                "description": filter_info.get("description", ""),
                "match_command": match_cmd,
                "strip_ansi": filter_info.get("strip_ansi", True),
                "strip_lines_matching": strip_lines,
                "keep_lines_matching": keep_lines,
                "match_output": match_output,
                "max_lines": filter_info.get("max_lines"),
                "tail_lines": filter_info.get("tail_lines"),
                "truncate_lines_at": filter_info.get("truncate_lines_at"),
                "on_empty": filter_info.get("on_empty"),
                "source": f"rtk-ai/rtk (src/filters/{toml_path.name})",
                "license": "Apache-2.0",
                "modified": True,
                "tests": [
                    {
                        "name": t.get("name", ""),
                        "input": t.get("input", ""),
                        "expected": t.get("expected", ""),
                    }
                    for t in test_cases
                    if isinstance(t, dict)
                ],
            }

            target_file = TARGET_DIR / f"{filter_name}.json"
            target_file.write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            count += 1

    print(f"Successfully ported {count} filters to {TARGET_DIR}")
    return count


if __name__ == "__main__":
    port_filters()
