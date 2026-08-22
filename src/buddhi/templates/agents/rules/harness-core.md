---
name: harness-core
version: 1.0.0
priority: P0
trigger: always_on
---

# Harness core protocol

- Before reading raw source to understand how this codebase works, consult
  `.buddhi/docs/` (OKF docs, see the `okf-context` skill) and, for structural
  questions ("what calls this", "what depends on this"), `.buddhi/graphs/tree-graph.db`
  or `.buddhi/graphs/tree-graph.json` — buddhi's code graph. Only fall back to
  grepping raw source when neither answers the question.
- A request that spans more than one domain (e.g. "add a feature" touching UI,
  an API, and a schema change) should go through the `/plan` workflow before any
  code is written, so the relevant specialist agents can ground a plan in the
  actual codebase rather than generic advice.
- Destructive operations — force-push, `git reset --hard`, dropping or truncating
  a database table, deploying to a production environment — require explicit
  user confirmation first. Never chain one of these into a larger command without
  a stop for confirmation.
- Prefer delegating verbose or exploratory shell/build/test command execution to
  the `terminal-runner` subagent instead of running it inline: it reports back a
  condensed, no-bluff summary instead of raw output, keeping the main agent's
  context lean for reasoning.
