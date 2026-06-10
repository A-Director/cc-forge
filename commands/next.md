---
name: hermes-next
description: >
  Surface the single highest-priority unblocked task from Taskmaster
  with full context. Read-only — never modifies project state.
allowed-tools: Read, Bash
model: claude-sonnet-4-6
invocation: user
---

# Hermes Next

Read `.taskmaster/tasks/tasks.json` and identify the highest-priority
unblocked task (not blocked by incomplete dependencies).

Output:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NEXT TASK  ·  #[id]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [Task title]

  What it is:
  [2-3 sentences describing the task clearly]

  Why it matters:
  [1 sentence on why this is the next logical step]

  Likely files involved:
  - [file or directory]
  - [file or directory]

  Complexity:     [Low / Medium / High]
  Estimated time: [rough estimate]
  Tags:           [feat / fix / auth / billing / etc.]

  When done, run:
  /hermes-gate-review  ← [if gate is due after this task]
  task-master done [id]  ← mark complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If all tasks are blocked, report:
"All remaining tasks have unresolved dependencies. Here's what's blocking progress:
[list the blocking tasks and what they depend on]"

---

## UI/frontend task detection

Before surfacing a task as the next action, check whether it involves
UI or frontend work. The task is a UI/frontend task if **any** of the
following match:

- Task `tags` include `frontend`, `ui`, or `react`
- Task `title` contains (case-insensitive) any of: `UI`, `React`,
  `frontend`, `component`, `KaTeX`, `panel`, `view`, `page`

When a UI/frontend task is detected, decide where the UX SME
gate runs based on whether a design document already exists:

**Look in `docs/`** for a design document, wireframe, mockup, or
spec for this feature (e.g. `docs/<feature>-design.md`,
`docs/wireframes/<feature>.*`, or any file clearly describing the
intended UI for this task).

**If a design doc exists** → do not start the task. Surface the UX
Expert gate review as the step that comes BEFORE the task:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  GATE DUE  ·  UX SME review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Next task:  #[id] — [title]
  This task involves UI/frontend work.
  Design doc found: [path]

  Required step before writing code:
  /hermes-gate-review  ← UX SME (design review)

  Once UX SME review is complete (PASS or CONDITIONAL),
  proceed with task #[id].
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**If no design doc exists** → surface the task as normal, but include
an explicit reminder that the UX SME gate must run after build,
before merging to main:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  NEXT TASK  ·  #[id]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  [Task title]
  [...standard task surface block...]

  Post-build gate (required before merge to main):
  /hermes-gate-review  ← UX SME
  No design doc found in docs/ — UX reviews the built UI instead.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If the developer has already run the UX SME gate for this task
(check `DECISIONS.md` or recent gate review output for a matching
entry), skip the gate and surface the task as normal.

---

## Hermes closes

After surfacing the next task, immediately begin working on it.
Do not ask for confirmation — the developer invoked /hermes-next
because they want to work on the next task. Start it.

If the task requires a real decision before starting (e.g. credentials
needed, external service required), state that specifically:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Starting Task #[N]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Task:     #[N] — [title]
  Blocked:  [Only if genuinely blocked — what's needed]
  Starting: [First concrete action]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## When Taskmaster is empty

If no pending tasks exist, do not return "all tasks complete" and
stop. Instead:

1. Read `.cc-forge/state.json` for current stage and phase.
2. Read `PRD.md` for the next phase scope.
3. Check if a gate review produced conditions that need tracking
   (read `.cc-forge/state.json` `gates_passed` for open conditions).
4. Generate Taskmaster tasks from:
   - Open gate conditions (highest priority)
   - Next PRD phase features (after conditions cleared)
5. Seed Taskmaster with the generated tasks.
6. Surface the first unblocked task.

Output format when seeding:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  [Phase N] complete — seeding [Phase N+1]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Created [N] tasks from [source]:
  → [N] blocking (must fix first)
  → [N] conditions (phase 1.5 work)
  → [N] features (next phase)

  First task: #[N] — [title]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

After seeding, continue into the standard next-task flow — surface
the first task using the normal output format and (if it's a UI task)
the UI/frontend detection logic above.
