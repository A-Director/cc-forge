---
name: hermes-next
description: >
  Surface the single highest-priority unblocked task from Taskmaster
  with full context. Run with /hermes next at the start of any session.
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
  /hermes gate review  ← [if gate is due after this task]
  task-master done [id]  ← mark complete

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If all tasks are blocked, report:
"All remaining tasks have unresolved dependencies. Here's what's blocking progress:
[list the blocking tasks and what they depend on]"
