---
name: session-start
description: >
  Runs automatically at the start of every Claude Code session.
  Orients the developer, surfaces the next task, checks backlog %,
  and flags anything needing immediate attention. Under 150 words.
---

# Session Start Protocol

At the start of every Claude Code session, before doing anything else:

## 1. Read state (silently)
- `.cc-forge/state.json` — current stage and project state
- `.taskmaster/tasks/tasks.json` — task status
- `.cc-forge/backlog/master.md` — backlog completion %
- `CLAUDE.md` — standing orders
- `RISKS.md` — any overdue risk reviews

## 2. Orient (out loud, briefly)

Format:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [Project name]  ·  Stage [N] [NAME]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Last:     [Last completed task or "nothing completed yet"]
  Next:     #[N] — [Task title]
  Backlog:  [N]% ([N] domains launch-ready)
  [One flag only — most urgent]

  Starting: [first action]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 3. Flags to surface immediately

Surface these if true — one line each:
- `⚠ Gate review due` — feature merged but not reviewed by personas
- `⚠ [Document] missing` — required doc doesn't exist
- `⚠ Backlog [domain] at 0%` — domain not started, launch is approaching
- `⚠ RISKS.md: [N] overdue` — risk reviews past their review date
- `⚠ Argus due` — weekly compliance check not run this week
- `⚠ Context at X%` — if previous session compacted near limit
- `⚠ Deploy pending` — SRE/Security gate not passed yet

## 4. Model selection

Before the first task, select the right model:
- Planning a new feature or hard problem → suggest Opus
- Standard build task → Sonnet (default)
- Simple question or lookup → mention Haiku is available

Do not proceed until developer confirms direction.

## 4. Begin

State the next task and start it immediately. Do not ask "what would you
like to work on?" — that question is answered by Taskmaster.

If a decision is genuinely required before any work can proceed, ask it.
Otherwise: state the task and begin. The developer will redirect if needed.
## Hermes speaks last — always

After every significant action in the session, append the Hermes closing
summary (see HERMES.md — Hermes voice section). The format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  [what just happened]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ [Completed]
  Stage:    [N] [NAME]
  Backlog:  [N]%
  Next:     [Single clearest next action]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

One next step. No questions unless a real decision is needed.
No "want me to continue?" — just state what happens next.


## Logging

At session start, generate a session ID and write the session_start entry:
```bash
export SESSION_ID=$(date +%s | md5sum | head -c 8)
export STAGE=$(cat .cc-forge/state.json | python3 -c "import sys,json; print(json.load(sys.stdin)['current_stage'])" 2>/dev/null || echo 0)
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"session_start\",\"stage\":$STAGE,\"data\":{\"flags_at_start\":[$FLAGS]}}" >> .cc-forge/usage.log
```


---
name: session-end
description: >
  Runs at the end of every Claude Code session.
  Compacts, updates Taskmaster, updates backlog, flags doc updates needed,
  and sets up the next session cleanly.
---

# Session End Protocol

At the end of every session, before closing:

## 1. Task status
Update Taskmaster with any tasks completed or progressed this session.
If a task is partially done, add a note with current state.

## 2. Backlog updates
For each persona gate that ran this session, confirm their domain
backlog file was updated with evidence. If not, flag it:
"Security Auditor ran but 03-security.md not updated — do this before closing."

## 3. Document flags
Check what was worked on and flag any documents needing updates:
```
Documents to update before next session:
- ARCHITECTURE.md — [decision made today]
- API.md — [new endpoint added]
- ENV.md — [new variable added]
- DECISIONS.md — [decision that needs recording]
- RISKS.md — [any new accepted risks]
```

## 4. Compact recommendation
If context usage is above 40%, recommend `/compact` now.
If the session covered a complete phase, always compact regardless of %.

## 5. Gate check
If a feature was completed this session, flag the review needed:
"Feature [name] done. Queue: QA + Security review before merging."

## 6. Argus reminder
If Argus hasn't run this week: "Consider running /hermes-argus before
next session — weekly compliance check is due."

## 7. Next session primer
One sentence on what to pick up next:
"Next session: task #[N] — [title]."
## Logging

At session end, write the session_end entry:
```bash
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"session_end\",\"stage\":$STAGE,\"data\":{\"commands_run\":[$COMMANDS],\"tasks_completed\":[$TASKS],\"backlog_overall_pct_end\":$BACKLOG_PCT,\"compact_run\":$COMPACT_RUN,\"notes\":\"\"}}" >> .cc-forge/usage.log
```


---
name: phase-gates
description: >
  Defines when each persona activates, what triggers a gate review,
  how gate results update the backlog, and how overrides are recorded.
---

# Phase Gates

Phase gates are quality checkpoints ensuring the right expert reviews
the right thing at the right time. They are not bureaucracy — they are
the difference between shipping with confidence and shipping and hoping.

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
                                     → CFO (cost check)

Before any production deploy         → CTO
                                     → SRE Engineer
                                     → Security Auditor (full audit)
                                     → Legal/Compliance (first deploy)

Weekly (scheduled)                   → Argus (compliance monitor)
                                     → CFO (cost check)

Monthly                              → Market Analyst
                                     → Growth Agent (post-launch)

On demand                            → CEO (vision/strategy)
                                     → Research Agent (tech decisions)
                                     → Legal/Compliance (new features)
```

## How to invoke a gate

In Claude Code:
```
/hermes-gate review
```

Hermes reads current stage and recent activity, determines which
personas are due, and invokes them as subagents in sequence. Each runs
in its own clean context window — independent, no bias from other reviews.

## Gate outcomes

**PASS** — proceed to next stage or merge

**CONDITIONAL** — proceed, named issues must be resolved by deadline

**BLOCK** — do not proceed. Named issues must be resolved and gate re-run.

## After every gate — mandatory steps

1. Update `.cc-forge/state.json` with gate result
2. Each persona updates their domain backlog file:
   - Verified items → mark `done` with evidence (file:line or commit)
   - Failed items → mark `in-progress` or `not-started`
   - Not-applicable items → record in `DECISIONS.md`
3. Any BLOCK items → add entry to `RISKS.md` immediately
4. Any override/bypass → add entry to both `DECISIONS.md` and `RISKS.md`

## Override rule

**No deploy without passing SRE + Security gate. No exceptions.**

If the developer wants to override a gate:
- Acknowledge it, note the risk in one sentence
- Create DECISIONS.md entry: what was bypassed and why
- Create RISKS.md entry: the risk being accepted, likelihood, impact, review date
- Proceed — but the override is never silent

## Recording gate results

```json
{
  "gates_passed": [
    {
      "gate": "pre-deploy",
      "date": "2026-05-17",
      "personas": ["cto", "sre-engineer", "security-auditor"],
      "outcome": "CONDITIONAL",
      "conditions": ["Add rate limiting before public launch"],
      "backlog_updated": true,
      "risks_added": ["RISK-003"]
    }
  ]
}
```
