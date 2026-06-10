---
name: hermes-log
description: >
  Automatic usage logger. Every /hermes-* command appends a structured
  entry to .cc-forge/usage.log. Called automatically by every Hermes
  command and at session end. Never needs to be invoked manually.
  Powers /hermes-report for review sessions.
model: claude-haiku-4-5
effort: low
allowed-tools: Read, Write, Bash
invocation: internal
---

# Hermes Log

<role>
You are the cc-forge usage logger. You write structured log entries to
`.cc-forge/usage.log`. You are called automatically — the developer never
invokes you directly. You are fast, minimal, and never block the main task.
</role>

<constraints>
- Never output anything to the developer — this runs silently in the background
- Keep entries compact — one JSON object per line (JSONL format)
- Never log sensitive data: no API keys, no secrets, no PII, no file contents
- Always append — never overwrite the log file
- If the log file doesn't exist, create it with an empty array header
- Fail silently — if logging fails, do not interrupt the session
</constraints>

---

## Log entry schema

Every entry is one line of JSON appended to `.cc-forge/usage.log`:

```json
{
  "ts": "2026-05-18T09:23:11Z",
  "session_id": "abc123",
  "type": "command|gate|session_start|session_end|persona|backlog|drift|orphan_task|missing_coverage|standards_strip_detected|phase_transition",
  "stage": 5,
  "data": {}
}
```

---

## Entry types and data shapes

### type: session_start
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "session_start",
  "stage": 5,
  "data": {
    "taskmaster_tasks_done": 12,
    "taskmaster_tasks_remaining": 8,
    "backlog_overall_pct": 47,
    "claude_md_tokens": 487,
    "flags_at_start": ["gate_review_due", "runbook_missing"]
  }
}
```

### type: command
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "command",
  "stage": 5,
  "data": {
    "command": "/hermes-status",
    "duration_seconds": 12,
    "output_summary": "stage 05, 3 flags surfaced"
  }
}
```

### type: gate
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "gate",
  "stage": 5,
  "data": {
    "trigger": "feature_merged",
    "personas": ["qa-engineer", "security-auditor"],
    "outcomes": {
      "qa-engineer": "PASS",
      "security-auditor": "CONDITIONAL"
    },
    "blockers": 0,
    "conditions": 1,
    "backlog_items_updated": 3
  }
}
```

### type: persona
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "persona",
  "stage": 5,
  "data": {
    "persona": "security-auditor",
    "outcome": "CONDITIONAL",
    "critical_findings": 0,
    "high_findings": 1,
    "medium_findings": 2,
    "backlog_items_ticked": ["SEC-003", "SEC-004"],
    "risks_added": [],
    "decisions_added": []
  }
}
```

### type: backlog
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "backlog",
  "stage": 5,
  "data": {
    "domain": "03-security",
    "pct_before": 30,
    "pct_after": 45,
    "items_completed": ["SEC-003", "SEC-004"],
    "items_not_applicable": [],
    "overrides": []
  }
}
```

### type: drift
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "drift",
  "stage": 5,
  "data": {
    "detected_by": "argus",
    "severity": "IMPORTANT",
    "category": "gate_skipped",
    "description": "QA gate not run after feature merge 3 days ago",
    "corrected": false
  }
}
```

### type: orphan_task
Emitted when a gate-review persona seeds a Taskmaster task with no parent
backlog item (after also emitting a `missing_coverage` entry). Indicates
the work is happening but the framework couldn't anchor it. Feeds the
Session C dashboard's drift counters.
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "orphan_task",
  "stage": 5,
  "data": {
    "persona": "security-auditor",
    "task_id": "47",
    "finding": "Stack traces visible on /api/checkout 500s",
    "reason": "no parent backlog item exists for this finding category"
  }
}
```

### type: missing_coverage
Emitted when a persona finding has no matching backlog item to update.
Indicates a cc-forge template gap — a future template update should add
an item covering this finding category. Distinct from `orphan_task`
(orphan tracks the resulting task; missing_coverage tracks the
framework gap that caused it).
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "missing_coverage",
  "stage": 5,
  "data": {
    "persona": "security-auditor",
    "domain": ".cc-forge/backlog/03-security.md",
    "finding": "WebSocket origin validation missing — no template item exists",
    "suggested_template_item": "SEC-WS-001 — WebSocket connections validate Origin header"
  }
}
```

### type: standards_strip_detected
Emitted by `/hermes-backlog-init` Phase 6 verification (or by
`taskmaster-seed` when it discovers a missing Standard on a parent
item). Indicates a customisation pass dropped the `- Standard:` line off
a backlog item. Init refuses to complete when this event fires.
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "standards_strip_detected",
  "stage": 5,
  "data": {
    "detected_by": "backlog-init|taskmaster-seed",
    "file": ".cc-forge/backlog/03-security.md",
    "item_id": "SEC-UNI-001",
    "expected_standard": "OWASP ASVS 4.0 — V4.1.1",
    "found": null
  }
}
```

### type: phase_transition
Emitted by `/hermes-phase-gate` (Session A) when the PDLC phase
advances. Recorded here so the log schema is the single source of
truth for entry types.
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "phase_transition",
  "stage": 5,
  "data": {
    "from": 1,
    "to": 2,
    "outcome": "PASS|CONDITIONAL",
    "conditions": 3,
    "override": false
  }
}
```

### type: session_end
```json
{
  "ts": "...",
  "session_id": "...",
  "type": "session_end",
  "stage": 5,
  "data": {
    "duration_minutes": 47,
    "commands_run": ["/hermes-status", "/hermes-next", "/hermes-gate-review"],
    "tasks_completed": [12, 13],
    "gates_run": 1,
    "personas_invoked": ["qa-engineer"],
    "backlog_overall_pct_start": 42,
    "backlog_overall_pct_end": 47,
    "compact_run": true,
    "model_used": "sonnet",
    "notes": ""
  }
}
```

---

## How to write a log entry

```bash
# Append one JSON line to the log
echo '{"ts":"2026-05-18T09:23:11Z","session_id":"abc123","type":"command",...}' \
  >> .cc-forge/usage.log
```

Generate the session_id at session start:
```bash
SESSION_ID=$(date +%s | md5sum | head -c 8)
```

Generate timestamp:
```bash
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

---

## When each Hermes command logs

| Command | Logs type | When |
|---|---|---|
| Session opens | `session_start` | Immediately |
| `/hermes-status` | `command` | After running |
| `/hermes-next` | `command` | After running |
| `/hermes-gate-review` | `gate` + `persona` per persona | After each persona |
| `/hermes-backlog-init` | `backlog` per domain + `standards_strip_detected` per offender | After init / verification failure |
| `/hermes-phase-gate` | `phase_transition` | After phase advances |
| Persona gate-review seeding orphan tasks | `orphan_task` + `missing_coverage` | After each persona |
| `/hermes-argus` | `drift` per finding | After running |
| `/hermes-deploy` | `command` | After running |
| Session ends (`/compact`) | `session_end` | On compact/close |
