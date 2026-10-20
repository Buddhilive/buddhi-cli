"""Dependency-free YAML frontmatter parser and deterministic 6-gate admission validator."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from buddhi.scripts.autoharness.config import (
    STAGE_MAX_BODY_BYTES,
    STAGE_MAX_FILE_BYTES,
    STAGE_MAX_FILES,
    STAGE_MAX_FILES_TOTAL_BYTES,
    get_skill_body_max_lines,
)
from buddhi.scripts.autoharness.layer import check_new_name, check_subfile_path
from buddhi.scripts.autoharness.models import GateFinding, SkillIntent, ValidationResult
from buddhi.scripts.autoharness.redact import secret_hits
from buddhi.scripts.autoharness.skills_guard import scan as scan_guard

_ALLOWED_CATEGORIES = {
    "git",
    "testing",
    "debugging",
    "api",
    "database",
    "ui",
    "build",
    "architecture",
    "workflow",
    "documentation",
    "general",
    "performance",
    "security",
}
_TRIGGER_KEYWORDS = ("when", "use when", "whenever", "trigger", "if", "on")
_PLACEHOLDERS = ("TODO", "FIXME", "XXX", "REPLACE_ME", "<placeholder>")
_POINTER_RE = re.compile(
    r"\[.*?\]\(((?:\./)?(?:references|templates|scripts|assets)/[^\s\)]+)\)"
)


def parse_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Parse YAML frontmatter enclosed in --- markers, supporting CRLF and block scalars."""
    norm = content.replace("\r\n", "\n")
    if not norm.startswith("---"):
        raise ValueError("Missing leading '---' frontmatter delimiter.")

    lines = norm.split("\n")
    fm_lines: list[str] = []
    body_start_idx = -1

    for idx, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            body_start_idx = idx + 1
            break
        fm_lines.append(line)

    if body_start_idx == -1:
        raise ValueError("Unclosed '---' frontmatter delimiter.")

    body = "\n".join(lines[body_start_idx:])
    data: dict[str, str] = {}

    curr_key: str | None = None
    curr_scalar_mode: str | None = None  # '|' or '>'
    curr_scalar_lines: list[str] = []

    def flush_scalar() -> None:
        nonlocal curr_key, curr_scalar_mode, curr_scalar_lines
        if curr_key and curr_scalar_mode:
            if curr_scalar_mode == "|":
                data[curr_key] = "\n".join(curr_scalar_lines).strip()
            else:  # '>'
                data[curr_key] = " ".join(
                    l.strip() for l in curr_scalar_lines if l.strip()
                ).strip()
        curr_key = None
        curr_scalar_mode = None
        curr_scalar_lines = []

    for line in fm_lines:
        if curr_scalar_mode is not None:
            if line.startswith(("  ", "\t")) or line == "":
                indent = (
                    2 if line.startswith("  ") else 1 if line.startswith("\t") else 0
                )
                curr_scalar_lines.append(line[indent:])
                continue
            flush_scalar()

        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            if val in ("|", ">", "|-", ">-"):
                curr_key = key
                curr_scalar_mode = val[0]
                curr_scalar_lines = []
            else:
                # Strip matching surrounding quotes if present
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                data[key] = val

    flush_scalar()
    return data, body


def validate_skill_candidate(
    intent: SkillIntent,
    assembled_body: str | None,
    target_is_agent_created: bool,
    target_exists: bool,
    layer_root: Path,
) -> ValidationResult:
    """Run all 6 deterministic admission gates on a proposed skill mutation."""
    findings: list[GateFinding] = []

    # 1. Gate 6: Ownership & Provenance barrier
    if intent.action in ("update", "patch", "remove_file", "delete"):
        if not target_exists:
            findings.append(
                GateFinding(
                    "ownership",
                    "not_found",
                    f"Target skill '{intent.name}' does not exist.",
                )
            )
        elif not target_is_agent_created:
            findings.append(
                GateFinding(
                    "ownership",
                    "self_produced",
                    f"Cannot modify native skill '{intent.name}'; only agent-created skills are mutable.",
                )
            )

    if intent.action == "create":
        if target_exists:
            findings.append(
                GateFinding(
                    "ownership",
                    "already_exists",
                    f"Skill '{intent.name}' already exists.",
                )
            )
        try:
            check_new_name(intent.name)
        except ValueError as exc:
            findings.append(GateFinding("structure", "invalid_name", str(exc)))

    if not intent.reason.strip():
        findings.append(
            GateFinding(
                "provenance",
                "missing_reason",
                "Mutation must provide a non-empty 'reason'.",
            )
        )

    if intent.action != "delete" and not intent.evidence.strip():
        findings.append(
            GateFinding(
                "provenance",
                "missing_evidence",
                "Skill creation or update must provide non-empty 'evidence'.",
            )
        )

    if intent.action == "delete":
        if not intent.absorbed_into:
            findings.append(
                GateFinding(
                    "provenance",
                    "missing_absorbed_into",
                    "Consolidation deletion must specify 'absorbed_into' surviving skill.",
                )
            )
        return ValidationResult(valid=len(findings) == 0, findings=findings)

    if assembled_body is None:
        findings.append(
            GateFinding("structure", "missing_body", "Assembled skill body is missing.")
        )
        return ValidationResult(valid=False, findings=findings)

    # 2. Gate 1: Safety Scanner (skills_guard)
    body_violations = scan_guard(assembled_body)
    for v in body_violations:
        findings.append(
            GateFinding("safety", v["family"], f"Line {v['line']}: {v['snippet']}")
        )

    for rel_path, content in intent.files.items():
        sub_violations = scan_guard(content)
        for v in sub_violations:
            findings.append(
                GateFinding(
                    "safety",
                    v["family"],
                    f"{rel_path}:{v['line']}: {v['snippet']}",
                    file_path=rel_path,
                )
            )

    # 3. Gate 2: Secrets Scanner
    body_secrets = secret_hits(assembled_body)
    if body_secrets:
        findings.append(
            GateFinding(
                "secrets",
                "unredacted_secret",
                f"Found unredacted secret(s) in body: {', '.join(body_secrets)}",
            )
        )

    for rel_path, content in intent.files.items():
        sub_secrets = secret_hits(content)
        if sub_secrets:
            findings.append(
                GateFinding(
                    "secrets",
                    "unredacted_secret",
                    f"Found unredacted secret(s) in {rel_path}: {', '.join(sub_secrets)}",
                    file_path=rel_path,
                )
            )

    # 4. Gate 3: Structure & Frontmatter
    try:
        frontmatter, clean_body = parse_frontmatter(assembled_body)
        if not frontmatter.get("name"):
            findings.append(
                GateFinding(
                    "structure", "missing_name", "Frontmatter must contain 'name'."
                )
            )
        elif frontmatter["name"] != intent.name:
            findings.append(
                GateFinding(
                    "structure",
                    "name_mismatch",
                    f"Frontmatter name '{frontmatter['name']}' != intent '{intent.name}'.",
                )
            )

        desc = frontmatter.get("description", "")
        if not desc:
            findings.append(
                GateFinding(
                    "structure",
                    "missing_description",
                    "Frontmatter must contain 'description'.",
                )
            )
        else:
            if len(desc) > 60:
                findings.append(
                    GateFinding(
                        "completeness",
                        "description_too_long",
                        f"Index description ({len(desc)} chars) exceeds 60-char ceiling.",
                    )
                )
            if (
                not any(k in desc.lower() for k in _TRIGGER_KEYWORDS)
                and '"' not in desc
                and "'" not in desc
            ):
                findings.append(
                    GateFinding(
                        "completeness",
                        "description_missing_trigger",
                        "Description must contain 'when' or a quoted trigger phrase.",
                    )
                )

        cat = frontmatter.get("category", "")
        if cat and cat.lower() not in _ALLOWED_CATEGORIES:
            findings.append(
                GateFinding(
                    "structure",
                    "invalid_category",
                    f"Category '{cat}' is not in allowed list.",
                )
            )

    except ValueError as exc:
        findings.append(GateFinding("structure", "malformed_frontmatter", str(exc)))
        clean_body = assembled_body

    # Validate subfile paths and AST for python
    for rel_path, content in intent.files.items():
        try:
            check_subfile_path(rel_path)
        except ValueError as exc:
            findings.append(
                GateFinding(
                    "structure", "invalid_subfile_path", str(exc), file_path=rel_path
                )
            )

        if rel_path.endswith(".py"):
            try:
                ast.parse(content)
            except SyntaxError as exc:
                findings.append(
                    GateFinding(
                        "structure",
                        "python_syntax_error",
                        f"{rel_path}: {exc}",
                        file_path=rel_path,
                    )
                )

    # Bidirectional pointer check: files referenced in body must exist in files or on disk
    referenced_pointers = {
        m.replace("./", "") for m in _POINTER_RE.findall(assembled_body)
    }
    for ptr in referenced_pointers:
        if (
            ptr not in intent.files
            and not (layer_root / "skills" / intent.name / ptr).is_file()
        ):
            findings.append(
                GateFinding(
                    "structure",
                    "dangling_pointer",
                    f"Pointer '{ptr}' referenced in SKILL.md is missing from subfiles.",
                )
            )

    # 5. Gate 4: Quotas
    if len(assembled_body.encode("utf-8")) > STAGE_MAX_BODY_BYTES:
        findings.append(
            GateFinding(
                "quotas",
                "body_too_large",
                f"Body size exceeds {STAGE_MAX_BODY_BYTES} bytes.",
            )
        )

    if len(intent.files) > STAGE_MAX_FILES:
        findings.append(
            GateFinding(
                "quotas",
                "too_many_files",
                f"Skill has {len(intent.files)} subfiles (max {STAGE_MAX_FILES}).",
            )
        )

    total_sub_bytes = 0
    for rel_path, content in intent.files.items():
        sub_bytes = len(content.encode("utf-8"))
        if sub_bytes > STAGE_MAX_FILE_BYTES:
            findings.append(
                GateFinding(
                    "quotas",
                    "subfile_too_large",
                    f"Subfile '{rel_path}' exceeds {STAGE_MAX_FILE_BYTES} bytes.",
                    file_path=rel_path,
                )
            )
        total_sub_bytes += sub_bytes

    if total_sub_bytes > STAGE_MAX_FILES_TOTAL_BYTES:
        findings.append(
            GateFinding(
                "quotas",
                "total_subfiles_too_large",
                f"Total subfiles size ({total_sub_bytes}) exceeds {STAGE_MAX_FILES_TOTAL_BYTES} bytes.",
            )
        )

    # 6. Gate 5: Completeness & Altitude
    for ph in _PLACEHOLDERS:
        if ph in assembled_body:
            findings.append(
                GateFinding(
                    "completeness",
                    "placeholder_detected",
                    f"Placeholder token '{ph}' detected in SKILL.md.",
                )
            )

    non_blank_lines = [l for l in clean_body.splitlines() if l.strip()]
    max_lines = get_skill_body_max_lines()
    if len(non_blank_lines) > max_lines:
        findings.append(
            GateFinding(
                "altitude",
                "body_too_long",
                f"Body has {len(non_blank_lines)} non-blank lines (cap: {max_lines}). Move details to references/.",
            )
        )

    if intent.layer == "global":
        # Check repo-agnostic: no machine absolute paths
        for pat in (r"/home/\w+", r"/Users/\w+", r"[A-Za-z]:\\Users\\\w+"):
            if re.search(pat, assembled_body):
                findings.append(
                    GateFinding(
                        "completeness",
                        "not_repo_agnostic",
                        f"Global skill contains machine-specific absolute path pattern '{pat}'.",
                    )
                )

    return ValidationResult(valid=len(findings) == 0, findings=findings)
