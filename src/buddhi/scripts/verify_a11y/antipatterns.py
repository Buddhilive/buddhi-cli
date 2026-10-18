from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

from buddhi.scripts.verify_a11y.artifacts import (
    exception_entries,
    line_of,
    missing_fields,
    read,
    scannable,
    source_files,
)
from buddhi.scripts.verify_a11y.models import (
    CHOICE_CHECKS,
    SOURCE_CHECKS,
    GateFinding,
)

ATTRS = r"((?:[^>]|=>)*)"
OVERLAY_DOMAINS = (
    "accessibe.com",
    "acsbapp.com",
    "userway.org",
    "audioeye.com",
    "equalweb.com",
    "maxaccess.io",
    "allyable.com",
    "adally.com",
    "accessiway.com",
    "truabilities.com",
)

COMPOSITES = {
    "tablist": ("tab",),
    "listbox": ("option",),
    "tree": ("treeitem",),
    "radiogroup": ("radio",),
    "grid": ("row",),
    "treegrid": ("row",),
    "menu": ("menuitem", "menuitemcheckbox", "menuitemradio"),
    "menubar": ("menuitem", "menuitemcheckbox", "menuitemradio"),
}

NATIVE_CHILDREN = {
    "radiogroup": re.compile(
        r"<input\b[^>]*\btype\s*=\s*[\"']radio[\"']", re.IGNORECASE
    ),
    "grid": re.compile(r"<tr\b", re.IGNORECASE),
    "treegrid": re.compile(r"<tr\b", re.IGNORECASE),
}

REDUNDANT_ROLES = {
    "button": ("button",),
    "nav": ("navigation",),
    "main": ("main",),
    "aside": ("complementary",),
    "ul": ("list",),
    "ol": ("list",),
    "li": ("listitem",),
    "img": ("img",),
    "table": ("table",),
    "article": ("article",),
    "dialog": ("dialog",),
    "progress": ("progressbar",),
    "textarea": ("textbox",),
    "h1": ("heading",),
    "h2": ("heading",),
    "h3": ("heading",),
    "h4": ("heading",),
    "h5": ("heading",),
    "h6": ("heading",),
}

SCRIPT_SUFFIXES = {".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro"}
FINDING_AT = re.compile(r"^(.+?):(\d+) — ")
GATE_FIELD = re.compile(
    r"(?:Gate finding|Achado do gate):\*{0,2}[ \t]*(.*)", re.IGNORECASE
)
DECISION_GATE = re.compile(
    r"\(gate:\s*`([\w-]+)`\s*[·,]\s*`([^`]+)`\s*\)", re.IGNORECASE
)
MARKUP = re.compile(r"[\w:@.-]+\s*[=:]\s*\S.*")
UNSIGNED = re.compile(
    r"^\W*$|^\W*(?:tbd|todo|pending|pendente|awaiting|aguardando|none|nenhum|nenhuma|n/a|a definir|não há|nao ha)\b",
    re.IGNORECASE,
)
AGENT = re.compile(
    r"\b(?:ai|ia|llm|agent|agente|bot|claude|chatgpt|gpt|copilot|gemini|codex)\b",
    re.IGNORECASE,
)
FENCE = re.compile(r"^```.*?^```", re.MULTILINE | re.DOTALL)
HTML_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def check_source_antipatterns(
    root: Path, src: Path, findings: list[GateFinding]
) -> None:
    click_handler = re.compile(
        r"\bon[cC]lick\b|@click\b|\bv-on:click\b|\bon:click\b|\(click\)"
    )
    clickable = re.compile(r"<(div|span)\b" + ATTRS + r">")
    checks = (
        (
            "positive-tabindex",
            re.compile(r"tabindex\s*=\s*[\"'{]?\s*[1-9]", re.IGNORECASE),
            "positive tabindex breaks the natural focus order",
        ),
        (
            "outline-none",
            re.compile(r"outline\s*:\s*(none|0)\s*[;}]|\boutline-none\b"),
            "outline suppressed — pair it with a visible focus indicator that survives forced-colors mode; a box-shadow ring alone disappears there (SC 2.4.7)",
        ),
        (
            "redundant-alert",
            re.compile(
                r"role\s*=\s*[\"']alert[\"'][^>]*aria-live|aria-live[^>]*role\s*=\s*[\"']alert[\"']"
            ),
            'role="alert" already implies aria-live="assertive" — declaring both is ARIA Soup (A11Y.md §6)',
        ),
        (
            "nullified-alt",
            re.compile(
                r"<img\b(?="
                + ATTRS
                + r"\balt\s*=\s*[\"'][^\"']+[\"'])"
                + ATTRS
                + r"(?:\baria-hidden(?:\s*=\s*[\"'{]?\s*true|(?=[\s/>]))|\brole\s*=\s*[\"'](?:presentation|none)[\"'])"
            ),
            'aria-hidden or role="presentation" on an image that carries a non-empty alt cancels it for screen readers while every checker still passes (A11Y.md §6, guide-images.md)',
        ),
        (
            "media-autoplay",
            re.compile(
                r"<(video|audio)\b[^>]*\bautoplay\b(?!\s*[:=]\s*[{\"']?\s*false)",
                re.IGNORECASE,
            ),
            "autoplay declared in the markup cannot be vetoed by prefers-reduced-motion — grant it by script, mute it, and give it a pause mechanism (SC 2.2.2 / 1.4.2, guide-media.md §3)",
        ),
        (
            "overlay",
            re.compile(
                r"(?:src|href)\s*=\s*[\"'][^\"']*(?:"
                + "|".join(re.escape(d) for d in OVERLAY_DOMAINS)
                + r")",
                re.IGNORECASE,
            ),
            "accessibility overlay script — an overlay never fixes the DOM that produced the barrier and conflicts with the assistive technology the person already configured (A11Y.md §6)",
        ),
    )
    for path in source_files(root, src):
        text = scannable(path)
        if text is None:
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        for name, pattern, message in checks:
            for match in pattern.finditer(text):
                level = (
                    "WARN" if name in ("outline-none", "media-autoplay") else "ERROR"
                )
                findings.append(
                    GateFinding(
                        level,
                        name,
                        f"{rel}:{line_of(text, match.start())} — {message}",
                        match.group(0),
                    )
                )
        for match in clickable.finditer(text):
            attrs = match.group(2)
            if not click_handler.search(attrs):
                continue
            where = f"{rel}:{line_of(text, match.start())}"
            if re.search(r"\brole\s*=", attrs) and re.search(
                r"\btabindex\s*=", attrs, re.IGNORECASE
            ):
                findings.append(
                    GateFinding(
                        "WARN",
                        "clickable-div",
                        f"{where} — clickable <{match.group(1)}> replicating a button by hand: verify Enter and Space are handled, or use a native <button> (A11Y.md §6)",
                        match.group(0),
                    )
                )
            else:
                findings.append(
                    GateFinding(
                        "ERROR",
                        "clickable-div",
                        f"{where} — clickable <{match.group(1)}> — use a native <button> (A11Y.md §6)",
                        match.group(0),
                    )
                )


def check_placeholder_labels(
    root: Path, src: Path, findings: list[GateFinding]
) -> None:
    field = re.compile(r"<(input|textarea)\b" + ATTRS + r">")
    skip_types = (
        "hidden",
        "submit",
        "button",
        "reset",
        "checkbox",
        "radio",
        "file",
        "range",
        "color",
        "image",
    )
    for path in source_files(root, src):
        text = scannable(path)
        if text is None or path.suffix in (".css", ".scss", ".js", ".ts"):
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        for match in field.finditer(text):
            attrs = match.group(2)
            if not re.search(r"\bplaceholder\s*=", attrs):
                continue
            kind = re.search(r"\btype\s*=\s*[\"']([\w-]+)", attrs)
            if kind and kind.group(1).lower() in skip_types:
                continue
            if re.search(r"\baria-label(ledby)?\s*=|\btitle\s*=", attrs):
                continue
            if re.search(r"(?<![:\w])id\s*=\s*\{", attrs) or re.search(
                r":id\s*=|v-bind:id", attrs
            ):
                continue
            id_match = re.search(r"(?<![:\w-])id\s*=\s*[\"']([^\"'{}]+)[\"']", attrs)
            if id_match and re.search(
                r"\b(?:for|htmlFor)\s*=\s*[\"']"
                + re.escape(id_match.group(1))
                + r"[\"']",
                text,
            ):
                continue
            before = text[: match.start()]
            if before.rfind("<label") > before.rfind("</label>"):
                continue
            findings.append(
                GateFinding(
                    "ERROR",
                    "placeholder-label",
                    f"{rel}:{line_of(text, match.start())} — <{match.group(1)}> labeled only by its placeholder. The label disappears while typing; give it a visible <label> (A11Y.md §6)",
                    match.group(0),
                )
            )


def check_half_climbed(root: Path, src: Path, findings: list[GateFinding]) -> None:
    for path in source_files(root, src):
        text = scannable(path)
        if text is None or path.suffix in (".css", ".scss"):
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        roles = set(re.findall(r"\brole\s*=\s*[\"']([\w-]+)[\"']", text))
        for parent, children in COMPOSITES.items():
            native = NATIVE_CHILDREN.get(parent)
            if (
                parent in roles
                and not any(child in roles for child in children)
                and not (native and native.search(text))
            ):
                m = re.search(r"\brole\s*=\s*[\"']" + parent + r"[\"']", text)
                pos = m.start() if m else 0
                where = f"{rel}:{line_of(text, pos)}"
                need = "/".join(children)
                if parent == "tablist":
                    findings.append(
                        GateFinding(
                            "ERROR",
                            "half-climbed-aria",
                            f'{where} — role="tablist" with no role="tab" in this file: the mold that survived two releases. Complete the pattern (role="tab", aria-selected, arrow keys) or drop the tablist and keep plain buttons (A11Y.md §6)',
                            f'role="{parent}"',
                        )
                    )
                else:
                    findings.append(
                        GateFinding(
                            "WARN",
                            "half-climbed-aria",
                            f'{where} — role="{parent}" with no role="{need}" in this file. If the children live in another component, fine; otherwise the pattern announces what it does not deliver (A11Y.md §6)',
                            f'role="{parent}"',
                        )
                    )


def check_aria_soup(root: Path, src: Path, findings: list[GateFinding]) -> None:
    redundant = re.compile(r"<(" + "|".join(REDUNDANT_ROLES) + r"|a)\b" + ATTRS + r">")
    dup_label = re.compile(
        r"<(a|button)\b"
        + ATTRS
        + r"\baria-label\s*=\s*[\"']([^\"']+)[\"']"
        + ATTRS
        + r">\s*([^<{]+?)\s*<",
        re.IGNORECASE,
    )
    static_expanded = re.compile(r"\baria-expanded\s*=\s*[\"'](?:true|false)[\"']")
    dynamic_expanded = re.compile(
        r"aria-expanded(?!\s*=\s*[\"'](?:true|false)[\"'])|ariaExpanded"
    )

    files = [(p, scannable(p)) for p in source_files(root, src)]
    toggled = any(
        p.suffix in SCRIPT_SUFFIXES and dynamic_expanded.search(scannable(p) or "")
        for p in source_files(root, root)
    )

    for path, text in files:
        if not text or path.suffix in (".css", ".scss"):
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        for match in redundant.finditer(text):
            tag, attrs = match.group(1).lower(), match.group(2)
            role = re.search(r"\brole\s*=\s*[\"']([\w-]+)[\"']", attrs)
            if not role:
                continue
            if tag == "a":
                if role.group(1) == "link" and re.search(r"\bhref\s*=", attrs):
                    findings.append(
                        GateFinding(
                            "ERROR",
                            "aria-soup",
                            f'{rel}:{line_of(text, match.start())} — role="link" on <a href>: redundant role on a native element (ARIA Soup, A11Y.md §6)',
                            match.group(0),
                        )
                    )
                continue
            if role.group(1) in REDUNDANT_ROLES.get(tag, ()):
                findings.append(
                    GateFinding(
                        "ERROR",
                        "aria-soup",
                        f'{rel}:{line_of(text, match.start())} — role="{role.group(1)}" on <{tag}>: redundant role on a native element (ARIA Soup, A11Y.md §6)',
                        match.group(0),
                    )
                )
        for match in dup_label.finditer(text):
            label, visible = match.group(3), match.group(5)
            if (
                re.sub(r"\s+", " ", label).strip().lower()
                == re.sub(r"\s+", " ", visible).strip().lower()
            ):
                findings.append(
                    GateFinding(
                        "WARN",
                        "aria-soup",
                        f"{rel}:{line_of(text, match.start())} — aria-label repeats the visible text of <{match.group(1)}>. Drop it: when the two drift apart it becomes an SC 2.5.3 failure (ARIA Soup, A11Y.md §6)",
                        match.group(0),
                    )
                )
        if not toggled:
            for match in static_expanded.finditer(text):
                findings.append(
                    GateFinding(
                        "WARN",
                        "aria-soup",
                        f"{rel}:{line_of(text, match.start())} — aria-expanded hardcoded and no script in the project ever toggles it: a state that never updates is worse than none (SC 4.1.2, ARIA Soup, A11Y.md §6)",
                        match.group(0),
                    )
                )


def check_orphaned_aria(root: Path, src: Path, findings: list[GateFinding]) -> None:
    relations = re.compile(
        r'\b(aria-controls|aria-labelledby|aria-describedby|aria-activedescendant)\s*=\s*"([^"{}]+)"'
    )
    declared = re.compile(r'\bid\s*=\s*"([^"{}]+)"')
    for path in source_files(root, src):
        text = scannable(path)
        if text is None:
            continue
        try:
            rel = path.relative_to(root)
        except ValueError:
            rel = path
        ids = set(declared.findall(text))
        for match in relations.finditer(text):
            attribute, value = match.group(1), match.group(2)
            for target in value.split():
                if target not in ids:
                    findings.append(
                        GateFinding(
                            "WARN",
                            "orphaned-aria",
                            f'{rel}:{line_of(text, match.start())} — {attribute}="{target}" has no matching id in this file. If the target lives in another component, make sure the id is passed down rather than generated on both sides (A11Y.md §6).',
                            match.group(0),
                        )
                    )


def filled(field: re.Match | None) -> bool:
    return bool(
        field and field.group(1).strip() and not field.group(1).lstrip().startswith("[")
    )


def as_path(token: str) -> str:
    path = token.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path.strip("/")


def gate_exceptions(
    root: Path, src: Path, exceptions_path: Path | None, findings: list[GateFinding]
) -> list[tuple[str, list[str], list[str], str, dt.date | None, bool]]:
    if not exceptions_path or not exceptions_path.is_file():
        return []
    entries = exception_entries(exceptions_path)
    stray = sum(
        1 for m in GATE_FIELD.finditer(read(exceptions_path) or "") if filled(m)
    ) - sum(1 for _, block in entries if filled(GATE_FIELD.search(block)))
    if stray > 0:
        findings.append(
            GateFinding(
                "WARN",
                "registers",
                f"EXCEPTIONS.md has {stray} Gate finding field(s) outside an entry the gate can read. They cover nothing.",
            )
        )
    found = []
    today = dt.datetime.now(dt.timezone.utc).date()
    for label, block in entries:
        field = GATE_FIELD.search(block)
        if field is None or not filled(field):
            continue
        tokens = re.findall(r"`([^`]+)`", field.group(1))
        checks = [t for t in tokens if t in SOURCE_CHECKS]
        files, strangers = [], []
        for name in (as_path(t) for t in tokens if t not in SOURCE_CHECKS):
            for base in (root, src):
                if name and (base / name).is_file():
                    files.append((base / name).relative_to(root).as_posix())
                    break
            else:
                strangers.append(name or "(empty)")
        if not checks or not files or strangers:
            findings.append(
                GateFinding(
                    "WARN",
                    "registers",
                    f"{label}: the Gate finding field must name at least one check the gate runs and each file it covers, in backticks (`clickable-div` in `src/legacy/Grid.tsx`)"
                    + (
                        f"; not a file in this project: {', '.join(strangers)}"
                        if strangers
                        else ""
                    )
                    + ". A directory would cover a whole rule (EXCEPTIONS.md rule 3).",
                )
            )
            if not checks or not files:
                continue
        unsigned = [
            f
            for f, pattern in (
                ("risk owner", r"(Risk Owner|Dono do Risco)"),
                ("approver", r"(Approved by|Aprovado por)"),
                ("tracking issue", r"(Tracking Issue|Issue de Rastreio)"),
            )
            if (m := re.search(pattern + r":\*{0,2}[ \t]*(.*)", block))
            and UNSIGNED.search(m.group(2).strip())
        ]
        approver = re.search(r"(?:Approved by|Aprovado por):\*{0,2}[ \t]*(.*)", block)
        if approver and AGENT.search(approver.group(1)) and "approver" not in unsigned:
            unsigned.append("approver")
        if unsigned and not missing_fields(block):
            findings.append(
                GateFinding(
                    "WARN",
                    "registers",
                    f"{label} names a gate finding but its {' and '.join(unsigned)} name(s) nobody who can sign ('pending', 'TBD', 'none', an AI agent): it covers nothing until a person signs.",
                )
            )
        date_val = re.search(
            r"(?:Expiry|Expiração)[^:\n]*:\*{0,2}[ \t]*\[?(\d{4}-\d{2}-\d{2})", block
        )
        date = dt.date.fromisoformat(date_val.group(1)) if date_val else None
        in_force = (
            not missing_fields(block)
            and not unsigned
            and date is not None
            and date >= today
        )
        found.append(
            (
                label,
                checks,
                files,
                (approver.group(1).strip() if approver else "")[:40],
                date,
                in_force,
            )
        )
    return found


def gate_decisions(
    decisions_path: Path | None, findings: list[GateFinding]
) -> list[tuple[int, str, str]]:
    if not decisions_path or not decisions_path.is_file():
        return []
    blank = lambda m: re.sub(r"[^\n]", " ", m.group(0))
    text = FENCE.sub(blank, HTML_COMMENT.sub(blank, read(decisions_path) or ""))
    heading = re.search(r"^##\s+(?:Decisions|Decisões)\b", text, re.MULTILINE)
    if not heading:
        return []
    found = []
    for n, raw in enumerate(
        text[heading.start() :].split("\n"), line_of(text, heading.start())
    ):
        if raw.lstrip().startswith(">") or "~~" in raw:
            continue
        for match in DECISION_GATE.finditer(raw):
            check, markup = match.group(1), match.group(2).strip()
            if check not in SOURCE_CHECKS:
                findings.append(
                    GateFinding(
                        "WARN",
                        "registers",
                        f"A11Y-DECISIONS.md:{n} names `{check}`, which is not a check this gate runs.",
                    )
                )
            elif check not in CHOICE_CHECKS:
                findings.append(
                    GateFinding(
                        "WARN",
                        "registers",
                        f"A11Y-DECISIONS.md:{n} names `{check}`, which flags a failure, not a choice between conformant alternatives. Fix it, or accept it in EXCEPTIONS.md with an owner, an approver and an expiry.",
                    )
                )
            elif not MARKUP.fullmatch(markup):
                findings.append(
                    GateFinding(
                        "WARN",
                        "registers",
                        f'A11Y-DECISIONS.md:{n} names `{markup}`, which is not one attribute or declaration with its value (`role="list"`, `outline: none`). A fragment would cover every `{check}` finding in the project.',
                    )
                )
            else:
                found.append((n, check, markup))
    return found


def chooses(markup: str, subject: str) -> bool:
    norm = lambda t: re.sub(
        r"\s+", " ", re.sub(r"\s*([=:])\s*", r"\1", t.replace("'", '"'))
    )
    return bool(
        re.search(
            r"(?:^|(?<=[\s<{;,(]))" + re.escape(norm(markup)) + r"(?![\w-])",
            norm(subject),
        )
    )


def apply_registers(
    root: Path,
    src: Path,
    exceptions_path: Path | None,
    decisions_path: Path | None,
    findings: list[GateFinding],
) -> None:
    exceptions = gate_exceptions(root, src, exceptions_path, findings)
    decisions = gate_decisions(decisions_path, findings)
    if not exceptions and not decisions:
        return
    used: set[int] = set()
    for i, f in enumerate(findings):
        at = FINDING_AT.match(f.message)
        if f.level == "REGISTERED" or f.check not in SOURCE_CHECKS or not at:
            continue
        rel = Path(at.group(1)).as_posix()
        record = None
        for k, (label, checks, files, approver, date, in_force) in enumerate(
            exceptions
        ):
            if f.check in checks and rel in files:
                used.add(k)
                if in_force and not record:
                    record = (
                        f"EXCEPTIONS.md {label}, approved by {approver}, until {date}"
                    )
        if not record and f.subject:
            record = next(
                (
                    f"A11Y-DECISIONS.md:{n}"
                    for n, chosen, markup in decisions
                    if chosen == f.check and chooses(markup, f.subject)
                ),
                None,
            )
        if record:
            findings[i] = GateFinding(
                "REGISTERED", f.check, f"{f.message} [{record}]", f.subject
            )
    scanned = src.resolve()
    for k, (label, checks, files, _, _, in_force) in enumerate(exceptions):
        if (
            in_force
            and k not in used
            and any((root / f).resolve().is_relative_to(scanned) for f in files)
        ):
            findings.append(
                GateFinding(
                    "WARN",
                    "registers",
                    f"{label} covers {', '.join(f'`{c}`' for c in checks)} in {', '.join(files)}, and this run finds none there. If it was fixed, close the exception.",
                )
            )
