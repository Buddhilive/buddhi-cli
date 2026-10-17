"""Security invariants, sandboxing, slug sanitization, and secret scanning."""

from __future__ import annotations

import re
from pathlib import Path

TOPIC_DIRS: dict[str, str] = {
    "decision": "decisions",
    "convention": "conventions",
    "preference": "preferences",
    "feedback": "feedback",
    "sdd-rationale": "sdd",
    "domain-learning": "learnings",
}

WINDOWS_RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}

SECRET_PATTERNS = [
    re.compile(
        r"(?i)(?:api_key|access_token|secret_key|private_key|auth_token|client_secret|bearer)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-\.]{16,}['\"]?"
    ),
    re.compile(r"sk-(?:proj-)?[a-zA-Z0-9_-]{32,}"),
    re.compile(r"gh[pousr]_[a-zA-Z0-9]{36,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"(?i)(?:postgres|mysql|mongodb|redis):\/\/[^:]+:[^@]+@[a-zA-Z0-9\._\-]+"
    ),
]


def sanitize_slug(raw_slug: str) -> str:
    """Sanitize slug for safe cross-platform file naming."""
    # Replace path separators and special characters with dash
    clean = raw_slug.replace("/", "-").replace("\\", "-")
    slug = re.sub(r"[^a-z0-9_-]+", "-", clean.lower()).strip("-_")
    if not slug or slug in WINDOWS_RESERVED or slug == "..":
        slug = f"mem-{slug}" if slug else "mem-node"
    return slug[:60]


def build_memory_file_path(base_memory_dir: Path, kind: str, slug: str) -> Path:
    """Builds and validates an atomic concept file path inside base_memory_dir."""
    if ".." in slug or "/" in slug or "\\" in slug:
        raise PermissionError(
            f"Slug traversal blocked: '{slug}' contains path separators or traversal characters"
        )
    topic_sub = TOPIC_DIRS.get(kind, "misc")
    clean_slug = sanitize_slug(slug)
    target = (base_memory_dir / topic_sub / f"{clean_slug}.md").resolve()
    base_resolved = base_memory_dir.resolve()
    if not target.is_relative_to(base_resolved):
        raise PermissionError(
            f"Slug traversal blocked: '{slug}' resolves outside memory base directory"
        )
    return target


def parse_source_resource(
    resource: str, workspace_root: Path
) -> tuple[Path, int | None, int | None]:
    """Parses and validates a code source anchor ('path/file.py#L10-L20')."""
    path_part, _, line_part = resource.partition("#")
    cleaned = path_part.strip().replace("\\", "/")
    if cleaned.startswith(("/", "\\")) or ".." in Path(cleaned).parts:
        raise PermissionError(
            f"Source resource '{resource}' uses absolute or parent traversal path"
        )

    target = (workspace_root / cleaned).resolve()
    ws_resolved = workspace_root.resolve()
    if not target.is_relative_to(ws_resolved):
        raise PermissionError(f"Source resource '{resource}' escapes workspace root")

    start_line, end_line = None, None
    if line_part:
        m = re.match(r"^L(\d+)(?:-L(\d+))?$", line_part.strip())
        if not m:
            raise ValueError(f"Invalid line range in source anchor: #{line_part}")
        start_line = int(m.group(1))
        end_line = int(m.group(2)) if m.group(2) else start_line
        if start_line <= 0 or end_line < start_line:
            raise ValueError(f"Invalid line range bounds: L{start_line}-L{end_line}")

    return target, start_line, end_line


def resolve_and_sandbox_import(
    raw_ref: str,
    base_dir: Path,
    workspace_root: Path,
    user_memory_root: Path,
) -> Path:
    """Resolves an `@path` import string while strictly enforcing workspace / user-memory sandboxing."""
    cleaned = raw_ref.lstrip("@").strip()
    if "\0" in cleaned or "\r" in cleaned or "\n" in cleaned:
        raise ValueError(f"Invalid characters in import path: '{raw_ref}'")

    if cleaned.startswith(("\\\\", "//")):
        raise PermissionError(f"UNC network paths forbidden: '{raw_ref}'")

    # Base path resolution
    if cleaned.startswith("~"):
        target = Path(cleaned).expanduser()
    elif cleaned.startswith("/") or (
        len(cleaned) > 2 and cleaned[1] == ":" and cleaned[2] in "\\/"
    ):
        target = Path(cleaned)
    else:
        # Relative to current file directory if exists, otherwise relative to workspace root
        from_base = (base_dir / cleaned).resolve()
        if from_base.exists():
            target = from_base
        else:
            target = (workspace_root / cleaned).resolve()

    try:
        resolved = target.resolve(strict=True)
    except (FileNotFoundError, RuntimeError, OSError) as exc:
        raise FileNotFoundError(f"Cannot resolve import '{raw_ref}': {exc}") from exc

    ws_resolved = workspace_root.resolve()
    user_resolved = user_memory_root.resolve()

    in_workspace = resolved.is_relative_to(ws_resolved)
    in_user = resolved.is_relative_to(user_resolved)

    if not (in_workspace or in_user):
        raise PermissionError(
            f"Sandbox escape blocked: '{raw_ref}' resolves outside permitted roots"
        )

    if not resolved.is_file():
        raise ValueError(f"Import target is not a regular file: '{raw_ref}'")

    return resolved


def assert_no_secrets_in_tracked_memory(content: str, scope: str) -> None:
    """Blocks secrets/credentials from being persisted into git-tracked scopes."""
    if scope in ("local", "agent-local"):
        return

    for pattern in SECRET_PATTERNS:
        if pattern.search(content):
            raise PermissionError(
                "Potential secret or credential detected in memory content. "
                "Credentials must never be saved to git-tracked 'project' memory. "
                "Use scope 'local' or store credentials in environment variables."
            )
