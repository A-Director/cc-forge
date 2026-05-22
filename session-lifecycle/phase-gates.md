# Phase Gates — SDLC vs PDLC

> Two kinds of gate review exist in cc-forge. Don't confuse them.

cc-forge runs gate reviews at two distinct rhythms. The trigger map
in `lifecycle.md` covers the within-phase rhythm. This file covers
the distinction between the two kinds.

---

## SDLC gates (within phase)

**Frequency:** Many per phase — fired by trigger conditions like
"feature merged to main", "auth/payment code touched", "deploy
about to run", etc.

**Personas:** Subset — usually 1–3 personas relevant to what was
just built (e.g. QA after a feature merge, Security after auth
work, UX before a UI build with a design doc).

**Command:** `/hermes gate review`

**Output:** A single persona (or small panel) returns PASS /
CONDITIONAL / BLOCK on the work that just happened.

**State.json effect:** Adds an entry to `gates_passed` with the
personas, outcome, and conditions. Does not change `current_phase`.

**Trigger map:** See `lifecycle.md` "Gate trigger map" section.

---

## PDLC gates (between phases)

**Frequency:** Rare — typically 3–5 times in the entire life of a
project (MVP→Beta, Beta→Pilot, Pilot→Launch, Launch→Growth).

**Personas:** Full panel for the *target* phase — every persona
active in the new phase weighs in.

**Command:** `/hermes-phase-gate`

**Output:** Exit-criteria validation, full-panel review,
consolidated outcome, dedicated commit advancing `current_phase`.

**State.json effect:** Bumps `current_phase`. Adds an entry to
`gates_passed` with `gate: "phase_transition"` and `from_phase` /
`to_phase` fields.

**Side effects:** Writes a CHANGELOG entry. Updates
`backlog/master.md` current-phase header and recalculates domain
bars against the new phase. Conditional findings become
`in-progress` backlog items.

**Specification:** See `stages/00-phase-gate/phase-gate-agent.md`
for the full agent flow and `PHASES.md` for phase definitions.

---

## Updated gate trigger map (consolidated)

The full trigger map from `lifecycle.md`, with PDLC transitions
added:

```
TRIGGER                              GATE KIND   PERSONAS INVOKED
─────────────────────────────────────────────────────────────────
Feature merged to main               SDLC        → QA Engineer
                                                 → Security (if
                                                   auth/data/pay
                                                   touched)

UI/frontend feature built,           SDLC        → UX Expert
before merging to main                             (or before build
                                                   if design doc
                                                   exists in docs/)

Design document approved             SDLC        → CTO
                                                 → UX Expert

Sprint complete                      SDLC        → Product Owner
                                                 → CFO

Before any production deploy         SDLC        → CTO
                                                 → SRE Engineer
                                                 → Security
                                                 → Legal (first
                                                   deploy)

Weekly (scheduled)                   SDLC        → Argus
                                                 → CFO

Monthly                              SDLC        → Market Analyst
                                                 → Growth Agent

On demand                            SDLC        → CEO
                                                 → Research Agent
                                                 → Legal/Compliance

PDLC phase transition                PDLC        → Full panel for
(/hermes-phase-gate)                               the target phase
                                                 (see PHASES.md)
```

---

## Which one fires when

Quick disambiguator:

- "I just merged a feature, anything to review?" → SDLC,
  `/hermes gate review`
- "About to deploy" → SDLC, `/hermes gate review` (or `/hermes-deploy`
  which runs the gate check inline)
- "Ready to invite real users to try it" → PDLC, `/hermes-phase-gate`
  (advancing MVP → Beta)
- "Ready to charge money" → PDLC, `/hermes-phase-gate` (advancing
  Beta → Pilot)
- "Going public" → PDLC, `/hermes-phase-gate` (advancing Pilot →
  Launch)
- Anything else within the current phase → SDLC

If in doubt, default to SDLC. Phase gates are heavy and infrequent.

---

## Related

- `lifecycle.md` — within-phase session-start/end protocol, gate
  trigger map, override rule, stage advancement rule
- `PHASES.md` — phase definitions, exit gates, domain bars
- `stages/00-phase-gate/phase-gate-agent.md` — full phase
  transition flow
- `hermes/commands/phase-gate.md` — `/hermes-phase-gate` command
  spec
