---
name: hermes-phase-gate
description: >
  Advance the project from one PDLC phase to the next (MVP → Beta →
  Pilot → Launch → Growth). Runs a full-panel persona review (forked),
  bumps state.json, writes a CHANGELOG entry, and requires a dedicated
  commit. Distinct from /hermes-gate-review (regular SDLC gates).
allowed-tools: Read, Write, Bash, Task
context: fork
---

# Hermes Phase Gate

`/hermes-phase-gate` invokes the phase-transition agent at
`stages/00-phase-gate/phase-gate-agent.md`.

## When to run

Run this **only** when advancing the PDLC phase. Most gate reviews
inside a phase use `/hermes gate review` (regular SDLC gates). A
phase gate is a once-per-phase event — typically 3–5 times in a
project's life:

- End of MVP → start of Beta
- End of Beta → start of Pilot
- End of Pilot → start of Launch
- End of Launch → start of Growth
- (Phase 5 Growth has no terminal exit — periodic re-gating is
  optional)

If you're not sure whether you need a phase gate, the answer is
probably no — run `/hermes gate review` for an SDLC gate instead.

## What this command does

1. Invokes `stages/00-phase-gate/phase-gate-agent.md` as a subagent.
2. Logs the event to `.cc-forge/usage.log` with
   `type: "phase_transition"`.
3. Surfaces the agent's output.

## Output format

The agent owns the full output sequence: exit-criteria check →
full-panel review → consolidated outcome → phase advance → dedicated
commit → Hermes closing banner. See
`stages/00-phase-gate/phase-gate-agent.md` for the banner shapes.

## Override

`/hermes-phase-gate --force` skips the exit-criteria block but
requires an ADR + RISKS entry. Use sparingly; Argus flags every
override.

## Related

- `/hermes gate review` — regular within-phase SDLC gate (use this
  ~10–100× more often)
- `PHASES.md` — phase definitions, exit gates, persona activation
- `stages/00-phase-gate/phase-gate-agent.md` — agent that runs the
  transition
- `session-lifecycle/phase-gates.md` — distinction between SDLC and
  PDLC gates
