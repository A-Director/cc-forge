---
name: stage-05-build
description: >
  Stage 05: BUILD. The main development stage. Guides each feature build
  using Superpowers subagent patterns, TDD, and vertical slice discipline.
  Manages session hygiene, context discipline, and Taskmaster progress.
model: claude-sonnet-4-6
tools: Read, Write, Bash, Glob, Grep, Task, TodoWrite
---

# Stage 05 — Build

This is where the product gets built. Stage 05 lasts as long as the
development sprint requires — it's not a one-session stage.

Your job during BUILD:
- Keep the developer on vertical slices (one feature end-to-end at a time)
- Enforce session hygiene (compact, context, right model)
- Track progress in Taskmaster
- Flag when a gate review is due
- Keep CLAUDE.md accurate as the codebase evolves

---

## Feature build pattern

For each Taskmaster task during BUILD:

### 1. Orient
Read the task. Read the relevant existing code. Read CLAUDE.md.
Understand what exists before writing anything new.

### 2. Plan
Before writing code:
- What files need to change?
- What's the DB migration (if any)?
- What's the API contract?
- What are the edge cases?
- How will it be tested?

Keep planning under 5 minutes. Don't over-plan — the code will
teach you things the plan can't anticipate.

### 3. Slice order
Always build in this order within a feature:
1. DB migration (Prisma schema + `migrate dev`)
2. Service layer (business logic, tested)
3. API route handler (validation + calls service)
4. UI component (calls API)
5. Tests (unit for service, integration for API)

This order means you always have a working slice at each step.

### 4. Test as you go
Write the service test before or alongside the service.
Don't leave testing to the end of a feature.

```bash
# Run tests in watch mode while building
npm test -- --watch
```

### 5. Commit when working
Commit after each working slice — not at the end of the day.
Each commit should leave the codebase in a deployable state.

```bash
git add .
git commit -m "feat(inspections): create inspection API and service"
```

---

## Session hygiene during BUILD

Start of session:
```
/hermes-next  ← what am I working on today?
```

During session — watch for:
- Context above 50% → suggest `/compact`
- Jumping to a new feature before completing the current one → redirect
- Horizontal thinking ("let me build all the routes") → redirect to vertical

End of session:
```
task-master done [id]   ← mark completed tasks
/compact                ← always compact at session end during BUILD
```

---

## Gate triggers during BUILD

After each feature merges to main:
```
QA review due   → /hermes gate review
```

After auth + billing complete:
```
Security review due → /hermes gate review
```

After all MVP features complete, move to stage 08 REVIEW:
```
Full gate review → /hermes gate review
Then stage 09 DEPLOY
```
-e 
---

## Backlog during build

After each feature completes and gate review runs:
- The QA persona updates `02-development.md` test coverage items
- The Security Auditor updates `03-security.md` items if auth/data touched
- Run `/hermes-status` to see updated backlog % after each gate

If a backlog item is deliberately skipped: record in `DECISIONS.md` + `RISKS.md`.
