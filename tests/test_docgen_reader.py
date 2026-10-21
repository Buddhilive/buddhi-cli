from __future__ import annotations

from pathlib import Path

from buddhi.docgen.reader import OKFMarkdownReader


def test_okf_reader_parses_nested_frontmatter(tmp_path: Path) -> None:
    doc_path = tmp_path / "concept.md"
    content = """---
type: Function
title: my_function
description: Computes something critical.
status: stable
tags: [python, core]
generated:
  by: antigravity/model
  at: "2026-10-27T12:00:00Z"
sources:
  - id: src
    resource: src/core.py#L10-L25
    content_hash: 5f4dcc3b5aa765d61d8327deb882cf99
relations:
  - kind: calls
    target: helper_func
---

# Summary
This is my function.

## Code Example
```python
x = my_function()
```

See [Helper](helper.md) or [External](https://example.com) or [Section](#summary).
"""
    doc_path.write_text(content, encoding="utf-8")

    reader = OKFMarkdownReader(settings={"PATH": str(tmp_path)})
    html_content, metadata = reader.read(str(doc_path))

    assert metadata["title"] == "my_function"
    assert metadata["summary"] == "Computes something critical."
    assert metadata["okf_status"] == "stable"
    assert metadata["status"] == "published"
    assert metadata["kind"] == "Function"
    assert metadata["tags"] == ["python", "core"]
    assert metadata["generated"]["by"] == "antigravity/model"
    assert len(metadata["sources"]) == 1
    assert metadata["sources"][0]["content_hash"] == "5f4dcc3b5aa765d61d8327deb882cf99"
    assert metadata["relations"][0]["target"] == "helper_func"

    # HTML rendering and markdown extensions
    assert "This is my function." in html_content
    assert "<code" in html_content

    # Relative .md link should be rewritten to .html
    assert 'href="helper.html"' in html_content
    # External link should remain untouched
    assert 'href="https://example.com"' in html_content
    # Fragment should remain untouched
    assert 'href="#summary"' in html_content


def test_okf_reader_strips_forbidden_attested_computation_fields(
    tmp_path: Path,
) -> None:
    doc_path = tmp_path / "forbidden.md"
    content = """---
type: Module
title: security_test
runtime: python3.11
parameters: {key: value}
executor: worker-1
attester: enclave-0
---

# Safe Content
"""
    doc_path.write_text(content, encoding="utf-8")

    reader = OKFMarkdownReader(settings={"PATH": str(tmp_path)})
    _, metadata = reader.read(str(doc_path))

    assert metadata["title"] == "security_test"
    assert "runtime" not in metadata
    assert "parameters" not in metadata
    assert "executor" not in metadata
    assert "attester" not in metadata


def test_okf_reader_falls_back_to_h1_when_title_omitted(tmp_path: Path) -> None:
    doc_path = tmp_path / "untitled.md"
    content = """---
type: Concept
description: Missing explicit title
---

# Heading One Title

Body text here.
"""
    doc_path.write_text(content, encoding="utf-8")

    reader = OKFMarkdownReader(settings={"PATH": str(tmp_path)})
    _, metadata = reader.read(str(doc_path))

    assert metadata["title"] == "Heading One Title"
