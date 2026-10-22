"""Custom Pelican reader for Google Open Knowledge Format (OKF v0.2) markdown files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

import markdown
from pelican.readers import BaseReader  # type: ignore[import-untyped]

from buddhi.memory.frontmatter import split_frontmatter

# Regex matching relative markdown links inside HTML <a> tags:
# Matches href="something.md" or href="dir/something.md#fragment"
# Skips http://, https://, mailto:, ftp://, and pure fragments #...
_MD_LINK_RE = re.compile(
    r'(?P<prefix><a\s+[^>]*?href=["\'])(?P<target>(?!https?://|mailto:|ftp://|#)[^"\':#]+?\.md)(?P<suffix>#[^"\']*?)?(?P<postfix>["\'])',
    re.IGNORECASE,
)

_MERMAID_BLOCK_RE = re.compile(r"```mermaid\r?\n(.*?)\r?\n```", re.DOTALL)


def classify_doc_section(rel_path: Path) -> str:
    """Classify relative document path into a human-friendly documentation section."""
    parts = rel_path.parts
    if len(parts) <= 1:
        return "Overview"
    top = parts[0]
    if top in ("communities", "god-nodes"):
        return top
    if top == "src" and len(parts) >= 3:
        return parts[2].replace("_", " ").title()
    if top == ".agents":
        return "Harness & Skills"
    if top == "tests":
        return "Tests"
    return top.replace("_", " ").title()


class OKFMarkdownReader(BaseReader):
    """Pelican reader parsing OKF v0.2 YAML frontmatter and rendering Markdown."""

    enabled = True
    file_extensions: ClassVar[list[str]] = ["md", "markdown"]

    def read(self, filename: str) -> tuple[str, dict[str, Any]]:
        file_path = Path(filename)
        raw_text = file_path.read_text(encoding="utf-8")

        # 1. Frontmatter parsing: split_frontmatter uses yaml.safe_load and
        # automatically strips forbidden Attested Computation fields
        # ('runtime', 'parameters', 'executor', 'attester')
        data, body = split_frontmatter(raw_text)

        # 2. Map OKF metadata to Pelican Page metadata
        metadata: dict[str, Any] = {}
        for k, v in data.items():
            metadata[k.lower()] = v

        # Normalize key Pelican page attributes
        title = data.get("title")
        if not title:
            # Fall back to first H1 in body or filename stem
            h1_match = re.search(r"^#\s+(.+)$", body, re.MULTILINE)
            title = h1_match.group(1).strip() if h1_match else file_path.stem
        metadata["title"] = title

        description = data.get("description") or data.get("summary") or ""
        metadata["summary"] = description
        metadata["description"] = description
        okf_status = data.get("status", "stable")
        metadata["okf_status"] = okf_status
        # In Pelican, content status must be in ('published', 'hidden', 'draft', 'skip')
        metadata["status"] = "draft" if okf_status == "draft" else "published"
        metadata["kind"] = data.get("type") or data.get("kind", "concept")
        metadata["okf_type"] = metadata["kind"]
        metadata["okf_version"] = str(data.get("okf_version", "0.2"))

        # Calculate hierarchical URL / save_as relative to content root
        content_root_str = self.settings.get("PATH", ".")
        content_root = Path(content_root_str).resolve()
        try:
            rel_path = file_path.resolve().relative_to(content_root)
        except (ValueError, RuntimeError):
            rel_path = file_path

        html_rel = rel_path.with_suffix(".html").as_posix()
        metadata["save_as"] = html_rel
        metadata["url"] = html_rel
        default_tpl = "index" if html_rel == "index.html" else "page"
        metadata["template"] = data.get("template") or default_tpl
        metadata["doc_section"] = classify_doc_section(rel_path)

        # 3. Preprocess Mermaid code blocks to <pre class="mermaid"> and render Markdown
        processed_body = _MERMAID_BLOCK_RE.sub(
            r'<pre class="mermaid">\n\1\n</pre>', body
        )
        md = markdown.Markdown(
            extensions=["fenced_code", "tables", "toc", "codehilite"],
            extension_configs={
                "codehilite": {"css_class": "highlight", "guess_lang": False}
            },
        )
        html_content = md.convert(processed_body)

        # 4. Relative link rewriting: [Text](path/doc.md#anchor) -> <a href="path/doc.html#anchor">
        def _rewrite_link(m: re.Match) -> str:
            prefix = m.group("prefix")
            target = m.group("target")
            suffix = m.group("suffix") or ""
            postfix = m.group("postfix")
            html_target = target[:-3] + ".html"
            return f"{prefix}{html_target}{suffix}{postfix}"

        html_content = _MD_LINK_RE.sub(_rewrite_link, html_content)
        return html_content, metadata
