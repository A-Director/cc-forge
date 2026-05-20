---
name: hermes-status
description: >
  Print a structured project health summary showing current stage, task
  status, backlog % across all 10 domains, pending persona reviews,
  open risks, document completeness, and deploy status.
  Runs automatically at session start via CLAUDE.md session protocol.
  Also available on demand with /hermes-status.
---

# Hermes Status

Read the following and produce the status report:
1. `.cc-forge/state.json` — stage, stack, gates passed
2. `.taskmaster/tasks/tasks.json` — task counts and next task
3. `.cc-forge/backlog/master.md` — backlog % per domain
4. `RISKS.md` — open and overdue risks
5. Check existence of each required document

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
  Overall:     [N]%  ([done]/[total] applicable items)

  01 Product      [N]%    02 Development  [N]%
  03 Security     [N]%    04 Reliability  [N]%
  05 Design       [N]%    06 Integrations [N]%
  07 Compliance   [N]%    08 Launch       [N]%
  09 Growth       [N]%    10 Operations   [N]%

  Launch ready: [Yes — domains 01–08 all 100% / No — [N] incomplete]

  PERSONA GATES
  ───────────────────────────────────────────
  [✓/⚠/—]  CTO review         [date or "due" or "—"]
  [✓/⚠/—]  Security audit     [date or "due" or "—"]
  [✓/⚠/—]  QA review          [date or "due" or "—"]
  [✓/⚠/—]  SRE review         [date or "due" or "—"]
  [✓/⚠/—]  Product Owner      [date or "due" or "—"]
  [✓/⚠/—]  Argus              [date or "due — weekly check"]

  DOCUMENTS
  ───────────────────────────────────────────
  [✓/✗]  CLAUDE.md           [✓/✗]  RUNBOOK.md
  [✓/✗]  PRD.md              [✓/✗]  INCIDENT.md
  [✓/✗]  ARCHITECTURE.md     [✓/✗]  MONITORING.md
  [✓/✗]  DECISIONS.md        [✓/✗]  ENV.md
  [✓/✗]  RISKS.md            [✓/✗]  API.md

  RISKS
  ───────────────────────────────────────────
  Open:     [N]  Overdue:  [N]
  [Most urgent open risk if any — one line]

  DEPLOY
  ───────────────────────────────────────────
  Status:    [Not deployed / Deployed to production]
  Domain:    [yourdomain.com or "—"]
  Last deploy: [date or "never"]

  FLAGS  (most urgent first — max 3)
  ───────────────────────────────────────────
  [⚠ flag] or "No flags — all clear"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Priority closing

After the status report, close with one clear priority:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Priority
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Next:     [The single most important thing right now]
  [One sentence of context if needed]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

State it and begin. Do not ask "what would you like to do?"

---

## Logging

After producing the status report, append a log entry:
```bash
echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"session_id\":\"$SESSION_ID\",\"type\":\"command\",\"stage\":$STAGE,\"data\":{\"command\":\"/hermes-status\",\"flags_count\":$FLAGS_COUNT,\"backlog_pct\":$BACKLOG_PCT}}" >> .cc-forge/usage.log
```
