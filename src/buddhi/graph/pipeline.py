"""Shared walk -> build -> resolve -> cluster pipeline.

Used by both `buddhi generate` and `buddhi init`/`buddhi docs plan` so the two
commands never drift into building the graph two different ways.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from buddhi.discovery.walker import WalkResult, walk
from buddhi.graph.builder import BuildContext, build_graph
from buddhi.graph.cache import get_git_head_sha
from buddhi.graph.clustering import assign_communities
from buddhi.graph.resolver import resolve
from buddhi.languages.registry import available_languages
from buddhi.persist.sqlite_writer import load_extract_cache


@dataclass
class PipelineResult:
    root: Path
    walk_result: WalkResult
    build_ctx: BuildContext
    community_count: int
    language_warnings: dict[str, str]


def run_pipeline(root: Path, max_file_size: int = 2_000_000) -> PipelineResult:
    """Walk `root`, build the code graph, resolve edges, and cluster it."""
    lang_status = available_languages()
    avail = {lang for lang, err in lang_status.items() if err is None}
    language_warnings = {
        lang: err for lang, err in lang_status.items() if err is not None
    }

    walk_result = walk(root, max_file_size=max_file_size, available_languages=avail)

    db_path = root / ".buddhi" / "graphs" / "tree-graph.db"
    existing_cache = load_extract_cache(db_path) if db_path.is_file() else None

    build_ctx = build_graph(walk_result, existing_cache=existing_cache)
    resolve(build_ctx)
    community_count = assign_communities(build_ctx.graph)
    build_ctx.graph.built_at_commit = get_git_head_sha(root)

    return PipelineResult(
        root=root,
        walk_result=walk_result,
        build_ctx=build_ctx,
        community_count=community_count,
        language_warnings=language_warnings,
    )
