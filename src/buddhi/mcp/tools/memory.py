"""MCP tool implementation for Google OKF v0.2 & Claude Code memory operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from buddhi.memory.hash import compute_content_hash
from buddhi.memory.models import (
    MemoryConfidence,
    MemoryFrontmatter,
    MemoryKind,
    MemoryNode,
    MemorySource,
    MemoryStatus,
)
from buddhi.memory.resolver import matches_active_files, resolve_imports
from buddhi.memory.security import sanitize_slug
from buddhi.memory.store import MemoryStore


def execute_buddhi_memory(
    action: str,
    query: str | None = None,
    kind: str | None = None,
    scope: str = "project",
    active_files: list[str] | None = None,
    node_id: str | None = None,
    title: str | None = None,
    summary: str | None = None,
    body: str | None = None,
    path_globs: list[str] | None = None,
    sources: list[str] | None = None,
    tags: list[str] | None = None,
    expand_imports: bool = True,
    root_path: Path | None = None,
) -> str:
    """Execute memory action: search, read, remember, status."""
    workspace_root = root_path if root_path is not None else Path.cwd().resolve()
    store = MemoryStore(workspace_root)

    action_lower = action.lower().strip()

    if action_lower == "status":
        val = store.validate_bundle(scope=scope)
        return json.dumps(val, indent=2)

    elif action_lower == "search":
        kind_enum = None
        if kind:
            try:
                kind_enum = MemoryKind(kind)
            except ValueError:
                pass

        all_nodes = store.list_nodes(scopes=[scope], kind=kind_enum)
        results: list[dict[str, Any]] = []

        q_lower = query.lower().strip() if query else ""

        for node in all_nodes:
            # Check path glob matching
            if active_files is not None and not matches_active_files(
                node.frontmatter.paths, active_files
            ):
                continue

            # Check query relevance
            if q_lower:
                in_title = q_lower in node.title.lower()
                in_summary = q_lower in node.summary.lower()
                in_tags = any(q_lower in t.lower() for t in node.frontmatter.tags)
                in_body = q_lower in node.body.lower()
                if not (in_title or in_summary or in_tags or in_body):
                    continue

            results.append(
                {
                    "id": node.id,
                    "kind": node.kind.value,
                    "title": node.title,
                    "summary": node.summary,
                    "status": node.frontmatter.status.value,
                    "confidence": node.frontmatter.confidence.value,
                    "scope": node.frontmatter.scope,
                    "paths": node.frontmatter.paths,
                    "tags": node.frontmatter.tags,
                }
            )

        return json.dumps({"count": len(results), "memories": results}, indent=2)

    elif action_lower == "read":
        if not node_id:
            return "Error: node_id parameter is required for 'read' action."

        all_nodes = store.list_nodes(scopes=[scope])
        target_node = next((n for n in all_nodes if n.id == node_id), None)
        if not target_node:
            return f"Error: memory concept '{node_id}' not found in scope '{scope}'."

        raw_md = target_node.to_markdown()
        if expand_imports and target_node.file_path:
            return resolve_imports(
                text=raw_md,
                base_file=target_node.file_path,
                workspace_root=workspace_root,
                user_memory_root=store.user_memory_root,
            )
        return raw_md

    elif action_lower == "remember":
        if not title or not summary:
            return "Error: 'title' and 'summary' are required parameters for 'remember' action."

        try:
            kind_enum = MemoryKind(kind) if kind else MemoryKind.CONVENTION
        except ValueError:
            return f"Error: invalid kind '{kind}'. Must be one of {[k.value for k in MemoryKind]}."

        slug = sanitize_slug(title)
        new_id = node_id or f"mem-{kind_enum.value}-{slug}"

        source_objs: list[MemorySource] = []
        if sources:
            for idx, s_ref in enumerate(sources, 1):
                try:
                    chash = compute_content_hash(workspace_root, s_ref)
                    source_objs.append(
                        MemorySource(
                            id=f"src-{idx}", resource=s_ref, content_hash=chash
                        )
                    )
                except (OSError, ValueError) as exc:
                    return f"Error hashing source anchor '{s_ref}': {exc}"

        node = MemoryNode(
            frontmatter=MemoryFrontmatter(
                id=new_id,
                kind=kind_enum,
                title=title,
                summary=summary,
                status=MemoryStatus.STABLE,
                confidence=MemoryConfidence.VERIFIED,
                scope=scope,
                paths=path_globs or [],
                tags=tags or [],
                sources=source_objs,
            ),
            body=f"# Summary\n\n{summary}\n\n# Context & Rationale\n\n{body}\n"
            if body
            else f"# Summary\n\n{summary}\n",
        )

        try:
            saved_path = store.save_node(node, scope=scope)
            return json.dumps(
                {
                    "status": "success",
                    "id": new_id,
                    "path": str(saved_path),
                    "scope": scope,
                },
                indent=2,
            )
        except (OSError, ValueError, PermissionError) as exc:
            return f"Error persisting memory concept: {exc}"

    return (
        f"Error: unknown action '{action}'. Supported: search, read, remember, status."
    )
