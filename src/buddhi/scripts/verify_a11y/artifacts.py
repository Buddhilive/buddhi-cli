from __future__ import annotations

import datetime as dt
import re
import subprocess
from collections.abc import Generator
from pathlib import Path

from buddhi.scripts.verify_a11y.models import (
    ARTIFACTS,
    MARKUP_SUFFIXES,
    SCRIPT_SUFFIXES,
    SKIP_DIRS,
    SOURCE_SUFFIXES,
    GateFinding,
    ResolvedArtifacts,
)

PLACEHOLDER = re.compile(
    r"\[(YYYY|AAAA|MM/DD|DD/MM|e\.g\.|Ex:|Who|Link|Date|Quem|Data|Escreva|Write)",
    re.IGNORECASE,
)
CODE_SAMPLE = re.compile(
    r"(<(pre|code)\b[^>]*>)(.*?)(</\2\s*>)", re.IGNORECASE | re.DOTALL
)
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)
LINE_COMMENT = re.compile(r"^[ \t]*//[^\n]*", re.MULTILINE)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

SIGN_OFF = (
    ("risk owner", r"(Risk Owner|Dono do Risco)"),
    ("approver", r"(Approved by|Aprovado por)"),
    ("tracking issue", r"(Tracking Issue|Issue de Rastreio)"),
)


def git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return out.stdout.strip() if out.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def source_files(root: Path, src: Path) -> Generator[Path, None, None]:
    for path in src.rglob("*"):
        if path.is_file() and path.suffix.lower() in SOURCE_SUFFIXES:
            try:
                rel_parts = path.relative_to(root).parts
            except ValueError:
                rel_parts = path.parts
            if not any(part in SKIP_DIRS for part in rel_parts):
                yield path


def read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def without_code_samples(text: str | None) -> str | None:
    if text is None:
        return None
    return CODE_SAMPLE.sub(
        lambda m: m.group(1) + re.sub(r"[^\n]", " ", m.group(3)) + m.group(4), text
    )


def without_comments(text: str | None, suffix: str) -> str | None:
    if text is None:
        return None
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    if suffix in SCRIPT_SUFFIXES or suffix in (".css", ".scss"):
        text = BLOCK_COMMENT.sub(blank, text)
    if suffix in SCRIPT_SUFFIXES:
        text = LINE_COMMENT.sub(blank, text)
    if suffix in MARKUP_SUFFIXES:
        text = HTML_COMMENT.sub(blank, text)
    return text


def scannable(path: Path) -> str | None:
    return without_comments(without_code_samples(read(path)), path.suffix.lower())


def body_of(report: Path) -> str:
    text = read(report) or ""
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith(">"))


def resolve_artifacts(root: Path, report_dir: Path | None = None) -> ResolvedArtifacts:
    search_dirs = []
    if report_dir:
        search_dirs.append(report_dir)
    search_dirs.extend([root, root / ".buddhi" / "a11y"])

    # Also search any active spec dir under .buddhi/specs/*
    specs_root = root / ".buddhi" / "specs"
    if specs_root.is_dir():
        for d in specs_root.iterdir():
            if d.is_dir() and d.name != "done":
                search_dirs.append(d)

    def find_file(name: str) -> Path | None:
        for d in search_dirs:
            p = d / name
            if p.is_file():
                return p
        return None

    return ResolvedArtifacts(
        report_path=find_file("REPORT.md"),
        exceptions_path=find_file("EXCEPTIONS.md"),
        decisions_path=find_file("A11Y-DECISIONS.md"),
    )


def check_report_freshness(
    root: Path, report: Path, src: Path, findings: list[GateFinding]
) -> None:
    try:
        src_rel = str(src.relative_to(root)) if src != root else "."
    except ValueError:
        src_rel = "."

    last_ui = git(root, "log", "-1", "--format=%cI", "--", src_rel)
    last_report = git(root, "log", "-1", "--format=%cI", "--", report.name)
    if last_ui and last_report:
        if last_report < last_ui:
            findings.append(
                GateFinding(
                    "ERROR",
                    "freshness",
                    f"REPORT.md (last commit {last_report[:10]}) is older than the last "
                    f"interface change ({last_ui[:10]}). Revisit the entries that change affects.",
                )
            )
        return
    newest = max((p.stat().st_mtime for p in source_files(root, src)), default=None)
    if newest and report.stat().st_mtime < newest:
        findings.append(
            GateFinding(
                "ERROR",
                "freshness",
                "REPORT.md is older than the most recently modified source file.",
            )
        )


def status_claims_pass(body: str) -> bool:
    status = re.search(
        r"(?:Compliance Status|Status de Conformidade):?\*{0,2}[ \t]*(.*)",
        body,
        re.IGNORECASE,
    )
    value = status.group(1).strip() if status else ""
    conditional = re.search(r"CONDITIONAL|CONDICIONAL", value, re.IGNORECASE)
    return bool(
        not conditional
        and (re.search(r"\bPASS\b", value, re.IGNORECASE) or "✅" in value)
    )


def check_report_status(report: Path, findings: list[GateFinding]) -> None:
    body = body_of(report)
    unchecked = len(re.findall(r"^\s*-\s*\[\s\]", body, re.MULTILINE))
    failed = len(re.findall(r"^\s*-\s*\[!\]", body, re.MULTILINE))
    partial = len(re.findall(r"^\s*-\s*\[~\]", body, re.MULTILINE))

    field = re.search(
        r"(?:Compliance Status|Status de Conformidade):?\*{0,2}[ \t]*(.*)",
        body,
        re.IGNORECASE,
    )
    value = field.group(1).strip() if field else ""
    if not value:
        findings.append(
            GateFinding(
                "ERROR",
                "report-status",
                "REPORT.md has no Compliance Status field — fill it from templates/REPORT.md.",
            )
        )
        return
    if value.count("|") >= 2:
        findings.append(
            GateFinding(
                "ERROR",
                "report-status",
                "REPORT.md still carries the template's status placeholder "
                "(the PASS | CONDITIONAL | FAIL menu). Declare one status.",
            )
        )
        return

    if status_claims_pass(body) and (unchecked or failed or partial):
        findings.append(
            GateFinding(
                "ERROR",
                "report-status",
                f"REPORT.md claims PASS while carrying {unchecked} unverified, "
                f"{partial} partial and {failed} failed checkpoints. "
                "Status must be CONDITIONAL until they are closed.",
            )
        )
    if failed:
        findings.append(
            GateFinding(
                "WARN",
                "report-status",
                f"{failed} checkpoint(s) marked [!] (verified and failed) — "
                "fix them or open an EXCEPTIONS.md entry.",
            )
        )


def check_report_independence(report: Path, findings: list[GateFinding]) -> None:
    body = body_of(report)
    field = re.search(
        r"(?:Verification Independence|Independência da Verificação):?\*{0,2}[ \t]*(.*)",
        body,
        re.IGNORECASE,
    )
    if not field:
        findings.append(
            GateFinding(
                "ERROR",
                "independence",
                "REPORT.md has no Verification Independence field. Add it from "
                "templates/REPORT.md and declare who reproduced the automated checkpoints "
                "(A11Y.md §2, Independent Verification).",
            )
        )
        return

    value = field.group(1).strip()
    levels = [
        name
        for name in ("cross-agent", "fresh-context", "self-reported")
        if name in value.lower()
    ]
    if len(levels) != 1:
        findings.append(
            GateFinding(
                "ERROR",
                "independence",
                "REPORT.md does not declare exactly one verification level — expected "
                f"cross-agent, fresh-context or self-reported, found {len(levels)}. An untouched template menu counts as undeclared.",
            )
        )
        return

    level = levels[0]
    if level == "self-reported":
        if status_claims_pass(body):
            findings.append(
                GateFinding(
                    "ERROR",
                    "independence",
                    "REPORT.md claims PASS on self-reported verification — the agent that "
                    "generated the code is the only witness that it conforms. Re-run the "
                    "automated checkpoints in a fresh session (or with another agent), or "
                    "lower the status to CONDITIONAL.",
                )
            )
        else:
            findings.append(
                GateFinding(
                    "WARN",
                    "independence",
                    "Verification is self-reported: the generating agent checked its own "
                    "output. Ceiling is CONDITIONAL. A new chat over this project, without "
                    "the conversation that produced the code, raises it to fresh-context.",
                )
            )

    if re.fullmatch(
        r"(cross-agent|fresh-context|self-reported)\W*", value, re.IGNORECASE
    ):
        findings.append(
            GateFinding(
                "WARN",
                "independence",
                f"Verification level is '{level}' but nobody is named. Record which "
                "model/agent and which session reproduced the checkpoints — an "
                "unattributed level is not reproducible evidence.",
            )
        )


def check_report_gate(report: Path, findings: list[GateFinding]) -> str | None:
    body = body_of(report)
    field = re.search(
        r"(?:Static gate|Gate estático)[^:\n]*:\*{0,2}[ \t]*(.*)", body, re.IGNORECASE
    )
    if not field:
        findings.append(
            GateFinding(
                "ERROR",
                "gate-declared",
                "REPORT.md has no Static gate field. Add it from templates/REPORT.md and "
                "record this run's outcome (A11Y.md §2, Static Gate).",
            )
        )
        return None
    value = field.group(1).strip()
    if value.count("|") >= 2:
        findings.append(
            GateFinding(
                "ERROR",
                "gate-declared",
                "REPORT.md still carries the template's Static gate menu "
                "(PASS | FAIL | NOT RUN). Declare this run's outcome.",
            )
        )
        return None
    return value


def check_report_standard_version(report: Path, findings: list[GateFinding]) -> None:
    body = body_of(report)
    field = re.search(
        r"(?:Standard version|Versão do padrão)[^:\n]*:\*{0,2}[ \t]*(.*)",
        body,
        re.IGNORECASE,
    )
    if not field:
        findings.append(
            GateFinding(
                "WARN",
                "standard-version",
                "REPORT.md does not name the A11Y.md version it was verified against. Add the "
                "Standard version field from templates/REPORT.md — the Version line at the top of "
                "A11Y.md — so the evidence can be re-read against the rules in force.",
            )
        )
        return
    value = field.group(1).strip()
    if (
        not value
        or PLACEHOLDER.search(value)
        or not re.search(r"\b\d+\.\d+\.\d+\b", value)
    ):
        findings.append(
            GateFinding(
                "ERROR",
                "standard-version",
                "REPORT.md carries the Standard version field but no version (x.y.z) — copy it "
                "from the Version line at the top of the A11Y.md this project follows.",
            )
        )


def exception_entries(path: Path | None) -> list[tuple[str, str]]:
    if not path or not path.is_file():
        return []
    text = read(path) or ""
    blocks = re.split(
        r"^#{2,4}\s+\d+\.\s*(?:Basic Details|Detalhes Básicos)",
        text,
        flags=re.MULTILINE,
    )[1:]
    entries = []
    for i, block in enumerate(blocks, 1):
        entry_id = re.search(r"(?:Exception ID|ID da Exceção):\*{0,2}[ \t]*(.*)", block)
        label = (entry_id.group(1).strip() if entry_id else f"entry #{i}")[:40]
        if label and not PLACEHOLDER.search(label):
            entries.append((label, block))
    return entries


def missing_fields(block: str) -> list[str]:
    missing = []
    for field, pattern in SIGN_OFF:
        m = re.search(pattern + r":\*{0,2}[ \t]*(.*)", block)
        if not m or not m.group(2).strip() or PLACEHOLDER.search(m.group(2)):
            missing.append(field)
    return missing


def expiry_of(block: str) -> dt.date | None:
    expiry = re.search(
        r"(?:Expiry|Expiração)[^:\n]*:\*{0,2}[ \t]*\[?(\d{4}-\d{2}-\d{2})", block
    )
    return dt.date.fromisoformat(expiry.group(1)) if expiry else None


def check_exceptions(path: Path | None, findings: list[GateFinding]) -> None:
    if not path or not path.is_file():
        return
    today = dt.datetime.now(dt.timezone.utc).date()
    for label, block in exception_entries(path):
        for field in missing_fields(block):
            findings.append(
                GateFinding("ERROR", "exceptions", f"{label}: missing {field}.")
            )
        date = expiry_of(block)
        if not date:
            findings.append(
                GateFinding(
                    "ERROR",
                    "exceptions",
                    f"{label}: missing or unparseable expiry date (use YYYY-MM-DD).",
                )
            )
        elif date < today:
            findings.append(
                GateFinding(
                    "ERROR",
                    "exceptions",
                    f"{label}: expired on {date} — review, fix or consciously renew it.",
                )
            )
        elif (date - today).days <= 14:
            findings.append(
                GateFinding(
                    "WARN",
                    "exceptions",
                    f"{label}: expires in {(date - today).days} day(s).",
                )
            )


def check_gitignore(root: Path, findings: list[GateFinding]) -> None:
    gitignore = root / ".gitignore"
    if not gitignore.is_file():
        return
    patterns = [
        l.strip()
        for l in (read(gitignore) or "").splitlines()
        if l.strip() and not l.startswith("#")
    ]
    for artifact in ARTIFACTS:
        for pattern in patterns:
            if pattern.strip("/") == artifact or pattern in ("*.md", "**/*.md"):
                findings.append(
                    GateFinding(
                        "ERROR",
                        "gitignore",
                        f"{artifact} is excluded by .gitignore rule '{pattern}'. Project artifacts must be versioned.",
                    )
                )
                break
