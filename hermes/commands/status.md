---
name: hermes-status
description: >
  Print a structured project health summary showing current stage, task
  status, pending persona reviews, document completeness, and deploy status.
  Run with /hermes status at any time.
---

# Hermes Status

Read the following and produce the status report:
1. `.cc-forge/state.json` — stage, stack, gates passed
2. `.taskmaster/tasks/tasks.json` — task counts and next task
3. Check existence of each required document

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES STATUS  ·  [project name]
  [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Stage       [N] [STAGE NAME]
  Sprint      [current sprint context if known]

  TASKS
  ───────────────────────────────────────────
  Done:        [N]
  In progress: [N]
  Remaining:   [N]
  Blocked:     [N]
  Next:        #[id] — [title]

  PERSONA GATES
  ───────────────────────────────────────────
  [✓ or ⚠ or —]  CTO review         [date or "due" or "—"]
  [✓ or ⚠ or —]  Security audit     [date or "due" or "—"]
  [✓ or ⚠ or —]  QA review          [date or "due" or "—"]
  [✓ or ⚠ or —]  SRE review         [date or "due" or "—"]
  [✓ or ⚠ or —]  Product Owner      [date or "due" or "—"]

  DOCUMENTS
  ───────────────────────────────────────────
  [✓/✗]  CLAUDE.md           [✓/✗]  RUNBOOK.md
  [✓/✗]  PRD.md              [✓/✗]  INCIDENT.md
  [✓/✗]  ARCHITECTURE.md     [✓/✗]  MONITORING.md
  [✓/✗]  DECISIONS.md        [✓/✗]  API.md
  [✓/✗]  CHANGELOG.md        [✓/✗]  ENV.md

  DEPLOY
  ───────────────────────────────────────────
  Status:    [Not deployed / Deployed to production]
  Domain:    [yourdomain.com or "—"]
  Last deploy: [date or "never"]

  FLAGS
  ───────────────────────────────────────────
  [Any urgent flags — missing docs, overdue gates, etc.]
  [or "No flags — all clear"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
