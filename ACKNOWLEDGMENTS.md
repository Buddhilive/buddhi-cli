# Acknowledgments

`buddhi-cli` incorporates concepts, skills, rules, specifications, and contrast-checking logic adapted from the following open-source projects and architectural standards:

## AutoHarness

- **Repository**: [https://github.com/tigerless-labs/autoharness](https://github.com/tigerless-labs/autoharness)
- **Author**: Ryan / Tigerless Labs
- **License**: MIT License

### Description & Adapted Components

`autoharness` is a self-learning skill layer for AI coding agents that distills procedural knowledge from session episodes, merges overlapping skills, and prunes unused skills with usage-driven graduation. `buddhi-cli` adapts the `autoharness` architecture for Google Antigravity and Spec-Driven Development (SDD):
- **Core Architecture (`src/buddhi/scripts/autoharness/`)**: Deterministic 6-gate admission validator, regex secrets & PII redaction engine with Luhn checksum validation, static AST threat scanner across 6 threat families, cross-platform file locking (`msvcrt`/`fcntl`), atomic file writing, and append-only `.ledger.jsonl` provenance.
- **Sidecar Ownership Protection (`.sidecar.json`)**: Enforcing strict ownership isolation (`created_by: "agent"`) so agent-learning pipelines can never mutate, patch, or delete native harness or human-crafted skills.
- **Probation & Graduation Engine**: Tenure tracking, usage rate graduation, and capacity eviction archiving stale skills to `.agents/skills/.archive/`.
- **FastMCP Tool (`stage_skill`)**: Tool-based intent staging on `buddhi-mcp` with immediate parameter and structure validation.
- **Antigravity Customizations**: Interactive `/learn` skill (`.agents/skills/learn/` with `references/format_spec.md`), always-on rule (`.agents/rules/autoharness.md`), read-only subagents (`.agents/agents/reflector.md` and `curator.md`), and fail-open lifecycle hook (`.agents/hooks/autoharness_hook.py` registered in `hooks.json`).
- **CLI Subcommand Group (`buddhi scripts autoharness`)**: Providing `stage`, `promote`, `validate`, `status`, `capture`, `curate`, `check-links`, and `--selftest`.

We express our gratitude to Ryan and Tigerless Labs for authoring and sharing the `autoharness` project.

---

### Upstream MIT License (`autoharness`)

```text
MIT License

Copyright (c) 2026 ryan

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

## Claude Code Memory

- **Documentation**: [https://code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory)
- **Author**: Anthropic

### Description & Adapted Components

Claude Code provides architectural standards for hierarchical, budget-bounded agent memory. `buddhi-cli` adapts these memory patterns into the Google Antigravity harness:
- **Index Budget Enforcement**: Capping the primary memory entrypoint (`MEMORY.md`) to 200 lines / 25 KB with compaction and demotion into topic indexes to prevent LLM context saturation.
- **Hierarchical Scopes**: Distinguishing project-shared (`.agents/memory/`), local gitignored (`.agents/memory.local/`), cross-project user preferences (`~/.buddhi/memory/`), and subagent memory (`.agents/agent-memory/<agent>/`).
- **Path-Scoped Activation & Import Expansion**: Using glob patterns (`paths: [...]`) to match memories against active files and expanding inline `@path` references up to 5 hops with cycle detection and directory sandboxing.
- **Agent Memory Frontmatter**: Equipping specialist subagents with persistent domain memory.

We express our gratitude to Anthropic and the Claude Code team for publishing their memory architecture standards.

---

## Google Open Knowledge Format (OKF)

- **Repository**: [https://github.com/GoogleCloudPlatform/open-knowledge-format](https://github.com/GoogleCloudPlatform/open-knowledge-format)
- **Author**: Google Cloud Platform
- **License**: Apache License 2.0

### Description & Adapted Components

The Open Knowledge Format (OKF v0.2) specifies portable, machine-readable knowledge bundles of Markdown files with structured YAML frontmatter. `buddhi-cli` adapts OKF v0.2 for project memory concepts:
- **Concept Frontmatter Schema**: Standardized YAML frontmatter (`id`, `kind`, `title`, `summary`, `status`, `confidence`, `paths`, `tags`, `sources`, `relations`).
- **Source Code Provenance & Staleness**: Anchoring memories to source code line ranges (`resource#L10-L40`) and tracking staleness via SHA-256 `content_hash` comparison.
- **Bundle Topology**: Directory structures with topic `index.md` files, a chronological mutation `log.md`, and an entrypoint `MEMORY.md` declaring `okf_version: "0.2"`.

We express our gratitude to the Google Cloud Platform team and contributors for the Open Knowledge Format specification.

---

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

## A11Y.md

- **Repository**: [https://github.com/fecarrico/A11Y.md](https://github.com/fecarrico/A11Y.md)
- **Author**: Felipe A. Carriço (`fecarrico`)
- **License**: MIT License

### Description & Adapted Components

`A11Y.md` is an accessibility framework and instruction standard for AI coding assistants, treating accessibility as an invariant rather than a post-hoc audit. `buddhi-cli` adapts the `A11Y.md` system into the Google Antigravity harness and Spec-Driven Development (SDD) workflow:
- **`a11y` Skill & Pattern Guides**: Specialized Antigravity skill (`.agents/skills/a11y/`) packaging 31 modular pattern guides (`guide-*.md`) covering interactive elements, forms, dialogs, media, navigation, and touch targets with lazy-loading index to maintain token economy.
- **Always-on Rule**: `.agents/rules/a11y.md` enforcing WCAG 2.2 AA / EN 301 549 standards, semantic HTML over ARIA recreation, and pattern memory lookups.
- **Governance Artifacts & Templates**: Scaffolding templates for release evidence (`REPORT.md`), unresolvable technical exceptions (`EXCEPTIONS.md`), cross-turn pattern memory (`A11Y-DECISIONS.md`), and public accessibility statements (`ACCESSIBILITY.md`).
- **Deterministic Static Gate**: Pure Python 3.10+ stdlib modular package (`src/buddhi/scripts/verify_a11y/`) and CLI command (`buddhi scripts verify-a11y`) auditing 11 source anti-patterns, release evidence completeness, contrast evidence math, and verification independence.
- **Enhanced Contrast Engine**: Extended `buddhi scripts contrast` supporting multi-pair evaluation (`--bg`, `--fg`), strictness profiles (`standard`, `shield`, `launchpad`), alpha compositing over page background, and CSS stylesheet triage (`--css`).
- **FastMCP Tools**: Registered `verify_a11y` and enhanced `check_contrast` tools on the Buddhi MCP server for agent invocation.
- **SDD Memory Promotion**: Automatic extraction of `A11Y-DECISIONS.md` pattern choices into durable OKF concept nodes (`mem-decision-a11y-*`) during `/close-spec` and `buddhi memory sdd-promote`.

We express our gratitude to Felipe A. Carriço and contributors for authoring and sharing the `A11Y.md` specification and tools.

---

### Upstream MIT License (`A11Y.md`)

```text
MIT License

Copyright (c) 2026 fecarrico

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

## Graphify

- **Repository**: [https://github.com/Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify)
- **Author**: Safi Shamsi
- **License**: Apache License 2.0 (with portions under MIT License)

### Description & Adapted Components

`Graphify` converts complex software repositories into queryable knowledge graphs with topological analysis, Leiden community clustering, and agent tools. `buddhi-cli` adapts the following architectural concepts natively on its SQLite (`tree-graph.db`) + `igraph` + FastMCP stack:
- **Project-Wide Symbol Resolution & Confidence Tiers**: Categorizing edge provenance into discrete confidence tiers (`EXTRACTED`, `INFERRED`, `AMBIGUOUS`) with relationship contexts (`call`, `import`, `inherit`, `type_ref`).
- **Topological Analysis & Diagnostics**: Algorithmic ranking of architectural `god_nodes`, `surprising_connections`, diagnostic review questions, import cycle detection, and shortest relational paths with candidate symbol disambiguation.
- **Blast Radius Analysis**: Evaluating transitive callers, affected communities, and impacted hubs across working trees and git diff revisions.
- **Token-Efficient Retrieval**: Hub-blocked traversal (preventing high-degree utility hubs from exploding neighborhood bounds) and IDF-weighted multi-field anchor scoring.
- **Hook-Based Context Injection**: Sub-50ms non-blocking context injection for agent file-reads and session staleness checks.

We express our gratitude to Safi Shamsi and the Graphify contributors for sharing their knowledge-graph architecture.

---
