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
3. `.cc-forge/backlog/master.md` — backlog completion %
4. Check existence of each required document

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

  BACKLOG
  ───────────────────────────────────────────
  Overall:     [N]% complete ([done]/[total] applicable items)
  01 Product   [N]%   02 Development  [N]%
  03 Security  [N]%   04 Reliability  [N]%
  05 Design    [N]%   06 Integrations [N]%
  07 Compliance[N]%   08 Launch       [N]%
  Launch ready: [Yes — all 01-08 at 100% / No — [N] domains incomplete]

  PERSONA GATES
  ───────────────────────────────────────────
  [✓ or ⚠ or —]  CTO review         [date or "due" or "—"]
  [✓ or ⚠ or —]  Security audit     [date or "due" or "—"]
  [✓ or ⚠ or —]  QA review          [date or "due" or "—"]
  [✓ or ⚠ or —]  SRE review         [date or "due" or "—"]
  [✓ or ⚠ or —]  Product Owner      [date or "due" or "—"]
  [✓ or ⚠ or —]  Argus              [date or "due" or "—"]

  DOCUMENTS
  ───────────────────────────────────────────
  [✓/✗]  CLAUDE.md           [✓/✗]  RUNBOOK.md
  [✓/✗]  PRD.md              [✓/✗]  INCIDENT.md
  [✓/✗]  ARCHITECTURE.md     [✓/✗]  MONITORING.md
  [✓/✗]  DECISIONS.md        [✓/✗]  RISKS.md
  [✓/✗]  CHANGELOG.md        [✓/✗]  ENV.md

  RISKS
  ───────────────────────────────────────────
  Open risks:   [N]  ([N] overdue for review)
  [Most critical open risk if any]

  DEPLOY
  ───────────────────────────────────────────
  Status:    [Not deployed / Deployed to production]
  Domain:    [yourdomain.com or "—"]
  Last deploy: [date or "never"]

  FLAGS
  ───────────────────────────────────────────
  [Any urgent flags — missing docs, overdue gates, overdue risks]
  [or "No flags — all clear"]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Logging

After producing the status report, append a log entry:
```bash
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"command\",\"stage\":$STAGE,\"data\":{\"command\":\"/hermes-status\",\"flags_count\":$FLAGS_COUNT,\"backlog_pct\":$BACKLOG_PCT}}" >> .cc-forge/usage.log
```

---

## Hermes closes

After the status report, close with one clear priority:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Priority
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Next:     [The single most important thing right now]
  [One sentence of context if needed]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
