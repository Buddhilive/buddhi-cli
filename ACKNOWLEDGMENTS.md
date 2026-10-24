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

The Open Knowledge Format (OKF) specifies portable, machine-readable knowledge bundles of Markdown files with structured YAML frontmatter. `buddhi-cli` adapts OKF across both codebase documentation (`.buddhi/docs/`) and project memory concepts (`.agents/memory/`):
- **Codebase Documentation & Live Site (`.buddhi/docs/` & `buddhi docs`)**: Structured OKF concept documents for modules, classes, functions/methods, Leiden communities, god nodes, and architecture reports, compiled into a browsable static documentation site via Pelican's custom `OKFMarkdownReader`.
- **Concept Frontmatter Schema**: Standardized YAML frontmatter (`id`, `kind`, `title`, `summary`, `status`, `confidence`, `paths`, `tags`, `sources`, `relations`).
- **Source Code Provenance & Staleness**: Anchoring memories to source code line ranges (`resource#L10-L40`) and tracking staleness via SHA-256 `content_hash` comparison.
- **Bundle Topology**: Directory structures with topic `index.md` files, a chronological mutation `log.md`, and an entrypoint `MEMORY.md` declaring `okf_version: "0.2"`.

We express our gratitude to the Google Cloud Platform team and contributors for the Open Knowledge Format specification.

---

## Pelican Static Site Generator

- **Documentation**: [https://docs.getpelican.com/en/latest/index.html](https://docs.getpelican.com/en/latest/index.html)
- **Repository**: [https://github.com/getpelican/pelican](https://github.com/getpelican/pelican)
- **Author**: Justin Mayer and the Pelican contributors
- **License**: AGPL-3.0 / MIT (used as an unmodified library dependency via Python API)

### Description & Integration

Pelican is a Python-based static site generator powered by Jinja2 templates and `python-markdown`. `buddhi-cli` integrates Pelican as the static site compilation and live-reloading server engine for `buddhi docs`:
- **Programmatic Site Generation (`pelican.Pelican` & `pelican.settings.read_settings`)**: Compiles `.buddhi/docs/` into `.buddhi/site/` without requiring external configuration files in the user's project root.
- **Custom `OKFMarkdownReader` (`pelican.readers.BaseReader`)**: Bridges Google Open Knowledge Format (OKF) YAML frontmatter (`sources`, `relations`, `generated`, `status`, `confidence`) into Pelican `Page` metadata and Jinja2 template context.
- **Live Server & Watcher (`buddhi docs` / `buddhi docs serve`)**: Uses Pelican's HTTP server and auto-reload pipeline to serve live codebase documentation locally.

We express our gratitude to Justin Mayer and the Pelican community for building and maintaining Pelican.

---

## RepoAgent

- **Paper**: [https://arxiv.org/abs/2402.16667](https://arxiv.org/abs/2402.16667)
- **Repository**: [https://github.com/OpenBMB/RepoAgent](https://github.com/OpenBMB/RepoAgent)
- **Authors**: OpenBMB / Tsinghua University

### Description & Adapted Components

`RepoAgent` introduces an LLM-powered, dependency-aware repository documentation methodology using AST call graphs. `buddhi-cli` adapts RepoAgent's bottom-up topological ordering (`topological_doc_order`) so callees and class members are documented before callers and containers, combined with SHA-256 snippet hashing (`content_hash`) for incremental staleness detection in `.buddhi/docs-plan.json`.

We express our gratitude to the RepoAgent authors for their research on dependency-aware codebase documentation.

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
- **Graph-Grounded Documentation Wiki & Architecture Reports**: Generating agent-crawlable and human-navigable community hubs (`communities/<slug>.md`), god-node articles (`god-nodes/<slug>.md`), and structural audit reports (`architecture-report.md`) with two-pass Windows `MAX_PATH`-safe slugging, case-insensitive deduplication, atomic writes (`write_text_atomic_if_changed`), and orphan sweeping (inspired by `graphify/wiki.py` and `graphify/report.py`).

We express our gratitude to Safi Shamsi and the Graphify contributors for sharing their knowledge-graph architecture.

---


---

## RTK (Rust Token Killer)

- **Repository**: [https://github.com/rtk-ai/rtk](https://github.com/rtk-ai/rtk)
- **Author**: rtk-ai
- **License**: Apache License 2.0 (for adapted components)

### Description & Adapted Components

`rtk` is a high-performance CLI proxy that minimizes LLM token consumption by 60–90% on common development commands. `buddhi-cli` adapts the command-filtering concepts, declarative filter rules, and lifecycle hook integration from `rtk`'s open-source Apache-2.0 components into pure Python (Python 3.10+):
- **Core Filtering Architecture (`src/buddhi/scripts/rtk/`)**: Declarative JSON filter engine supporting line stripping, keeping, replacement rules, duplicate collapse, ANSI stripping, empty fallback messaging, and non-destructive head/tail line limits.
- **Error Line Protection**: Guaranteed retention of compiler errors, failure summaries, exception traces, and panic lines during filtering and head/tail truncation.
- **Fail-Open Process Runner (`runner.py`)**: Subprocess execution preserving exact command exit codes, streaming output capture, and automated raw failure logging under `.buddhi/rtk/raw/` for auditing.
- **Broad Port of Builtin Filters (`builtin_filters/`)**: Over 60 declarative filters converted to zero-dependency JSON, covering Git, Pytest, Ruff, Mypy, UV, NPM, Cargo, Docker, Go, JVM, PHP, Ruby, and cloud/system CLI tools with embedded test suites.
- **Google Antigravity Integration**: Always-on rule (`.agents/rules/rtk.md`), skill (`.agents/skills/rtk/`), updated subagent conventions (`terminal-runner.md`), and fail-open lifecycle hook (`.agents/hooks/rtk_hook.py` registered in `hooks.json` under `PreToolUse`).
- **Observability & Custom Filter Trust (`tracking.py`, `trust.py`)**: Local `.buddhi/rtk/runs.jsonl` savings ledger with strict argument/secret redaction, `buddhi scripts rtk gain` metrics reporting, and SHA-256 hash pinning for project-local custom filters.
- **Harness Templates (`src/buddhi/templates/agents/`)**: Bundled rules, skills, and hooks synchronized so newly initialized Buddhi harnesses automatically benefit from token reduction.

### Exclusion Notice (BUSL-1.1 Components)

Upstream `rtk` employs a dual-license model where `engine/` (advanced compression engine) and `proxy/` (API proxy) are licensed under the Business Source License 1.1 (BUSL-1.1). **No components, algorithms, code, or data from `engine/` or `proxy/` are included, ported, or derived in `buddhi-cli`.** All filtering and execution logic in `buddhi-cli` was implemented independently using pure Python standard library primitives and the Apache-2.0 licensed filter specifications.

We express our sincere appreciation to `rtk-ai` for designing and sharing `rtk`.

---

### Upstream Apache 2.0 License (`rtk`)

```text
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work
      (an example is provided in the Appendix below).

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship. For the purposes
      of this License, Derivative Works shall not include works that remain
      separable from, or merely link (or bind by name) to the interfaces of,
      the Work and Derivative Works thereof.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner. For the purposes of this definition, "submitted"
      means any form of electronic, verbal, or written communication sent
      to the Licensor or its representatives, including but not limited to
      communication on electronic mailing lists, source code control systems,
      and issue tracking systems that are managed by, or on behalf of, the
      Licensor for the purpose of discussing and improving the Work, but
      excluding communication that is conspicuously marked or otherwise
      designated in writing by the copyright owner as "Not a Contribution."

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work,
      where such license applies only to those patent claims licensable
      by such Contributor that are necessarily infringed by their
      Contribution(s) alone or by combination of their Contribution(s)
      with the Work to which such Contribution(s) was submitted. If You
      institute patent litigation against any entity (including a
      cross-claim or counterclaim in a lawsuit) alleging that the Work
      or a Contribution incorporated within the Work constitutes direct
      or contributory patent infringement, then any patent licenses
      granted to You under this License for that Work shall terminate
      as of the date such litigation is filed.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work,
          excluding those notices that do not pertain to any part of
          the Derivative Works; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute must
          include a readable copy of the attribution notices contained
          within such NOTICE file, excluding those notices that do not
          pertain to any part of the Derivative Works, in at least one
          of the following places: within a NOTICE text file distributed
          as part of the Derivative Works; within the Source form or
          documentation, if provided along with the Derivative Works; or,
          within a display generated by the Derivative Works, if and
          wherever such third-party notices normally appear. The contents
          of the NOTICE file are for informational purposes only and
          do not modify the License. You may add Your own attribution
          notices within Derivative Works that You distribute, alongside
          or as an addendum to the NOTICE text from the Work, provided
          that such additional attribution notices cannot be construed
          as modifying the License.

      You may add Your own copyright statement to Your modifications and
      may provide additional or different license terms and conditions
      for use, reproduction, or distribution of Your modifications, or
      for any such Derivative Works as a whole, provided Your use,
      reproduction, and distribution of the Work otherwise complies with
      the conditions stated in this License.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.
      Notwithstanding the above, nothing herein shall supersede or modify
      the terms of any separate license agreement you may have executed
      with Licensor regarding such Contributions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor,
      except as required for reasonable and customary use in describing the
      origin of the Work and reproducing the content of the NOTICE file.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied, including, without limitation, any warranties or conditions
      of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
      PARTICULAR PURPOSE. You are solely responsible for determining the
      appropriateness of using or redistributing the Work and assume any
      risks associated with Your exercise of permissions under this License.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work (including but not limited to damages for loss of goodwill,
      work stoppage, computer failure or malfunction, or any and all
      other commercial damages or losses), even if such Contributor
      has been advised of the possibility of such damages.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License. However, in accepting such obligations, You may act only
      on Your own behalf and on Your sole responsibility, not on behalf
      of any other Contributor, and only if You agree to indemnify,
      defend, and hold each Contributor harmless for any liability
      incurred by, or claims asserted against, such Contributor by reason
      of your accepting any such warranty or additional liability.

   END OF TERMS AND CONDITIONS
```
