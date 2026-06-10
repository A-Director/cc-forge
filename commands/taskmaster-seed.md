---
name: hermes-taskmaster-seed
description: >
  Helper invoked by gate-review personas (and other agents) when seeding
  Taskmaster tasks. Enforces a strict task title/description shape so
  every task carries its standards-grounded parent backlog item.
  Not user-invocable on the command line — internal helper.
model: claude-haiku-4-5
effort: low
allowed-tools: Read, Write, Bash
invocation: internal
---

# Hermes Taskmaster Seed

Helper for personas and agents that need to create a Taskmaster task as
part of a gate-review (or similar) flow. The helper exists for one
reason: to guarantee every task carries its parent backlog ID and
**Standard** reference. Without this, tasks orphan from the backlog and
the standards-grounded structure of cc-forge breaks.

If you are a persona reading this: invoke this helper for every task you
want to seed. Do not craft Taskmaster tasks directly.

---

## Inputs

The caller must provide:

| Field | Required | Source |
|---|---|---|
| `backlog_id` | yes (or explicit `null` + `missing_coverage` log entry) | parent backlog item ID (e.g. `SEC-UNI-006`) |
| `backlog_path` | yes | path to the backlog file (e.g. `.cc-forge/backlog/03-security.md`) |
| `action` | yes | short action verb phrase (e.g. "Strip stack traces from production errors") |
| `standard` | yes (copied verbatim) | the `- Standard:` line from the parent backlog item |
| `outcome` | yes (copied verbatim) | the `- Outcome:` line from the parent backlog item |
| `phase` | optional | the `- Phase:` value from the parent backlog item, if present (Session A onward) |
| `acceptance` | yes | what specifically makes this task done — written by the caller |
| `source` | yes | `gate-review:<persona-name>` or similar provenance |

---

## Enforced shape

### Task title

```
[<backlog_id>] <action>
```

Examples:
- `[SEC-UNI-006] Strip stack traces from production errors`
- `[REL-001] Write RUNBOOK.md incident-response section`
- `[DEV-TEST-003] Add e2e tests for sign-in protected-route flow`

Validation: the title MUST start with `[<backlog_id>]` followed by a
space, then the action. If `backlog_id` is `null` (missing coverage case),
the title prefix is `[ORPHAN]` and the helper additionally writes a
`type=orphan_task` log entry (see `hermes/log.md`).

### Task description

```
Parent:     <backlog_path> → [<backlog_id>]
Standard:   <standard>
Outcome:    <outcome>
Phase:      <phase>        # omitted if parent has no Phase field
Acceptance: <acceptance>
Source:     <source>
```

The Parent line is mandatory and must point at a real file path that
contains the referenced ID. The helper greps the file to confirm before
creating the task; if the ID isn't found at that path, the helper errors
and the persona must re-locate the parent.

---

## Error conditions (helper returns failure)

1. **Missing backlog_id** without an explicit `null` opt-out + matching
   `missing_coverage` log entry already written → error: "orphan task
   attempted without missing_coverage log entry; refusing to seed."
2. **Title doesn't start with `[<backlog_id>] `** → error: "task title
   must lead with parent backlog ID."
3. **Standard field empty or missing** → error: "Standard required;
   copy verbatim from parent backlog item. If parent has no Standard
   line, that's a `standards_strip_detected` event — log it and fix the
   template before continuing."
4. **Parent path does not contain the backlog_id** → error: "parent
   <backlog_id> not found in <backlog_path>."

When the helper errors, the persona's gate review remains valid — but
the offending task is not seeded. The persona must fix the inputs and
retry, or escalate as a framework gap.

---

## What the helper does (in order)

1. Validate all required inputs against the error conditions above.
2. Read `backlog_path`, grep for `[<backlog_id>]`, confirm presence.
3. Re-read the Standard, Outcome, and Phase from the file to ensure the
   caller's copies match the source of truth. Warn (don't error) if the
   caller's Standard differs from the file's — typically means the
   caller copied from stale context; use the file's version.
4. Create the Taskmaster task via the project's existing Taskmaster
   integration (see project-specific Taskmaster setup).
5. Append a log entry to `.cc-forge/usage.log`:
   ```json
   {"ts":"...","type":"persona","data":{"persona":"<caller>","tasks_seeded":["<task-id>"],"backlog_items_ticked":["<backlog_id>"]}}
   ```
6. Return the new task ID to the caller, who uses it to update the
   parent backlog item's Evidence line (per
   `personas/_shared/backlog-update-protocol.md` Step 2).

---

## Backwards compatibility

For backlog items that pre-date Session A (no **Phase** field): the
`phase` input is optional and the Phase line is omitted from the task
description. Every other field is mandatory regardless of vintage.

For projects that haven't run the updated `/hermes-backlog-init` and
whose backlog files have missing **Standard** lines (gap #48 territory):
the helper errors on `Standard required` and surfaces the underlying
template damage. Fix the backlog file first (re-run
`/hermes-backlog-init` once gap #48 is fixed), then re-seed.

---

## Related

- `personas/_shared/backlog-update-protocol.md` — the 3-step protocol
  every gate-review persona follows; this helper enforces Step 3.
- `hermes/log.md` — `orphan_task`, `missing_coverage`,
  `standards_strip_detected` schemas referenced above.
- `hermes/backlog-init.md` — guarantees Standard lines are preserved so
  this helper has something to copy.
