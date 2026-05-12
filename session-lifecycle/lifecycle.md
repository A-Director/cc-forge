---
name: session-start
description: >
  Runs automatically at the start of every Claude Code session.
  Orients the developer, surfaces the next task, and flags anything
  that needs immediate attention. Keeps it under 150 words.
---

# Session Start Protocol

At the start of every Claude Code session, before doing anything else:

## 1. Read state (silently)
- `.cc-forge/state.json` — current stage and project state
- `.taskmaster/tasks/tasks.json` — task status
- `CLAUDE.md` — standing orders

## 2. Orient (out loud, briefly)

Format:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Project name]  ·  Stage [N] [NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Last:  [Last completed task or "nothing completed yet"]
  Next:  #[N] — [Task title]
  [Any flags — see below]

  Ready? (or tell me what you want to work on)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 3. Flags to surface immediately

Surface these if true — one line each:
- `⚠ Gate review due` — feature merged but not reviewed by personas
- `⚠ [Document] missing` — required doc doesn't exist
- `⚠ Context at X%` — if previous session compacted near limit
- `⚠ Deploy pending` — SRE/Security gate not passed yet
- `⚠ CFO: infra cost up X%` — if last CFO report flagged an issue

## 4. Model selection

Before the first task, select the right model:
- Planning a new feature or hard problem → suggest Opus
- Standard build task → Sonnet (default)
- Simple lookup or question → mention Haiku is available

Do not proceed until developer confirms direction.

---
name: session-end
description: >
  Runs at the end of every Claude Code session.
  Compacts, updates Taskmaster, flags doc updates needed,
  and sets up the next session cleanly.
---

# Session End Protocol

At the end of every session, before closing:

## 1. Task status
Update Taskmaster with any tasks completed or progressed this session.
If a task is partially done, add a note to it with current state.

## 2. Document flags
Check what was worked on and flag any documents that need updating.
Do not update them now — note them for the developer:

```
Documents to update before next session:
- ARCHITECTURE.md — [we decided X today]
- API.md — [new endpoint /api/vehicles added]
- ENV.md — [new STRIPE_PRICE_ID variable added]
```

## 3. Compact recommendation
If context usage is above 40%, recommend `/compact` now:
"We're at ~X% context. Recommend running `/compact` before we close —
it'll make the next session faster."

If context is below 40%, still recommend it if the session covered
a complete phase or distinct piece of work.

## 4. Gate check
If a feature was completed this session, flag the review needed:
"Feature [name] is done. Queue for QA + Security review before merging."

## 5. Next session primer
One sentence on what to pick up next:
"Next session: pick up task #[N] — [title]. It depends on [X] which
is now done."

---
name: phase-gates
description: >
  Defines when each persona activates, what triggers a gate review,
  and how gate results are recorded in project state.
---

# Phase Gates

Phase gates are the quality checkpoints that ensure the right expert
reviews the right thing at the right time. They are not bureaucracy —
they are the difference between shipping with confidence and shipping
and hoping.

## Gate trigger map

```
TRIGGER                              PERSONAS INVOKED
──────────────────────────────────────────────────────────────────
Feature merged to main               → QA Engineer (always)
                                     → Security Auditor (if auth/
                                       data/payment code touched)

Design document approved             → CTO (architecture)
                                     → UX Expert (user flows)

Sprint complete                      → Product Owner (PRD alignment)
                                     → CFO (cost check — Haiku)

Before any production deploy         → CTO (structural review)
                                     → SRE Engineer (ops readiness)
                                     → Security Auditor (full audit)
                                     → Legal/Compliance (first deploy)

Monthly (scheduled)                  → Market Analyst
                                     → Growth Agent (post-launch)
                                     → CFO (trending costs)

On demand                            → CEO (vision/strategy)
                                     → Research Agent (tech decisions)
                                     → Legal/Compliance (new features)
```

## How to invoke a gate

In Claude Code:
```
/hermes gate review
```

Hermes reads the current stage and recent activity, determines which
personas are due, and invokes them as subagents in sequence. Each runs
in its own clean context window (fresh — no bias from build session).

Results are collected and presented as a consolidated gate report.

## Gate outcomes

**PASS** — proceed to next stage or merge

**CONDITIONAL** — proceed, but named issues must be resolved by
a specified deadline (usually next sprint or before deploy)

**BLOCK** — do not proceed. Named issues must be resolved and the
gate re-run before moving forward.

## Recording gate results

After every gate, update `.cc-forge/state.json`:

```json
{
  "gates_passed": [
    {
      "gate": "pre-deploy",
      "date": "2026-05-12",
      "personas": ["cto", "sre-engineer", "security-auditor"],
      "outcome": "CONDITIONAL",
      "conditions": ["Add rate limiting to auth endpoints before launch"]
    }
  ]
}
```

## The rule

**No deploy without a passing SRE + Security gate.**
No exceptions. Not even for "just a quick hotfix."
Hotfixes get expedited gates, not skipped gates.
