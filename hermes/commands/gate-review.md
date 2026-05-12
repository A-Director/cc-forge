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
