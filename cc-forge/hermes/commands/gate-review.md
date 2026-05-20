---
name: hermes-gate-review
description: >
  Trigger a phase gate review. Reads the current stage, determines which
  personas are due, invokes them as subagents, and produces a consolidated
  gate report. Run with /hermes gate review.
---

# Hermes Gate Review

Read `.cc-forge/state.json` to determine the current stage and recent
gate history. Based on the trigger, invoke the appropriate personas.

## Determine which personas to invoke

```
Stage 02 SPEC complete     → Product Owner
Stage 04 DESIGN complete   → CTO + UX Expert
Feature merged             → QA Engineer
                             + Security Auditor (if auth/payment/data touched)
Stage 08 REVIEW            → All: CTO + QA + Security + UX + Product Owner
Before deploy (stage 09)   → CTO + SRE + Security Auditor + Legal (first deploy)
```

If invoked without context, ask:
"What triggered this review? (feature merge / stage complete / pre-deploy)"

## Invoke each persona as a subagent

Each persona must run in its own clean context window with:
1. Relevant source files
2. The persona definition from `personas/[name].md`
3. No knowledge of other personas' findings (to avoid bias)

## Consolidate and report

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GATE REVIEW  ·  [trigger]  ·  [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  OVERALL GATE: [PASS / CONDITIONAL / BLOCK]

  [CTO]        [PASS/CONDITIONAL/BLOCK]  [one-line summary]
  [Security]   [PASS/CONDITIONAL/BLOCK]  [one-line summary]
  [QA]         [PASS/CONDITIONAL/BLOCK]  [one-line summary]
  [SRE]        [PASS/CONDITIONAL/BLOCK]  [one-line summary]
  [Product]    [PASS/CONDITIONAL/BLOCK]  [one-line summary]

  BLOCKING ISSUES  (must resolve before proceeding)
  ─────────────────────────────────────────────────
  1. [Issue from persona] — [file/location] — [fix]

  CONDITIONS  (resolve by [date])
  ─────────────────────────────────────────────────
  1. [Condition] — [deadline]

  PROCEED:  [Yes — gate passed / No — fix blocking issues first]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Update `.cc-forge/state.json` with the gate result.

If gate is BLOCK, do not update state. Report what must be fixed.

---

## After every gate review

1. Update `.cc-forge/state.json` with gate result
2. Each persona updates their domain backlog file — marking items done with evidence
3. Any BLOCK items → add to `RISKS.md` immediately with review date
4. Any override decisions → add to `DECISIONS.md`
5. Run `/hermes-status` to see updated backlog % and flags

## Logging

After every gate review, append entries for each persona invoked:
```bash
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"gate\",\"stage\":$STAGE,\"data\":{\"trigger\":\"$TRIGGER\",\"personas\":[$PERSONAS],\"outcomes\":{$OUTCOMES},\"blockers\":$BLOCKERS,\"conditions\":$CONDITIONS,\"backlog_items_updated\":$ITEMS_UPDATED}}" >> .cc-forge/usage.log
```

---

## Context to pass to each persona subagent

Each persona runs in a clean context window. To avoid the "false alarm"
problem (persona flags something as missing that actually exists), pass
the full Hermes minimum document set to every persona subagent:

**Always include:**
- `CLAUDE.md` — project constraints and stack
- `PRD.md` — product requirements
- `ARCHITECTURE.md` — system design
- `DECISIONS.md` — decisions already made
- `ENV.md` — environment variables
- `.cc-forge/state.json` — current stage and stack

**Include based on gate type:**
- Pre-deploy gates: also include `RUNBOOK.md`, `INCIDENT.md`, `MONITORING.md`
- Feature gates: also include the relevant source files being reviewed
- Backlog gates: also include the relevant `.cc-forge/backlog/[domain].md`

**Never assume a document doesn't exist** — read the file system first.
If a document is not found after checking, then flag it as missing.
