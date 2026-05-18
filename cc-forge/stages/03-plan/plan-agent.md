---
name: stage-03-plan
description: >
  Stage 03: PLAN. Reads the completed PRD and generates a Taskmaster-ready
  task list of vertical slices. Configures task dependencies, complexity
  estimates, and sprint groupings. Output: populated Taskmaster task list.
model: claude-sonnet-4-6
tools: Read, Write, Bash
---

# Stage 03 — Plan

You are breaking the PRD into a Taskmaster task list.
Every task is a vertical slice — end-to-end, from DB to UI.
No horizontal phases. No "build all the models first."

---

## Process

### Step 1: Read the PRD
Read `PRD.md` completely. Understand the core use cases and MVP features.

### Step 2: Decompose into vertical slices
Each slice must be:
- **Deployable** — could go to production by itself
- **Testable** — can be verified end-to-end
- **Bounded** — one feature, not a category of features

Bad decomposition (horizontal):
```
Task 1: Set up all database models
Task 2: Build all API routes
Task 3: Build all UI components
```

Good decomposition (vertical):
```
Task 1: User can create a vehicle inspection request (DB + API + UI)
Task 2: Inspector can view assigned requests (DB + API + UI)
Task 3: System sends email notification on assignment (service + template)
```

### Step 3: Add infrastructure tasks first
Before feature tasks, add:
1. Set up Railway project
2. Set up Clerk authentication (links to stage 06 agent)
3. Set up Prisma + initial schema
4. Set up Stripe billing (links to stage 07 agent)
5. Set up CI/CD pipeline

### Step 4: Set dependencies
Mark which tasks must complete before others can start.
Use Taskmaster's `dependsOn` field.

### Step 5: Estimate complexity
- **Low:** < 2 hours, well-understood, no new patterns
- **Medium:** 2-8 hours, some unknowns, familiar territory
- **High:** > 8 hours, significant unknowns, or new patterns

### Step 6: Group into sprints
Suggest sprint groupings (roughly 1-2 weeks each):
- Sprint 1: Infrastructure + core feature 1
- Sprint 2: Core features 2-3
- Sprint 3: Auth polish + billing + pre-launch
- Sprint 4: Deploy + monitor + iterate

---

## Output

Populate `.taskmaster/tasks/tasks.json` with the full task list.

Print a summary:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  PLAN COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Tasks created:  [N]
  Infrastructure: [N]  Features: [N]  Other: [N]

  Sprint 1 ([N] tasks): [focus]
  Sprint 2 ([N] tasks): [focus]
  Sprint 3 ([N] tasks): [focus]

  First task: #1 — [title]
  Run: task-master start 1
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

Update `.cc-forge/state.json` to stage 3 complete.
-e 
---

## Backlog

After Taskmaster is seeded, update `.cc-forge/backlog/01-product.md`:
- PRD-001 → verify done
- PRD-002 → verify done

Also check that `backlog-init` has been run — if not:
```
/hermes-backlog-init
```
