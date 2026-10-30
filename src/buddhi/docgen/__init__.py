"""Buddhi documentation generation engine: OKF v0.2, code graph synthesis, and Pelican static site."""

from __future__ import annotations

from buddhi.docgen.planner import PlanEntry, build_docs_plan, plan_to_json
from buddhi.docgen.reader import OKFMarkdownReader
from buddhi.docgen.site import compile_site, get_pelican_settings, serve_docs
from buddhi.docgen.slug import (
    SlugResolver,
    safe_filename,
    stem_filename_budget,
    write_text_atomic_if_changed,
)

__all__ = [
    "OKFMarkdownReader",
    "PlanEntry",
    "SlugResolver",
    "build_docs_plan",
    "compile_site",
    "get_pelican_settings",
    "plan_to_json",
    "safe_filename",
    "serve_docs",
    "stem_filename_budget",
    "write_text_atomic_if_changed",
]
