---
name: verify
description: Prove a change actually works by running its real build/lint/test commands via the terminal-runner agent and reporting genuine pass/fail evidence, rather than claiming success from static reading.
version: 1.0.0
requires_agents: terminal-runner
artifact_outputs: verification-report
---

# /verify

$ARGUMENTS

Prove that a change works by actually running it, not by reasoning about what
should happen. Report real evidence for every command executed.

## Steps

1. Identify the scope: run `git diff` / `git status` (via the `terminal-runner`
   agent) to see which files changed, or use the explicit target named in
   `$ARGUMENTS` if the user gave one.
2. Determine this project's real verification commands: consult
   `.buddhi/docs/` and the code graph (see the `okf-context` skill pattern)
   plus the project's actual manifest/build files to find the build, lint,
   and test commands genuinely in use here. Never assume a generic command
   (e.g. `npm test`) without confirming it applies to this project — if the
   right command can't be found, ask the user instead of guessing.
3. Execute every determined command exclusively via the `terminal-runner`
   agent. Never run verification commands directly in the main agent's
   context.
4. For each command, report the command itself, its exit code, and a
   condensed summary of the real output (pass/fail counts, error lines) —
   never a paraphrase of expected behavior.
5. Flag anything that couldn't be verified this way (a UI flow, an
   interactive prompt, anything needing a browser) as requiring manual
   testing. Never omit it silently or claim it passed.
