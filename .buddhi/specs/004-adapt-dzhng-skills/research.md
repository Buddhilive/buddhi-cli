# Research & Upstream Analysis: `dzhng/skills` Adaptation

## 1. Upstream Project Overview
- **Repository**: [https://github.com/dzhng/skills](https://github.com/dzhng/skills)
- **Tag / Package**: `@dzhng/skills` v1.0.0
- **Author**: David Zhang
- **License**: MIT License (`Copyright (c) 2026 David Zhang`)

## 2. Upstream License Analysis
The project is licensed under the permissive MIT License. Full text:
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
In addition, the following sub-attributions are noted:
- Matt Pocock: `retro` skill (MIT License) and the "fog of war" / "discovering the map" concepts
- Thariq: "fog of war" and "discovering the map" concepts
- wheresryan22: `Anatomy` skill, adapted as `isometric-motion`
- helloianneo: `ian-xiaohei-illustrations`, adapted as `xiaohei-illustrations`

## 3. Skill Categorization and Adaptation Matrix

### A. 23 SDD-Complementary Skills (Scaffolded during `buddhi init`)
1. `audit-agents`: Evaluates `AGENTS.md` against 5 longevity/clarity tests.
2. `audit-choices`: Writes unprompted agent architectural decisions to `.buddhi/specs/<branch>/choices.md` (`sound`, `unsound`, `needs-user`).
3. `audit-performance`: Bounded-work and forward-progress runtime performance audits.
4. `audit-tests`: Test contract mapping and redundancy elimination.
5. `auto-research`: Empirical parameter tuning producing `.buddhi/specs/<branch>/research.md`.
6. `close-spec`: Archives `.buddhi/specs/<branch>/` into `.buddhi/specs/done/<branch>/` as a durable architectural rationale.
7. `code-review`: 26-point engineering review checklist.
8. `compare-screenshots`: Visual telemetry and reference-vs-candidate parity diffing via `buddhi scripts visual-parity-diff`.
9. `design-with-images`: Visual concept exploration with Antigravity `image-generator` subagent and iterative matching.
10. `eli5`: Plain-language explanation of any spec or diff.
11. `eval-skills`: Blind subagent skill evaluations and gap-driven refinement.
12. `explore-unknowns`: 4-quadrant unknown walk with 6 stage guides prior to `/specify`.
13. `handoff-spec`: Mid-implementation session handoff inside `.buddhi/specs/<branch>/`.
14. `marketing-pages`: Page-class rulebook and audits for web applications.
15. `preview-shots`: Cross-platform image previewing (Windows, macOS, Linux).
16. `ratchet-files`: 8,000-token source file ceiling enforced via `buddhi scripts check-file-size`.
17. `refactor-clean`: Clean structural refactoring with complete rename sweeps.
18. `retro`: Post-coding retrospective prioritizing automated checks over prose rules.
19. `review`: Sequenced closeout pass (`refactor-clean` -> `code-review` -> `write-docs`).
20. `screenshot-critique`: Unprimed subagent visual critique verified via `buddhi scripts receipts`.
21. `write-docs`: Markdown documentation hygiene (principles and pointers, not mirrors).
22. `write-skills`: Authoring and simplifying Antigravity `SKILL.md` files.
23. `write-tests`: Behavioral tracer-bullet test authoring.

### B. 5 Enhanced SDD Lifecycle Skills
- `/specify`: References upstream `/explore-unknowns` and `/auto-research` for pre-spec discovery.
- `/spec-plan`: Incorporates multi-perspective bias evaluation (fewest slices vs risk-first vs seam quality).
- `/tasks`: Organizes independently testable user stories with fog-of-war slicing.
- `/implement`: Incorporates periodic maintenance checkpoints, `/review`, and `/audit-choices`.
- `/verify`: Incorporates visual verification gates (`/compare-screenshots`, `/screenshot-critique`) and `/close-spec` prompt.

### C. 5 Custom Graphics Skills (Installed via `buddhi skills`)
- `renderer`: GPU rendering architecture rules (TypeGPU/WebGPU).
- `launch-video`: Motion-graphics launch video production.
- `cinematic-shot`: Oblique macro hero shots and motivated UI camera drift.
- `isometric-motion`: Interactive isometric technical diagrams and WebGL animations.
- `xiaohei-illustrations`: Conceptual 16:9 monochrome editorial illustrations.

### D. 3 CLI Supportive Scripts (Under `buddhi scripts`)
- `check-file-size`: Git-tracked source file token ratchet.
- `visual-parity-diff`: Pure Python PNG decoder/encoder and visual diffing.
- `receipts`: Deterministic critique report and SHA-256 verifier.

