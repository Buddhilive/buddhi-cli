---
name: okf-context
description: Use the codebase's generated OKF documentation under .buddhi/docs/ as the first source of truth for understanding code, before reading raw source files.
when_to_use: "Whenever you need to explain, navigate, or reason about how this codebase works — before grepping or reading raw source files for context."
allowed-tools: Read, Glob, Grep
version: 1.0.0
---

# Prefer OKF docs over re-reading source

This codebase has (or can have) machine-generated, dependency-aware documentation
under `.buddhi/docs/`, written as Open Knowledge Format (OKF) markdown — one concept
file per module/class/function, each with frontmatter describing what it is, where
it lives, and how fresh it is. Reading these first is cheaper and more reliable than
re-deriving understanding from raw source every time, and they already encode
caller/callee relationships you'd otherwise have to re-trace by hand.

## How to use it

1. Start at `.buddhi/docs/index.md` (bundle root) to see what's documented, then
   descend into the relevant subdirectory's own `index.md`.
2. Open the concept `.md` file for the symbol/module in question. Its frontmatter
   tells you:
   - `sources[0].resource` — exact file + line range the doc describes
   - `sources[0].content_hash` — matches the current code only if this doc is fresh
   - `status` — `deprecated` means treat with suspicion; `draft` means incomplete
   - `stale_after` — if present and in the past, treat the doc as unreliable
3. If the doc for the thing you need doesn't exist, is stale, or doesn't answer your
   question, fall back to reading the actual source (and, for structural questions —
   "what calls this", "what does this depend on" — consult
   `.buddhi/graphs/tree-graph.json` or `.buddhi/graphs/tree-graph.db`, buddhi's code
   graph, rather than grepping).
4. If you generate or substantially change code such that existing OKF docs go stale,
   say so, and suggest running the `/document-codebase` workflow (see
   `repoagent-doc-generation` skill) rather than silently leaving docs out of date.

Never treat an OKF doc as authoritative over the actual source code — it's a cache of
understanding, not the ground truth. When the two conflict, the source wins and the
doc needs regenerating.

