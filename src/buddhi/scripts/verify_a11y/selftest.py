from __future__ import annotations

import tempfile
from pathlib import Path

CLEAN_REPORT = """# Report
- **Compliance Status:** ⚠️ CONDITIONAL — screen reader validation pending
- **Verification Independence:** fresh-context — who verified: new session over the repo
- **Static gate (`verify-a11y.py`):** PASS — run on: 2026-09-25
- **Standard version:** 2.1.0
- [x] **Text & UI Contrast:** measured
| body | #1c1b19 | #f7f6f3 | 15.92:1 | 7:1 | ✅ |
- [ ] **Screen reader:** pending
## 3. Behavior and Task Return
- Scenarios run: guide-forms (4/4 passed) · guide-buttons (3/3 passed)
"""
CLEAN_ROW = "| body | #1c1b19 | #f7f6f3 | 15.92:1 | 7:1 | ✅ |"
PASS_REPORT = CLEAN_REPORT.replace(
    "⚠️ CONDITIONAL — screen reader validation pending", "✅ PASS"
).replace(
    "- [ ] **Screen reader:** pending",
    "- [x] **Screen reader:** NVDA 2026.1 + Firefox 141",
)
EXCEPTION_ENTRY = """# Exceptions
### 1. Basic Details
- **Exception ID:** EXT-2026-001
- **Risk Owner:** Ana Lima
- **Approved by:** QA lead
- **Tracking Issue:** https://example.com/issues/1
- **Gate finding:** `clickable-div` in `src/legacy.jsx`
### 4. Resolution Plan and Expiry
- **Expiry (review-by date):** 2999-12-31
"""
LIST_DECISION = '- **Unstyled list** → `<ul role="list">` — Safari drops list semantics under list-style: none (gate: `aria-soup` · `role="list"`). (2026-10-20)\n'

SELF_TEST_CASES = [
    (
        "clean project",
        {
            "src/index.html": '<label for="q">Search</label><input id="q" placeholder="title"><button>Go</button>'
            "<style>.a{color:#1c1b19;background:#f7f6f3}</style>",
            "REPORT.md": CLEAN_REPORT,
        },
        set(),
        set(),
        {
            "clickable-div",
            "placeholder-label",
            "aria-soup",
            "contrast-evidence",
            "gate-declared",
            "standard-version",
            "half-climbed-aria",
            "guide-coverage",
        },
    ),
    (
        "clickable div in four syntaxes, hand-made button warns",
        {
            "src/a.jsx": "<div onClick={() => go()}>x</div>",
            "src/b.vue": '<span @click="go">x</span><div v-on:click="go">y</div>',
            "src/c.svelte": "<div on:click={go}>x</div>",
            "src/d.html": (
                '<div (click)="go()">x</div><div role="button" tabindex="0"'
                ' onclick="go()">y</div>'
            ),
        },
        {"clickable-div", "artifacts"},
        {"clickable-div"},
        set(),
    ),
    (
        "placeholder as the only label",
        {
            "src/f.html": (
                '<input placeholder="E-mail"><input placeholder="ok"'
                ' aria-label="Name"><label>Wrapped <textarea'
                ' placeholder="fine"></textarea></label><label'
                ' for="z">Z</label><input id="z" placeholder="fine">'
            ),
        },
        {"placeholder-label", "artifacts"},
        set(),
        set(),
    ),
    (
        "half-climbed: tablist without tabs fails, menu without items warns",
        {
            "src/t.html": '<div role="tablist"><button>1</button></div>',
            "src/m.html": '<ul role="menu"><li>1</li></ul>',
            "src/ok.html": (
                '<div role="tablist"><button role="tab"'
                ' aria-selected="true">1</button></div>'
            ),
        },
        {"half-climbed-aria", "artifacts"},
        {"half-climbed-aria"},
        set(),
    ),
    (
        "aria soup: redundant roles, duplicated label, static aria-expanded",
        {
            "src/s.html": (
                '<nav role="navigation"></nav><a href="/" role="link">x</a><h2'
                ' role="heading">t</h2><button'
                ' aria-label="Close">Close</button><button'
                ' aria-expanded="false">Menu</button>'
            ),
        },
        {"aria-soup", "artifacts"},
        {"aria-soup"},
        set(),
    ),
    (
        "aria-expanded toggled by script is not soup",
        {
            "src/s.html": '<button aria-expanded="false">Menu</button>',
            "src/s.js": 'btn.setAttribute("aria-expanded", String(open))',
        },
        {"artifacts"},
        set(),
        {"aria-soup"},
    ),
    (
        "aria-expanded toggled by a script outside --src is not soup either",
        {
            "src/s.html": '<button aria-expanded="false">Menu</button>',
            "js/main.js": 'btn.setAttribute("aria-expanded", String(open))',
        },
        {"artifacts"},
        set(),
        {"aria-soup"},
    ),
    (
        "markup quoted in <pre>/<code> is documentation, not a component",
        {
            "src/doc.html": (
                '<p>Avoid <code>role="menu"</code> on site navigation.</p><pre><code>&lt;div'
                ' role="tablist"&gt;</code></pre><pre>\n<div'
                ' role="tablist"><button>1</button></div>\n<div'
                ' onclick="x()">y</div>\n</pre><div role="tablist"><button'
                ' role="tab" aria-selected="true">real</button></div>'
            ),
        },
        {"artifacts"},
        set(),
        {"half-climbed-aria", "clickable-div", "aria-soup"},
    ),
    (
        "comments are documentation, not markup",
        {
            "src/c.tsx": (
                '// role="menu" lives on the Dropdown, with its menuitems\n'
                '{/* aria-live="polite" is implied by role="alert" */}<p'
                ' role="alert">Saved</p>\n'
                "/* outline: none would hide focus */\n"
                'const url = "https://example.com/x";\n'
                '<div role="tablist"><button role="tab"'
                ' aria-selected="true">1</button></div>'
            ),
            "src/c.css": "/* outline: none */ a:focus { outline: 2px solid }",
            "src/h.html": ('<!-- <div onclick="x()">old</div> --><button>ok</button>'),
        },
        {"artifacts"},
        set(),
        {"half-climbed-aria", "redundant-alert", "outline-none", "clickable-div"},
    ),
    (
        (
            "native children satisfy a composite: radios under radiogroup, rows"
            " under grid"
        ),
        {
            "src/r.html": (
                '<fieldset role="radiogroup" aria-label="Plan"><label><input'
                ' type="radio" name="p"> A</label></fieldset><table'
                ' role="grid"><tr><td>1</td></tr></table>'
            ),
        },
        {"artifacts"},
        set(),
        {"half-climbed-aria"},
    ),
    (
        "a comment does not hide the real markup after it",
        {
            "src/m.html": (
                "<!-- the menu below needs menuitems -->\n<ul"
                ' role="menu"><li>1</li></ul>'
            ),
        },
        {"artifacts"},
        {"half-climbed-aria"},
        set(),
    ),
    (
        "standard version: missing field warns",
        {
            "src/index.html": ("<style>.a{color:#1c1b19;background:#f7f6f3}</style>"),
            "REPORT.md": CLEAN_REPORT.replace("- **Standard version:** 2.1.0\n", ""),
        },
        set(),
        {"standard-version"},
        {"gate-declared"},
    ),
    (
        "standard version: placeholder left in place fails",
        {
            "src/index.html": ("<style>.a{color:#1c1b19;background:#f7f6f3}</style>"),
            "REPORT.md": CLEAN_REPORT.replace(
                "- **Standard version:** 2.1.0",
                "- **Standard version:** [e.g. 2.1.0 — the Version line at the"
                " top of A11Y.md]",
            ),
        },
        {"standard-version", "gate-declared"},
        set(),
        set(),
    ),
    (
        "nullified alt: bare JSX aria-hidden and role=presentation",
        {
            "src/i.jsx": (
                '<img alt="Chart" aria-hidden /><img alt="Map"'
                ' role="presentation" /><img alt="" aria-hidden="true" />'
            ),
        },
        {"nullified-alt", "artifacts"},
        set(),
        set(),
    ),
    (
        "overlay vendor script",
        {
            "src/index.html": (
                '<script src="https://cdn.userway.org/widget.js"></script>'
            ),
        },
        {"overlay", "artifacts"},
        set(),
        set(),
    ),
    (
        "contrast: invented ratio fails",
        {
            "src/index.html": ("<style>.a{color:#767676;background:#ffffff}</style>"),
            "REPORT.md": CLEAN_REPORT.replace(
                CLEAN_ROW, "| body | #767676 | #ffffff | 7.20:1 | 7:1 | ✅ |"
            ),
        },
        {"contrast-evidence", "gate-declared"},
        set(),
        set(),
    ),
    (
        "contrast: honest ratio marked passing below floor fails",
        {
            "src/index.html": ("<style>.a{color:#767676;background:#ffffff}</style>"),
            "REPORT.md": CLEAN_REPORT.replace(
                CLEAN_ROW, "| body | #767676 | #ffffff | 4.54:1 | 7:1 | ✅ |"
            ),
        },
        {"contrast-evidence", "gate-declared"},
        set(),
        set(),
    ),
    (
        "contrast: a failing pair recorded honestly only warns",
        {
            "src/index.html": ("<style>.a{color:#767676;background:#ffffff}</style>"),
            "REPORT.md": CLEAN_REPORT.replace(
                CLEAN_ROW, "| body | #767676 | #ffffff | 4.54:1 | 7:1 | ❌ |"
            ),
        },
        set(),
        {"contrast-evidence"},
        {"gate-declared"},
    ),
    (
        "contrast: a sentence mentioning two colors and a floor is not a row",
        {
            "src/index.html": ("<style>.a{color:#1c1b19;background:#f7f6f3}</style>"),
            "REPORT.md": (
                CLEAN_REPORT
                + "\nNote: #8f8f8f and #a6a6a6 are decorative rails, outside the"
                " 7:1 floor.\n"
            ),
        },
        set(),
        set(),
        {"contrast-evidence"},
    ),
    (
        "contrast: checkpoint verified without a single pair fails",
        {
            "src/index.html": "<p>x</p>",
            "REPORT.md": CLEAN_REPORT.replace(CLEAN_ROW, ""),
        },
        {"contrast-evidence", "gate-declared"},
        set(),
        set(),
    ),
    (
        "gate declared PASS while this run finds errors",
        {
            "src/a.html": '<div onclick="x()">x</div>',
            "REPORT.md": CLEAN_REPORT,
        },
        {"gate-declared", "clickable-div"},
        set(),
        set(),
    ),
    (
        "gate declared NOT RUN while running warns",
        {
            "src/index.html": ("<style>.a{color:#1c1b19;background:#f7f6f3}</style>"),
            "REPORT.md": CLEAN_REPORT.replace(
                "PASS — run on: 2026-09-25", "NOT RUN — reason: no shell"
            ),
        },
        set(),
        {"gate-declared"},
        set(),
    ),
    (
        (
            "guide coverage: tabs built by script and a status message warn; a"
            " guide named outside §3 does not count"
        ),
        {
            "src/index.html": (
                '<p role="status"></p><style>.a{color:#1c1b19;background:#f7f6f3}</style>'
            ),
            "src/tabs.js": (
                "list.setAttribute('role', 'tablist');\n"
                "tab.setAttribute('role', 'tab');\n"
            ),
            "REPORT.md": (
                CLEAN_REPORT + "\n## Assessment Notes\n"
                "- guide-tabs-accordion and guide-toasts-notifications: next session\n"
            ),
        },
        set(),
        {"guide-coverage"},
        {"gate-declared"},
    ),
    (
        "guide coverage: a PASS report missing a present component's guide fails",
        {
            "src/index.html": (
                "<dialog open><button>Close</button></dialog><style>.a{color:#1c1b19;background:#f7f6f3}</style>"
            ),
            "REPORT.md": PASS_REPORT,
        },
        {"guide-coverage", "gate-declared"},
        set(),
        set(),
    ),
    (
        (
            "guide coverage: named guides satisfy; quoted, commented and prose"
            " mentions are not components"
        ),
        {
            "src/index.html": (
                '<div role="tablist"><button role="tab"'
                ' aria-selected="true">1</button></div><p>Drag a draggable'
                " card; a popover explains"
                ' it.</p><pre><video src="a.mp4"></video></pre><!-- <dialog'
                " open></dialog>"
                " --><style>.a{color:#1c1b19;background:#f7f6f3}</style>"
            ),
            "REPORT.md": CLEAN_REPORT.replace(
                "guide-forms (4/4 passed)", "guide-tabs-accordion (5/5 passed)"
            ),
        },
        set(),
        set(),
        {"guide-coverage"},
    ),
    (
        (
            "guide coverage: React components, TS generics, custom elements,"
            " data-role and attribute values are not components"
        ),
        {
            "src/a.tsx": (
                "const [d, setD] = useState<Dialog | null>(null)\nconst rows:"
                " Array<Table> = []\nreturn <Table rows={rows}><Form"
                " onSubmit={go} /></Table>"
            ),
            "src/b.html": (
                "<table-row></table-row><video-player></video-player><div"
                ' data-role="tab"></div><img alt="a popover and a tooltip"'
                ' src="x.png"><style>.a{color:#1c1b19;background:#f7f6f3}</style>'
            ),
            "src/c.js": "for (let i = 0; i<b && draggable; i++) {}",
            "REPORT.md": CLEAN_REPORT,
        },
        set(),
        set(),
        {"guide-coverage"},
    ),
    (
        (
            "guide coverage: roles in JSX braces, Vue bindings and object"
            " props, and elements a script creates, are found"
        ),
        {
            "src/a.tsx": (
                '<div role={"tablist"}><button role="tab"'
                ' aria-selected="true">1</button></div>'
            ),
            "src/b.vue": "<template><div :role=\"'tree'\"></div></template>",
            "src/c.js": (
                'h("div", { role: "feed" })\nconst dlg ='
                ' document.createElement("dialog")'
            ),
            "src/index.html": ("<style>.a{color:#1c1b19;background:#f7f6f3}</style>"),
            "REPORT.md": CLEAN_REPORT,
        },
        set(),
        {"guide-coverage"},
        {"gate-declared"},
    ),
    (
        (
            "registers: an exception in force covers its file; the same finding"
            " elsewhere fails"
        ),
        {
            "src/legacy.jsx": "<div onClick={go}>x</div>",
            "src/new.jsx": "<div onClick={go}>y</div>",
            "EXCEPTIONS.md": EXCEPTION_ENTRY,
        },
        {"clickable-div", "artifacts"},
        set(),
        set(),
        {"clickable-div"},
    ),
    (
        "registers: an expired exception covers nothing",
        {
            "src/legacy.jsx": "<div onClick={go}>x</div>",
            "EXCEPTIONS.md": EXCEPTION_ENTRY.replace("2999-12-31", "2020-01-01"),
        },
        {"clickable-div", "exceptions", "artifacts"},
        set(),
        set(),
        set(),
    ),
    (
        "registers: an exception whose finding is gone warns to close it",
        {
            "src/legacy.jsx": "<button onClick={go}>x</button>",
            "EXCEPTIONS.md": EXCEPTION_ENTRY,
        },
        {"artifacts"},
        {"registers"},
        set(),
        set(),
    ),
    (
        (
            "registers: a decision covers the markup it chose across a"
            " multi-line tag; markers in the rules and in comments are not read"
        ),
        {
            "src/l.jsx": (
                '<ul\n  className="plain"\n  role="list">\n  <li>a</li>\n</ul>\n<nav'
                ' role="navigation"></nav>'
            ),
            "A11Y-DECISIONS.md": (
                "# Decisions Log\n## Rules for the AI\n8. Mark it like (gate:"
                ' `aria-soup` · `role="navigation"`).\n## Decisions\n<!--'
                ' (gate: `aria-soup` · `role="navigation"`) -->\n' + LIST_DECISION
            ),
        },
        {"aria-soup", "artifacts"},
        set(),
        set(),
        {"aria-soup"},
    ),
    (
        (
            "registers: a decision cannot cover a failure, the half-climbed"
            " tablist included"
        ),
        {
            "src/a.jsx": "<div onClick={go}>x</div>",
            "src/t.html": '<div role="tablist"><button>1</button></div>',
            "A11Y-DECISIONS.md": (
                "## Decisions\n- **Card** → the whole card is clickable (gate:"
                " `clickable-div` · `onClick`)\n- **Tabs** → buttons only (gate:"
                ' `half-climbed-aria` · `role="tablist"`)\n'
            ),
        },
        {"clickable-div", "half-climbed-aria", "artifacts"},
        {"registers"},
        set(),
        set(),
    ),
    (
        (
            "registers: a decision covers the element the check flagged, not its"
            " neighbour on the same line"
        ),
        {
            "src/a.html": (
                '<nav role="navigation"><ul role="list"><li>a</li></ul></nav>'
            ),
            "A11Y-DECISIONS.md": "## Decisions\n" + LIST_DECISION,
        },
        {"aria-soup", "artifacts"},
        set(),
        set(),
        {"aria-soup"},
    ),
    (
        (
            "registers: a decision matches whole markup only; a bare fragment"
            " covers nothing"
        ),
        {
            "src/a.html": ('<ul><li role="listitem" data-role="list">a</li></ul>'),
            "A11Y-DECISIONS.md": (
                "## Decisions\n"
                + LIST_DECISION
                + "- **Anything** → loose (gate: `aria-soup` · `role`)\n"
            ),
        },
        {"aria-soup", "artifacts"},
        {"registers"},
        set(),
        set(),
    ),
    (
        (
            "registers: a directory, a pending or AI approver and a field"
            " outside the template's shape cover nothing"
        ),
        {
            "src/legacy.jsx": "<div onClick={go}>x</div>",
            "EXCEPTIONS.md": (
                "**Common fields**\n- **Gate finding:** `clickable-div` in"
                " `src/legacy.jsx`\n"
                + EXCEPTION_ENTRY.replace("`src/legacy.jsx`", "`src`").split("\n", 1)[1]
                + EXCEPTION_ENTRY.replace("EXT-2026-001", "EXT-2026-002")
                .replace("QA lead", "pending — awaiting sign-off")
                .split("\n", 1)[1]
                + EXCEPTION_ENTRY.replace("EXT-2026-001", "EXT-2026-003")
                .replace("QA lead", "Claude (AI agent)")
                .split("\n", 1)[1]
            ),
        },
        {"clickable-div", "artifacts"},
        {"registers"},
        set(),
        set(),
    ),
    (
        (
            "registers: ./ and backslash paths, paths from --src, and an entry"
            " renewed after an expired one"
        ),
        {
            "src/legacy.jsx": "<div onClick={go}>x</div>",
            "src/other.jsx": "<div onClick={go}>y</div>",
            "EXCEPTIONS.md": (
                EXCEPTION_ENTRY.replace("2999-12-31", "2020-01-01")
                + EXCEPTION_ENTRY.replace("EXT-2026-001", "EXT-2026-002")
                .replace("`src/legacy.jsx`", "`.\\legacy.jsx` and `./src/other.jsx`")
                .split("\n", 1)[1]
            ),
        },
        {"exceptions", "artifacts"},
        set(),
        {"clickable-div"},
        {"clickable-div"},
    ),
    (
        (
            "registers: a report declaring the gate PASS holds when every"
            " finding is registered"
        ),
        {
            "src/index.html": (
                '<ul role="list"><li>a</li></ul><style>.a{color:#1c1b19;background:#f7f6f3}</style>'
            ),
            "A11Y-DECISIONS.md": "## Decisions\n" + LIST_DECISION,
            "REPORT.md": CLEAN_REPORT,
        },
        set(),
        set(),
        {"gate-declared", "aria-soup"},
        {"aria-soup"},
    ),
]


from collections.abc import Callable
from typing import Any


def run_selftest(runner_func: Callable[..., Any]) -> tuple[int, str]:
    ok = True
    lines = []
    for item in SELF_TEST_CASES:
        name: str = item[0]  # type: ignore[assignment]
        files: dict[str, str] = item[1]  # type: ignore[assignment]
        want_err: set[str] = item[2]  # type: ignore[assignment]
        want_warn: set[str] = item[3]  # type: ignore[assignment]
        forbid: set[str] = item[4]  # type: ignore[assignment]
        want_reg: Any = item[5:]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel, content in files.items():
                path = root / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            res = runner_func(root, root / "src")
            errs = {f.check for f in res.errors}
            warns = {f.check for f in res.warnings}
            regs = {f.check for f in res.registered}
            seen = errs | warns
            missing = (want_err - errs) | (want_warn - warns)
            unexpected = (forbid & seen) | (errs - want_err - want_warn)
            if want_reg:
                missing |= want_reg[0] - regs
                unexpected |= regs - want_reg[0]
            passed = not missing and not unexpected
            ok &= passed
            lines.append(f"  {'OK' if passed else 'FAIL'} {name}")
            if not passed:
                for f in res.findings:
                    lines.append(f"      {f.level} [{f.check}] {f.message[:110]}")
                if missing:
                    lines.append(f"      missing: {sorted(missing)}")
                if unexpected:
                    lines.append(f"      unexpected: {sorted(unexpected)}")
    lines.append(f"self-test: {'PASS' if ok else 'FAIL'}")
    return (0 if ok else 1, "\n".join(lines))
