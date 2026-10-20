from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

mcp = FastMCP("buddhi-cli")

# Global DB path override if provided via CLI argument
OVERRIDE_DB_PATH: Path | None = None

# Global workspace root override if provided via CLI argument
OVERRIDE_ROOT: Path | None = None


def _get_db_path(cwd: str | None = None) -> Path:
    """Resolve the SQLite graph database path.

    1. Use the command-line override if set.
    2. Traverse upwards from CWD (or given cwd / OVERRIDE_ROOT) to auto-detect .buddhi/graphs/tree-graph.db.
    3. Fallback to (start_dir)/.buddhi/graphs/tree-graph.db if not found.
    """
    if OVERRIDE_DB_PATH is not None:
        return OVERRIDE_DB_PATH

    start_dir = (
        Path(cwd).resolve()
        if cwd
        else (OVERRIDE_ROOT if OVERRIDE_ROOT is not None else Path.cwd().resolve())
    )
    for parent in [start_dir] + list(start_dir.parents):
        for rel in [
            Path(".buddhi") / "graphs" / "tree-graph.db",
            Path(".buddhi") / "tree-graph.db",
            Path(".buddhi") / "graph.db",
        ]:
            candidate = parent / rel
            if candidate.exists():
                return candidate

    # Standard fallback
    return start_dir / ".buddhi" / "graphs" / "tree-graph.db"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_graph(
    action: Annotated[
        str,
        "Graph operation: 'blast_radius', 'god_nodes', 'surprises', 'questions', 'shortest_path', 'cycles', 'community', or 'stats'",
    ],
    targets: Annotated[
        list[str] | None,
        "Target file paths or symbol names/IDs for 'blast_radius'",
    ] = None,
    git_ref: Annotated[
        str | None,
        "Git revision or commit for 'blast_radius' diff",
    ] = None,
    staged: Annotated[
        bool,
        "Check staged git changes for 'blast_radius'",
    ] = False,
    source: Annotated[
        str | None,
        "Source symbol name or ID for 'shortest_path'",
    ] = None,
    target: Annotated[
        str | None,
        "Target symbol name or ID for 'shortest_path'",
    ] = None,
    community_id: Annotated[
        int | None,
        "Community ID for 'community' inspection",
    ] = None,
    max_hops: Annotated[
        int,
        "Maximum hops for 'blast_radius' (1-6) or 'shortest_path'",
    ] = 3,
    top_n: Annotated[
        int,
        "Maximum items to return for diagnostics",
    ] = 10,
    as_json: Annotated[
        bool,
        "Return structured JSON format",
    ] = False,
    cwd: Annotated[
        str | None,
        "Working directory override",
    ] = None,
) -> str:
    """Analyze code graph topology, blast radius, hubs, surprises, cycles, and stats."""
    from buddhi.mcp.tools.graph import execute_buddhi_graph

    db_path = _get_db_path(cwd)
    root_dir = Path(cwd).resolve() if cwd else OVERRIDE_ROOT
    try:
        return execute_buddhi_graph(
            action=action,
            db_path=str(db_path),
            root_path=root_dir,
            targets=targets,
            git_ref=git_ref,
            staged=staged,
            source=source,
            target=target,
            community_id=community_id,
            max_hops=max_hops,
            top_n=top_n,
            as_json=as_json,
        )
    except Exception as e:  # noqa: BLE001
        return f"Error executing graph operation: {e}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_search(
    query: Annotated[
        str,
        "Search query — function names, class names, or natural-language descriptions of code behavior",
    ],
    top_n: Annotated[int, "Number of top lexical anchors to retrieve"] = 3,
    mode: Annotated[
        str,
        "Output mode: 'full' (complete source), 'signatures' (declarations only), or 'map' (one-liner index)",
    ] = "full",
    include_bridges: Annotated[
        bool, "Include 1-hop bridge nodes from neighboring communities"
    ] = True,
    budget: Annotated[int, "Max character count for output. 0 = unbounded"] = 8000,
    cwd: Annotated[
        str | None,
        "Working directory override. Defaults to CWD of the MCP server process.",
    ] = None,
) -> str:
    """Search the codebase using Buddhi's topology-driven retrieval pipeline.

    This replaces standard keyword-only searches with community-aware,
    context-optimized results. It identifies lexical anchors, expands to community
    neighborhoods, filters out boilerplate, and sorts using a U-curve positional layout.
    """
    from buddhi.mcp.tools.search import execute_buddhi_search

    db_path = _get_db_path(cwd)
    root_dir = Path(cwd).resolve() if cwd else OVERRIDE_ROOT
    try:
        return execute_buddhi_search(
            query=query,
            db_path=str(db_path),
            top_n=top_n,
            mode=mode,
            include_bridges=include_bridges,
            budget=budget,
            root_path=root_dir,
        )
    except Exception as e:  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001
        return f"Error executing search: {e}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def buddhi_read(
    filepath: Annotated[str | None, "The workspace path to the file to read"] = None,
    query: Annotated[
        str | None, "Glob pattern or identifier to find files/symbols in the workspace"
    ] = None,
    mode: Annotated[
        str, "Compression profile: 'auto', 'full', 'signatures', 'map', or 'entropy'"
    ] = "auto",
    task_intent: Annotated[
        str | None, "Natural language goals (e.g. 'Fix the bug') to auto-resolve mode"
    ] = None,
    budget: Annotated[
        int, "Max token count budget. Fallbacks to map if exceeded"
    ] = 4000,
    cwd: Annotated[
        str | None,
        "Working directory override. Defaults to CWD of the MCP server process.",
    ] = None,
) -> str:
    """Read a file using dynamic compression, AST pruning, and bounce prevention logic, or search for files/symbols in the workspace."""
    from buddhi.mcp.tools.read import execute_buddhi_read

    db_path = _get_db_path(cwd)
    root_dir = Path(cwd).resolve() if cwd else OVERRIDE_ROOT
    try:
        return execute_buddhi_read(
            filepath=filepath,
            db_path=str(db_path) if db_path.exists() else None,
            mode=mode,
            task_intent=task_intent,
            budget=budget,
            query=query,
            root_path=root_dir,
        )
    except Exception as e:  # noqa: BLE001  # noqa: BLE001  # noqa: BLE001
        return f"Error executing read: {e}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def check_contrast(
    color_a: Annotated[
        str | None,
        "First color as hex (#FFFFFF or FFFFFF) or named color ('black', 'white')",
    ] = None,
    color_b: Annotated[
        str | None,
        "Second color as hex (#FFFFFF or FFFFFF) or named color ('black', 'white')",
    ] = None,
    bg: Annotated[
        str | None,
        "Background color token for multi-pair contrast checking",
    ] = None,
    fg: Annotated[
        list[str] | str | None,
        "Foreground color token(s) tested against the background",
    ] = None,
    profile: Annotated[
        str,
        "Strictness profile ('standard', 'shield', or 'launchpad')",
    ] = "standard",
    css_path: Annotated[
        str | None,
        "Path to CSS file for stylesheet triage analysis",
    ] = None,
    page_bg: Annotated[
        str,
        "Page background color token for CSS triage (default: #ffffff)",
    ] = "#ffffff",
) -> str:
    """Check WCAG 2.x contrast ratio between two colors, multi-pair tokens, or across a stylesheet."""
    from buddhi.mcp.tools.contrast import execute_check_contrast

    return execute_check_contrast(
        color_a=color_a,
        color_b=color_b,
        bg=bg,
        fg=fg,
        profile=profile,
        css_path=css_path,
        page_bg=page_bg,
    )


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True))
def verify_a11y(
    project_dir: Annotated[
        str,
        "Project root directory (default: current directory)",
    ] = ".",
    src: Annotated[
        str | None,
        "Subdirectory holding the interface source code to scan",
    ] = None,
    report_dir: Annotated[
        str | None,
        "Directory containing A11Y governance artifacts (REPORT.md, etc.)",
    ] = None,
    warn_only: Annotated[
        bool,
        "Report findings without failing exit status",
    ] = False,
    as_json: Annotated[
        bool,
        "Return structured JSON with findings, errors, and warnings",
    ] = False,
) -> str:
    """Run the A11Y.md static gate to verify artifacts, freshness, contrast math, and source anti-patterns."""
    from buddhi.mcp.tools.a11y import execute_verify_a11y

    return execute_verify_a11y(
        project_dir=project_dir,
        src=src,
        report_dir=report_dir,
        warn_only=warn_only,
        as_json=as_json,
    )


@mcp.tool()
def buddhi_memory(
    action: Annotated[
        str, "Memory operation: 'search', 'read', 'remember', or 'status'"
    ],
    query: Annotated[str | None, "Search query (keywords, concept title, tags)"] = None,
    kind: Annotated[
        str | None,
        "Filter or set concept kind: decision, convention, preference, feedback, sdd-rationale",
    ] = None,
    scope: Annotated[
        str, "Memory scope: 'project', 'local', 'user', or 'agent:<name>'"
    ] = "project",
    active_files: Annotated[
        list[str] | None,
        "List of currently active file paths for path-scoped glob matching",
    ] = None,
    node_id: Annotated[
        str | None,
        "Exact memory concept ID to read or update (e.g. 'mem-decision-sqlite-wal')",
    ] = None,
    title: Annotated[str | None, "Concept title (required for 'remember')"] = None,
    summary: Annotated[
        str | None, "One-sentence concept summary (required for 'remember')"
    ] = None,
    body: Annotated[
        str | None, "Markdown body detailing context, rationale, and invariants"
    ] = None,
    path_globs: Annotated[
        list[str] | None,
        "Glob patterns when this memory activates (e.g. ['src/api/**/*.py'])",
    ] = None,
    sources: Annotated[
        list[str] | None,
        "Code provenance anchors to hash and track staleness (e.g. ['src/api/auth.py#L10-L40'])",
    ] = None,
    tags: Annotated[list[str] | None, "Classification tags"] = None,
    expand_imports: Annotated[
        bool, "Expand @path imports inline (up to 5 hops)"
    ] = True,
    cwd: Annotated[
        str | None, "Working directory override. Defaults to CWD or --root."
    ] = None,
) -> str:
    """Query, read, and curate durable OKF v0.2 + Claude Code memory concepts for this project."""
    from buddhi.mcp.tools.memory import execute_buddhi_memory

    root_dir = Path(cwd).resolve() if cwd else OVERRIDE_ROOT
    try:
        return execute_buddhi_memory(
            action=action,
            query=query,
            kind=kind,
            scope=scope,
            active_files=active_files,
            node_id=node_id,
            title=title,
            summary=summary,
            body=body,
            path_globs=path_globs,
            sources=sources,
            tags=tags,
            expand_imports=expand_imports,
            root_path=root_dir,
        )
    except Exception as e:  # noqa: BLE001  # noqa: BLE001
        return f"Error executing memory operation: {e}"


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=False))
def stage_skill(
    action: Annotated[
        str, "Action: 'create', 'update', 'patch', 'remove_file', or 'delete'"
    ],
    name: Annotated[str, "Skill identifier (lowercase, hyphenated)"],
    layer: Annotated[str, "Target layer: 'project' (default) or 'global'"] = "project",
    body: Annotated[str | None, "Full Markdown body including YAML frontmatter"] = None,
    old_string: Annotated[
        str | None, "Exact target text to replace (for 'patch')"
    ] = None,
    new_string: Annotated[str | None, "Replacement text (for 'patch')"] = None,
    files: Annotated[
        dict[str, str] | None, "Relative subfile mapping {filepath: content}"
    ] = None,
    reason: Annotated[str, "Why this mutation is needed"] = "",
    evidence: Annotated[
        str, "Concrete log/code evidence demonstrating the problem/rule"
    ] = "",
    absorbed_into: Annotated[
        str | None, "Target surviving umbrella skill name (for 'delete')"
    ] = None,
    cwd: Annotated[str | None, "Workspace root override"] = None,
) -> str:
    """Stage a self-learned skill mutation into the AutoHarness intent queue for admission validation and promotion."""
    from buddhi.scripts.autoharness.intent_queue import append_intent
    from buddhi.scripts.autoharness.models import SkillIntent

    if action not in ("create", "update", "patch", "remove_file", "delete"):
        return f"Error: Invalid action '{action}'. Must be one of create, update, patch, remove_file, delete."

    if not name:
        return "Error: Skill name is required."

    if action in ("create", "update") and not body:
        return f"Error: Action '{action}' requires a Markdown body."

    if action == "patch" and (not old_string or new_string is None):
        return "Error: Action 'patch' requires 'old_string' and 'new_string'."

    if action != "delete" and not evidence.strip():
        return f"Error: Action '{action}' requires non-empty 'evidence'."

    if not reason.strip():
        return f"Error: Action '{action}' requires non-empty 'reason'."

    if action == "delete" and not absorbed_into:
        return "Error: Action 'delete' requires 'absorbed_into' naming the surviving skill."

    intent = SkillIntent(
        action=action,  # type: ignore[arg-type]
        name=name,
        layer=layer if layer in ("project", "global") else "project",  # type: ignore[arg-type]
        body=body,
        old_string=old_string,
        new_string=new_string,
        files=files or {},
        reason=reason,
        evidence=evidence,
        absorbed_into=absorbed_into,
    )

    project_root = (
        Path(cwd).resolve() if cwd else (OVERRIDE_ROOT or Path.cwd().resolve())
    )
    try:
        append_intent(intent, run_id="interactive", project_root=project_root)
        return f"[AutoHarness] Staged intent '{action} {name}'. Will be validated and landed on turn completion."
    except Exception as exc:  # noqa: BLE001
        return f"Error staging skill intent: {exc}"


def main() -> None:
    """CLI entrypoint for running the MCP server."""
    parser = argparse.ArgumentParser(description="Buddhi MCP Server (StdIO)")
    parser.add_argument(
        "--db-path",
        type=str,
        help="Explicit path to the .buddhi/graphs/tree-graph.db database (overrides auto-detection)",
    )
    parser.add_argument(
        "--root",
        "-r",
        type=str,
        help="Explicit path to the workspace root directory",
    )
    parser.add_argument(
        "root_dir",
        nargs="?",
        type=str,
        default=None,
        help="Optional positional path to the workspace root directory",
    )

    args, unknown = parser.parse_known_args()

    if args.db_path:
        global OVERRIDE_DB_PATH
        OVERRIDE_DB_PATH = Path(args.db_path).resolve()

    root_val = args.root or args.root_dir
    if root_val:
        global OVERRIDE_ROOT
        OVERRIDE_ROOT = Path(root_val).resolve()

    sys.argv = [sys.argv[0]] + unknown
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
