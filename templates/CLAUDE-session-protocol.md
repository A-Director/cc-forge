# cc-forge Session Protocol
#
# Add this block to the bottom of your project's CLAUDE.md.
# It makes the three manual commands automatic — Hermes runs
# them without being asked.
#
# ─────────────────────────────────────────────────────────────

## Session protocol (automatic)

### On session start — always, before anything else
Run the Hermes session start protocol automatically:
1. Read `.cc-forge/state.json` — current stage
2. Read `.taskmaster/tasks/tasks.json` — task status
3. Read `.cc-forge/backlog/master.md` — backlog %
4. Read `RISKS.md` — any overdue reviews
5. Print the HERMES STATUS summary in this format:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  [Project] · Stage [N] [NAME]
  [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Last:     [Last completed task — from claude-mem]
  Next:     #[N] — [task title]
  Backlog:  [N]%
  [⚠ One flag only — most urgent]

  Starting: [first action — not a question]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Do NOT ask "what would you like to work on?" — state the next
task and begin. The developer will redirect if needed.

### After every significant action — always
Close with the Hermes summary (see HERMES.md — Hermes voice section).
One next step. Stated, not asked.

### On session end — when /compact is run or session closes
Before compacting, print:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Session closing
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Done this session:
  ✓ [task or action completed]
  ✓ [task or action completed]

  To do next session:
  → [Next task #N — title]

  Docs to update:
  · [Any doc that needs updating based on today's work]

  [Running /compact now...]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Then run /compact automatically. Do not ask permission.
