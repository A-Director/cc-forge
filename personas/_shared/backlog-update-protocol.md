# Backlog update protocol (shared subroutine)

> Every gate-review persona references this file. When the protocol
> evolves, edit it here — not in every persona.

When a gate-review persona finishes its audit, it has produced findings.
Each finding is either a verified-clean check or a problem that needs work.
Both shapes feed back into the cc-forge backlog the same way: through this
protocol. Personas do not invent their own ad-hoc tracking.

The aim: every Taskmaster task carries a standards-grounded parent. Every
backlog item moves status as work flows. Nothing orphans.

---

## The mandatory 3-step update

Before ending a gate review, every gate-review persona MUST do these three
steps. Skipping any step is a protocol violation and Argus flags it.

### Step 1 — Identify the parent backlog item

For each finding in your report, locate the parent in
`.cc-forge/backlog/0X-<domain>.md`. The parent is the backlog item whose
**Outcome** the finding directly relates to.

```
Finding:  "Stack traces visible to users on /api/checkout 500s"
Parent:   .cc-forge/backlog/03-security.md → [SEC-UNI-006]
          (template SEC-006 — "Error messages do not expose stack traces")
```

If you cannot find a parent item:
1. Do NOT skip the step — that creates an orphan task.
2. Log `type=missing_coverage` to `.cc-forge/usage.log` with the finding
   summary and the domain. This indicates a cc-forge framework gap (a
   missing template item that should be added in a future template update).
3. Continue the review — log the gap, then seed the task with parent
   `null` and source `gate-review:<persona>` so it surfaces in Argus.

### Step 2 — Mark the parent backlog item `in-progress`

Edit `.cc-forge/backlog/0X-<domain>.md`. For the parent item, change:

```diff
- - Status: not-started
+ - Status: in-progress
- - Evidence: —
+ - Evidence: in-flight — Taskmaster #<task-id> seeded by <persona> on <ISO date>
```

Rules:
- If the item was already `in-progress`, append the new task ID to the
  evidence line (comma-separated). Don't overwrite prior in-flight work.
- If the item was already `done`, the finding contradicts the prior
  evidence — flag this as a `type=drift` log entry (the previously-passing
  check is no longer passing) and re-open the item to `in-progress`.
- Never move an item to `done` from a finding — only mark `done` for
  verified clean checks (and include file:line in Evidence).

### Step 3 — Seed the Taskmaster task with the Standard reference

For each non-clean finding, seed a Taskmaster task using
`hermes/commands/taskmaster-seed.md`. The task title MUST start with the
parent backlog ID; the task description MUST include the **Standard**
copied verbatim from the parent backlog item.

The seed helper enforces this. If you craft tasks manually without going
through the helper, you will create orphan tasks — the helper exists
precisely so personas don't have to remember every required field.

---

## Validate-and-retry loop (§3.8 write-path contract)

Persona-produced structured writes (backlog item edits, ADRs, intake
entries) are validated AT WRITE TIME against the §3.2 / §3.4 / §3.7
contract. On failure, the persona is re-prompted with the specific
violation and writes again. This is the §3.8 write-path mechanism —
the complement to retrospective parsing.

The mechanics (Session D, Phase D):

**1. Validate before declaring the write complete.** Use
`scripts/_hermes_writepath.py validate-backlog-item --feedback` (or
the equivalent helper for intake / ADR writes). The validator returns
either a clean result or a list of violations.

**2. On failure, the writer reads the feedback and revises.** The
feedback names each violated field and the contract it violated, in
order. Example feedback for a missing-Standard write:

```
VALIDATION FAILED (1 violations) — write must conform to §3.2 contract.
Violations:
  ↻ Standard: required field 'Standard' missing or empty (§3.2 — required
    for new writes; grandfathering is read-side only)

Action: revise the write to satisfy the contract above. The contract is
closed — do not invent values; if a required input genuinely doesn't
exist, mark the write as non-retryable and surface to the operator.
```

**3. Retry budget — 3 attempts (initial + 2 retries).** After the third
attempt:
- If the violations are RETRYABLE (format errors — typo, missing field
  the writer could include), the loop hits BUDGET_EXHAUSTED. The write
  is recorded as a `format_violation` event with `severity:
  hard_failed` and the persona surfaces to the operator. Three retries
  not fixing a format error usually means the persona's prompt has a
  structural problem; re-prompting won't fix it.
- If a violation is NON-RETRYABLE (the required input genuinely doesn't
  exist — e.g., the persona was asked to cite a Standard for a finding
  that has no standard reference, or referenced an item that doesn't
  exist), the loop halts immediately at attempt 1. There is no writer
  for a missing fact; re-prompting won't conjure one. The persona
  reports the missing input to the operator.

**4. Every attempt logs a `format_violation` event in usage.log.** The
event captures `attempt`, `retryable`, the specific violation, and
either `severity: strict` (retryable) or `severity: hard_failed`
(budget exhausted). The doctor's drift report shows these
stratified per the E-1 contract.

**5. Retrospective read-side validation is the backstop.** The
validate-and-retry loop catches malformed PERSONA writes at the source.
A human hand-edit that introduces a violation AFTER the write is caught
by the read-side parser the doctor runs (Layer 2 check). Both layers
are needed.

### Helper invocation pattern

```bash
# Inside a persona prompt or gate review, after composing the
# proposed write:
attempt=0
budget=3
while [ "$attempt" -lt "$budget" ]; do
  attempt=$((attempt + 1))
  feedback=$(echo "$proposed_json" \
    | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/_hermes_writepath.py" \
        validate-backlog-item --feedback)
  rc=$?
  if [ "$rc" -eq 0 ]; then
    break                      # validated; commit the write
  fi
  # Re-prompt yourself with $feedback; produce a revised $proposed_json
done
if [ "$rc" -ne 0 ]; then
  # Budget exhausted — surface the hard failure
  echo "✗ write-path budget exhausted after $budget attempts"
  exit 2
fi
```

In Python (when called from agent code rather than shell):

```python
from _hermes_writepath import run_validate_retry, validate_backlog_item

result = run_validate_retry(
    writer=produce_write,           # callable returning proposed dict
    validator=validate_backlog_item,
    project_root=project_root,
    write_target_file=".cc-forge/backlog/03-security.md",
    budget=3,
)
if result.success:
    commit_write(result)
else:
    surface_hard_failure(result.reason, result.final_violations)
```

---

## Examples — correctly-formed vs malformed

### ✅ Correctly-formed update (do this)

```
Finding from Security Auditor:
  [VULN-003] A05 Security Misconfiguration — api/checkout.ts:84
  Issue: Express error handler re-throws with full stack to client on 500.

Update steps:
  1. Parent: .cc-forge/backlog/03-security.md → [SEC-UNI-006]
  2. Backlog edit:
       SEC-UNI-006 Status: not-started → in-progress
       Evidence: in-flight — Taskmaster #47 seeded by security-auditor on 2026-05-22
  3. Taskmaster seed (via hermes/commands/taskmaster-seed.md):
       Title:       [SEC-UNI-006] Strip stack traces from production errors
       Parent:      .cc-forge/backlog/03-security.md → [SEC-UNI-006]
       Standard:    OWASP ASVS 4.0 — V7.4.1
       Outcome:     Internal system details not visible to potential attackers
       Phase:       2 (Beta)
       Acceptance:  Express error handler returns generic 500 in NODE_ENV=production;
                    full stack still emitted to Sentry. Test added.
       Source:      gate-review:security-auditor
```

### ❌ Malformed updates (never do this)

```
✗ Title: "Fix stack traces"
  — Missing parent backlog ID prefix. Orphan task.

✗ Description: "See gate review output."
  — No Standard, no Outcome, no Acceptance, no Source. Will not survive
    a context-window flush; loses standards grounding.

✗ Backlog edit skipped, only Taskmaster task created.
  — Backlog item remains not-started, but work is in flight. Drift.

✗ Finding logged, no parent identified, no missing_coverage entry.
  — Silent orphan. Worst case.
```

---

## Where personas record their updates

The gate-review output format already has spots for this. Every persona's
report must include a closing **Backlog Updates** section:

```
BACKLOG UPDATES
  ─────────────────────────────────────────
  Items moved to in-progress:
    • SEC-UNI-006 (Taskmaster #47)
    • SEC-UNI-011 (Taskmaster #48)

  Items marked done with evidence:
    • SEC-UNI-001 — verified clerkMiddleware on all /api/* routes (api/clerk.ts:12)

  Tasks seeded: 2 (via hermes/commands/taskmaster-seed.md)
  Orphan tasks: 0
  Missing coverage flagged: 0
```

When the consolidated gate review aggregates persona outputs, it sums
these counts and surfaces them in the Hermes closing banner.

---

## Logging the protocol

Every gate-review persona, at the end of its run, appends one log entry
per outcome category:

```bash
# For each task seeded
echo '{"ts":"...","type":"persona","data":{"persona":"<name>","backlog_items_ticked":["<ID>"],"tasks_seeded":["<task-id>"]}}' >> .cc-forge/usage.log

# For each orphan
echo '{"ts":"...","type":"orphan_task","data":{"persona":"<name>","task_id":"<id>","finding":"<short>"}}' >> .cc-forge/usage.log

# For each missing-coverage gap
echo '{"ts":"...","type":"missing_coverage","data":{"persona":"<name>","domain":"<file>","finding":"<short>"}}' >> .cc-forge/usage.log
```

See `hermes/log.md` for the full schema including the three protocol-related
types: `orphan_task`, `missing_coverage`, `standards_strip_detected`.

---

## Backwards compatibility

Existing projects whose backlog items lack a **Phase** field (Session A
predates them): the protocol still works — the Phase line in the
Taskmaster task description is simply omitted. The Standard line is
mandatory in all cases; if a backlog item is missing a Standard line,
that itself is a `type=standards_strip_detected` event and Argus flags it.

---

## Related

- `hermes/commands/taskmaster-seed.md` — the seed helper that enforces
  the task title/description format described in Step 3
- `hermes/log.md` — schema for `orphan_task`, `missing_coverage`,
  `standards_strip_detected`
- `hermes/commands/gate-review.md` — orchestrates persona invocations
  and aggregates the Backlog Updates section
- `hermes/backlog-init.md` — at init time, runs the Standards-preservation
  verification that guarantees this protocol has Standards to reference
