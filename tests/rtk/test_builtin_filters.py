from __future__ import annotations

import re

from buddhi.scripts.rtk.engine import apply_filter
from buddhi.scripts.rtk.filters import load_builtin_filters


def test_builtin_filters_load_and_compile() -> None:
    filters = load_builtin_filters()
    assert len(filters) >= 50, (
        f"Expected at least 50 builtin filters, found {len(filters)}"
    )

    for spec in filters:
        assert spec.name, "Filter must have a name"
        assert spec.license == "Apache-2.0", (
            f"Filter {spec.name} missing Apache-2.0 license"
        )
        assert spec.source, f"Filter {spec.name} missing source attribution"

        if spec.match_command:
            compiled = re.compile(spec.match_command)
            assert compiled is not None

        for p in spec.strip_lines_matching:
            compiled = re.compile(p)
            assert compiled is not None

        for p in spec.keep_lines_matching:
            compiled = re.compile(p)
            assert compiled is not None


def test_builtin_filter_embedded_test_cases() -> None:
    filters = load_builtin_filters()
    tested_cases = 0

    for spec in filters:
        for t in spec.tests:
            result = apply_filter(t.input, spec)
            # Normalise newlines and whitespace for comparison
            normalized_expected = t.expected.strip().replace("\r\n", "\n")
            normalized_result = result.strip().replace("\r\n", "\n")
            assert normalized_result == normalized_expected, (
                f"Filter {spec.name} test '{t.name}' failed:\nExpected:\n{normalized_expected}\nGot:\n{normalized_result}"
            )
            tested_cases += 1

    assert tested_cases > 0, "Expected at least one embedded test case to be executed"
