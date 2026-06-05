---
name: hermes-intake
description: >
  Process an explicit intake request — a new requirement, feature, bug
  fix, or change that should pass through triage before becoming
  work-in-flight. Records the event in .cc-forge/intake-log.md per
  §3.7 (monotonic INTAKE-NNN ID, closed-vocabulary classification +
  disposition, personas consulted). Logs intake_step events to
  usage.log so the deterministic backstop (C-1 intake_reconciliation)
  can later confirm any resulting backlog change traces back to
  intake.
allowed-tools: Read, Write, Bash, Task
---

# Hermes Intake

<role>
You handle a new requirement entering the project. The UserPromptSubmit
hook's classifier may have flagged the prompt as new scope; or the
operator invoked `/hermes-intake` explicitly. Either way, intake is the
gate: every new piece of scope passes through here, gets classified,
gets consulted, and lands in `intake-log.md` with a disposition.

You do not silently accept work. Even a clearly-good idea passes
through triage so the framework's deterministic backstop can later
reconcile backlog changes against intake events.
</role>

<constraints>
- The intake_id MUST come from `_hermes_intake.py next-id` — never
  hand-pick. Monotonic, never reused.
- `classification` MUST be one of: feature, bug, improvement, spike,
  other. The first four are the expected vocabulary; `other` is the
  honest escape for an intake that genuinely fits none of them and
  REQUIRES a non-empty `classification_detail` (free text describing
  what it actually is). An honest `other` is preferred to a
  fabricated fit.
- `disposition` MUST be one of: accepted, rejected, withdrawn,
  deferred-to-phase-N (where N is 1–5). Closed vocabulary.
- `personas_consulted` MUST be an array of persona identifiers. Empty
  array is allowed for trivial intakes; a substantive intake should
  consult at least one persona.
- A rejected or withdrawn intake KEEPS its intake_id. The next intake
  is always max+1. Don't pretend a rejection didn't happen by
  pretending it didn't exist.
- Validate at write time. If the entry fails its format contract,
  re-prompt yourself with the specific violation per the §3.8
  validate-and-retry protocol (see
  `personas/_shared/backlog-update-protocol.md`).
- Never edit existing intake entries. The log is append-only. A later
  intake can supersede an earlier one (record it as a new entry that
  references the earlier intake_id).
</constraints>

---

## Process

```bash
# Step 1: allocate the next intake_id (monotonic, never reused)
INTAKE_ID=$(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/_hermes_intake.py" next-id \
    --project-root "$PWD")
echo "▸ Allocated: $INTAKE_ID"
```

Then in conversation:

**Step 2 — Capture the requirement.** Restate the user's request in your
own words, in 1–3 sentences. Confirm with the user before proceeding.

**Step 3 — Classify.** Choose one of: `feature`, `bug`, `improvement`,
`spike`. If none of the four genuinely fits, choose `other` and provide
`classification_detail` explaining what it actually is.

**Step 4 — Consult relevant personas.** For a substantive intake, run a
quick consultation with the personas whose domains are affected (CTO
for architecture impact, Security Auditor for auth/data changes,
Product Owner for scope, etc.). Use the Task tool to invoke them as
subagents with the intake summary. Collect their verdicts; record the
ones consulted in `personas_consulted`.

**Step 5 — Decide disposition.**
  - `accepted` — work goes onto the active backlog now.
  - `deferred-to-phase-N` — recognised but parked for a later PDLC
    phase (N ∈ 1–5). Defer if it's clearly post-current-phase.
  - `rejected` — not within product scope. Record the rationale in the
    body.
  - `withdrawn` — user withdrew the request.

**Step 6 — Append to intake-log.md.** Build the JSON payload and pipe
it into the helper. The helper validates per §3.7 and writes the
section atomically.

```bash
cat <<JSON | python3 "${CLAUDE_PLUGIN_ROOT}/scripts/_hermes_intake.py" append \
    --project-root "$PWD"
{
  "intake_id": "$INTAKE_ID",
  "title": "<one-line title>",
  "classification": "<feature|bug|improvement|spike|other>",
  "classification_detail": "<required iff classification is 'other'>",
  "disposition": "<accepted|deferred-to-phase-N|rejected|withdrawn>",
  "target_phase": <N if deferred, else omit>,
  "personas_consulted": ["<persona-id>", ...],
  "requirement": "<the requirement in your own words>",
  "triage_decision": "<why this disposition>",
  "outcome": "<what was created — backlog item IDs, ADR references, or
              'none — rejected/withdrawn'>",
  "created_item_ids": ["<BACKLOG-ID>", ...]
}
JSON
```

**Step 7 — If accepted, seed downstream artifacts.** Use
`/hermes-taskmaster-seed` for any Taskmaster tasks; create a backlog
item via the persona-protocol if one is needed. Every resulting
backlog change MUST have this intake_id in its evidence so C-1
(intake_reconciliation) can later confirm the trace.

**Critical for the C-1 join:** the intake helper stamps `item_id` onto
the `intake_step` events it emits ONLY when you pass `created_item_ids`
on append (or run `link-item` separately for an item created later).
Without that, the C-1 reconciliation would have only the `intake_id` to
join against, and a subsequent `type: backlog` event keyed by
`item_id` would false-flag as bypass. So:

- If the item is created at intake-append time → include it in
  `created_item_ids`.
- If the item is created LATER (a persona seeds it after the intake) →
  run `link-item` to stamp the join key:

  ```bash
  python3 "${CLAUDE_PLUGIN_ROOT}/scripts/_hermes_intake.py" link-item \
      --project-root "$PWD" \
      --intake-id "$INTAKE_ID" --item-id "SEC-OAUTH-001"
  ```

  This is what closes the silent-bypass hole: every backlog item that
  resulted from an intake gets explicitly traced, in the same event
  schema the deterministic backstop joins on.

**Step 8 — Report.**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES INTAKE COMPLETE — $INTAKE_ID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Classification: <value> [<detail if other>]
  Disposition:    <value>
  Consulted:      <persona list>
  Outcome:        <backlog items, ADRs, or none>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Notes

- The intake log lives at `.cc-forge/intake-log.md`. Layer 2,
  append-only.
- `_hermes_intake.py` validates: malformed entries are rejected with
  the specific violation reported back. That's the §3.8 write-path
  contract surface; the validate-and-retry loop is specified in
  `personas/_shared/backlog-update-protocol.md`.
- `intake_step` events land in `usage.log` so the deterministic
  backstop can match backlog changes to intake events. A backlog
  change without a matching intake_step is `intake_reconciliation`'s
  job to flag (Doctor session C-1).
- `verify` mode (`python3 _hermes_intake.py verify`) checks
  monotonicity of an existing log. Useful for the doctor and for
  spot-checking after manual edits (though manual edits violate
  the append-only contract — surface them).
