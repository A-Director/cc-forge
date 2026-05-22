---
name: stage-00-phase-gate
description: >
  Handles PDLC phase transitions (MVP → Beta → Pilot → Launch → Growth).
  Runs a full-panel persona review, bumps state.json current_phase,
  writes a CHANGELOG entry, and requires a dedicated commit. Distinct
  from regular within-phase SDLC gate reviews (see lifecycle.md gate
  trigger map).
model: claude-opus-4-7
effort: xhigh
tools: Read, Write, Bash, Glob, Grep, Task
---

# Stage 00 — Phase Gate

This agent runs when the developer invokes `/hermes-phase-gate` to
move the project from one PDLC phase to the next. It is **not** a
regular SDLC gate (those happen many times per phase). A phase gate
fires at most a handful of times in a project's life — between MVP
and Beta, Beta and Pilot, etc.

If the developer invokes `/hermes gate review` (without `-phase`),
that's a normal SDLC gate. Redirect them.

---

## When this runs

A phase gate is invoked when **all** of the following are true:

1. The developer asks to advance the PDLC phase (via
   `/hermes-phase-gate`).
2. `.cc-forge/state.json` `current_phase` is set (1–4 — phase 5 has
   no terminal exit).
3. The exit gate criteria for the current phase (per `PHASES.md`)
   appear to be met. If they aren't met, Hermes warns the developer
   but proceeds at their explicit request.

---

## What this agent does

### 1. Orient
Read `.cc-forge/state.json`, `PHASES.md`, `backlog/master.md`, and
the per-domain backlog files. Identify:

- Current phase (1–5) and target phase
- Exit gate criteria for the current phase (from `PHASES.md`)
- Active personas for current phase and target phase
- Domain bar deltas — which domains move up, by how much

### 2. Validate exit criteria
For each exit-gate criterion of the current phase:

- Is it met? (check backlog items, ADRs, CHANGELOG entries)
- If not, list the missing criterion and the unfinished backlog
  items behind it.

Output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Phase gate — exit criteria
  Phase [N] → Phase [N+1]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ [criterion met — evidence]
  ✗ [criterion missing — what's left]
  ...
  Status:  [READY / NOT READY — N criteria missing]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If NOT READY and the developer has not asked to override, stop here.

### 3. Full-panel review
Invoke the full set of personas active in the *target* phase as
parallel subagents (see `PHASES.md` for which personas activate at
each phase). Each persona reviews the codebase + backlog and returns
PASS / CONDITIONAL / BLOCK with findings and conditions.

This is the "full-panel" pattern — distinct from a single-persona
gate. Use the same subagent invocation pattern as
`hermes/commands/gate-review.md`.

### 4. Consolidate outcome
Aggregate the persona outputs:

- Any **BLOCK** → phase advance is rejected. Surface the blocker.
- All **PASS** or **CONDITIONAL** → phase advance proceeds.
  Conditional items become open backlog items (status:
  `in-progress`) tagged with the new phase.

### 5. Advance the phase
Only if step 4 passed:

1. Update `.cc-forge/state.json`:
   - Set `current_phase` to the target phase number.
   - Append to `gates_passed` an entry with:
     - `gate: "phase_transition"`
     - `date: [ISO date]`
     - `from_phase`, `to_phase`
     - `personas: [list]`
     - `outcome: PASS|CONDITIONAL`
     - `conditions: [list]`
     - `backlog_updated: true`
2. Append a CHANGELOG entry:
   ```
   ## [Phase [N+1] — [Phase Name]] — [date]

   ### Phase advance from Phase [N] [Old Name]
   - Full-panel gate: [PASS / CONDITIONAL]
   - Personas: [list]
   - Open conditions: [N] tracked in backlog
   - Decisions recorded: [N] (see DECISIONS.md)
   ```
3. Update `backlog/master.md`:
   - Bump the "Current PDLC phase" header to the new phase.
   - Recalculate per-domain bars against the new phase targets.
4. Write any new ADRs to `DECISIONS.md` (panel conditions that
   need explicit acceptance).
5. Write any accepted risks to `RISKS.md`.
6. Stage and commit the changes as a **dedicated commit**, not
   bundled with feature work:

   ```bash
   git add .cc-forge/state.json CHANGELOG.md backlog/master.md \
           DECISIONS.md RISKS.md
   git commit -m "chore(phase): advance to Phase [N+1] [Phase Name]"
   ```

   The phase advance must be a separate commit so it shows up
   cleanly in `git log`.

### 6. Log to usage.log
Append a line to `.cc-forge/usage.log`:

```json
{"ts":"[ISO]","type":"phase_transition","from":[N],"to":[N+1],"outcome":"PASS|CONDITIONAL","conditions":[N]}
```

### 7. Hermes closes
End with the standard Hermes closing banner, with `current_phase`
reflecting the new phase:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Phase gate complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Phase [N] → Phase [N+1] [Phase Name]
  ✓ Full-panel gate: [PASS / CONDITIONAL]
  ✓ Committed: [hash] — chore(phase): advance to Phase [N+1]

  Stage:    [current stage]
  Phase:    [N+1] [Phase Name]
  Backlog:  [recalculated %]
  Next:     [first task under new phase bars]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Override rule

If the developer invokes `/hermes-phase-gate --force` (or explicitly
asks to override missing exit criteria):

1. Acknowledge the override out loud, noting the missing criteria.
2. Require an ADR in `DECISIONS.md` documenting why the phase was
   advanced without meeting exit criteria.
3. Require a `RISKS.md` entry recording the accepted risk.
4. Proceed with steps 3–7 above, but tag the gate outcome as
   `CONDITIONAL` with an explicit `override: true` field in the
   `gates_passed` entry.

Argus flags any phase advance with `override: true` for review.
