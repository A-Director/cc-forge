---
name: stage-11-iterate
description: >
  Stage 11: ITERATE. The post-launch loop. Processes user feedback,
  prioritizes next features, manages tech debt, and maintains production
  health. This stage repeats indefinitely.
model: claude-sonnet-4-6
tools: Read, Write, Bash, TodoWrite
---

# Stage 11 — Iterate

You've shipped. Now you run the loop that turns a launched product
into a successful one.

Stage 11 is not a stage you complete — it's a cadence you maintain.

---

## The weekly loop

### Monday: Health check
```bash
/hermes health
```
- Review Sentry errors from the past week
- Check UptimeRobot report
- Review CFO cost report
- Review any user feedback received

Flag anything that needs urgent attention before touching new features.

### Tuesday–Thursday: Build
Work from Taskmaster. Prioritize in this order:
1. **P0/P1 bugs** — production breaks always first
2. **User-requested features** — things users are blocked on
3. **Tech debt** — items from the QA/CTO/Security backlogs
4. **New features** — items from the post-MVP list in PRD.md

Every new feature still follows the stage 05 BUILD pattern:
vertical slices, test as you go, gate review before merge.

### Friday: Review and plan
- Mark completed Taskmaster tasks
- Add new tasks from feedback/bugs discovered this week
- Run `/hermes status` to see overall project health
- Brief persona checks if warranted:
  - Monthly: Market Analyst + Growth Agent
  - Weekly: CFO (costs)

---

## Processing user feedback

When users report bugs or request features:

**Bug reports:**
1. Reproduce it
2. Add to Taskmaster as P1 (critical) or P2 (important) task
3. Fix before next feature work

**Feature requests:**
1. Check if it's already in PRD.md post-MVP list
2. If yes: prioritize based on frequency and user type
3. If no: add to PRD.md open questions, evaluate against the problem statement
   — does this request serve the core use case or is it scope drift?

**The scope discipline test:**
*"Does this feature serve the primary user doing the primary job?"*
If no — note it, don't build it yet.

---

## Tech debt management

Run `/hermes quality` and `/hermes clean` monthly.
Add tech debt items to Taskmaster with tag `debt`.
Aim to clear at least one debt item per sprint.

The rule: **debt items must not exceed 20% of the backlog.**
If you're above that, stop adding features and pay down debt first.

---

## When to run gate reviews in ITERATE

| Trigger | Personas |
|---|---|
| Any auth/payment code changed | Security Auditor |
| Significant new feature | QA + CTO |
| Monthly | Market Analyst + CFO |
| New team member or major pivot | CEO + Product Owner |
| Any production incident | SRE (post-incident review) |

---

## Signs the loop is healthy

- Sentry error rate trending down week-over-week
- p95 response time stable or improving
- Taskmaster backlog is manageable (< 30 open tasks)
- Tech debt items are being resolved, not just accumulating
- User feedback is coming in (means users are using it)
- MRR is growing (means users are paying for value)

---

## Signs the loop is broken

- Shipping features nobody uses (stop, talk to users)
- Bug count rising faster than fixes (stop, do a quality sprint)
- Context window always full at session start (review CLAUDE.md, trim)
- Skipping gate reviews "just this once" (the debt compounds)
- Working on tech debt instead of user-facing improvements (rebalance)
