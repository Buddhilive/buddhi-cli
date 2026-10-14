# Acknowledgments

`buddhi-cli` incorporates concepts, skills, rules, and contrast-checking logic adapted from the following open-source projects:

## anti-slop

- **Repository**: [https://github.com/miqdadbadjuber/anti-slop](https://github.com/miqdadbadjuber/anti-slop)
- **Author**: Miqdad Badjuber
- **License**: MIT License

### Description & Adapted Components

The `anti-slop` filter prevents AI coding agents from generating generic, low-effort UI designs, marketing prose, and unnecessary code comments. `buddhi-cli` adapts the `anti-slop` suite into the Google Antigravity harness conventions:
- **Skills**: Six specialized skills scaffolded during `buddhi init` (`antislop`, `antislop-ui`, `antislop-copywriting`, `antislop-human`, `antislop-layoutmobile`, `antislop-code`).
- **Rules**: An always-on Antigravity routing rule (`.agents/rules/antislop.md`).
- **CLI Scripts**: Standalone Python ports of the WCAG 2.x contrast verification script (`buddhi scripts contrast`) and the global mode configuration utility (`buddhi scripts antislop-mode`).
- **MCP Tool**: The `check_contrast` tool integrated into the Buddhi MCP server.

We express our gratitude to Miqdad Badjuber and contributors for creating and sharing the `anti-slop` project.

---

### Upstream MIT License (`anti-slop`)

```text
MIT License

Copyright (c) 2026 Miqdad Badjuber (antislop)

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## skills (`dzhng/skills`)

- **Repository**: [https://github.com/dzhng/skills](https://github.com/dzhng/skills)
- **Author**: David Zhang
- **License**: MIT License

### Description & Adapted Components

The `dzhng/skills` project provides reusable agent skills for AI coding agents functioning as autonomous software factories. `buddhi-cli` adapts these skills into Google Antigravity harness conventions, grounding them in the code graph and complementing the Spec-Driven Development (SDD) workflow:
- **SDD-Complementary Skills**: 23 specialized agent skills scaffolded during `buddhi init`:
  - *Discovery & Research*: `explore-unknowns` (4-quadrant unknown walk), `auto-research` (progressive hypothesis testing).
  - *Implementation, Refactoring & Testing*: `refactor-clean` (clean structural refactoring), `write-tests` (tracer-bullet test authoring), `audit-tests` (test boundary mapping), `audit-performance` (runtime efficiency checks), `ratchet-files` (source file size ratchet), `write-docs` (markdown documentation principles), `marketing-pages` (marketing site architecture).
  - *Review, Decision Audit & Spec Lifecycle*: `code-review` (26-point engineering review), `review` (sequenced closeout pass), `audit-choices` (recording unprompted agent architectural choices into `.buddhi/specs/<branch>/choices.md`), `handoff-spec` (in-flight session handoffs), `close-spec` (spec archiving into `.buddhi/specs/done/<branch>/`), `eli5` (plain-language spec/diff explanations), `retro` (session retrospectives).
  - *Visual Review*: `design-with-images` (visual concept generation via Antigravity `image-generator`), `compare-screenshots` (objective pixel/edge/scene diffing), `screenshot-critique` (unprimed subagent visual checks), `preview-shots` (cross-platform image viewing).
  - *Authoring*: `write-skills` (skill authoring rulebook), `eval-skills` (subagent skill evaluation), `audit-agents` (AGENTS.md longevity audit).
- **CLI Scripts**: Pure Python 3.10+ stdlib utilities integrated under `buddhi scripts`:
  - `buddhi scripts check-file-size`: Git-tracked source file token ratchet (default 8,000 tokens / 32 KB).
  - `buddhi scripts visual-parity-diff`: Pure Python PNG codec, solo scene metrics, and pair diffing.
  - `buddhi scripts receipts`: Deterministic critique report claim verifier and SHA-256 artifact validator.

### Sub-Attributions & Gratitude

We express our gratitude to David Zhang and upstream contributors:
- **Matt Pocock**: For the `retro` skill (MIT License, Copyright (c) 2026 Matt Pocock) and the "fog of war" / "discovering the map" concepts.
- **Thariq**: For the "fog of war" and "discovering the map" concepts that helped shape iterative agent specification and slicing.

---

### Upstream MIT License (`dzhng/skills`)

```text
MIT License

Copyright (c) 2026 David Zhang

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
