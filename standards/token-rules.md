# Token Rules — The Golden 12

Token efficiency is not optional. It determines how long Claude Code stays
useful in a session, how much parallelism you can run, and ultimately how
much you get done per dollar. These 12 rules are enforced by Hermes across
every session.

---

## Rule 1 — CLAUDE.md is your standing orders

CLAUDE.md is loaded on every session and persists in the context window the
entire time. It is not evicted when not needed.

**Target: 300–600 tokens.** If yours is over 2,000 tokens, you are storing
task state or documentation that does not belong there.

What belongs in CLAUDE.md:
- Exact stack versions
- Build and test commands
- Naming conventions specific to this project
- Key architectural constraints ("controllers call services, services call DB")
- Things Claude will get wrong without being told

What does NOT belong:
- Task status or what you built last session (that's claude-mem's job)
- Documentation that belongs in ARCHITECTURE.md or API.md
- Generic best practices Claude already knows

Run `/init` to generate a baseline, then trim ruthlessly.

---

## Rule 2 — `/context` is your memory profiler

At any point, run `/context` to see every item occupying your context window:
open files, attached documents, tool definitions, conversation turns, system
prompt, and running token counts per element.

Use it to:
- Spot files pulled in that are no longer needed
- Identify when a conversation thread has grown too long
- Decide between `/compact` and a fresh session

Think of it as `htop` for your context window. Run it before any large task.

---

## Rule 3 — `/compact` proactively, not reactively

A healthy session produces a better compact summary than a degraded one.

**Run `/compact` when you finish a distinct phase** — not when Claude starts
forgetting things. End of a feature, end of a debugging session, end of a
refactor. That's the right time.

What `/compact` preserves: architectural decisions, files modified, current
task state, next steps, errors and how they were resolved.

What it discards: intermediate reasoning, superseded approaches, raw tool outputs.

If you are done with a task entirely and moving to something unrelated, use
`/clear` instead — it wipes context completely and resets the session.

---

## Rule 4 — `/commands` for repeated sequences

Natural language prompts are probabilistic — the same prompt produces slightly
different behaviour each run. Commands are deterministic.

Define named commands for multi-step sequences you run repeatedly:
- Test + fix type errors + lint in sequence
- Generate a component with your folder conventions
- Write a commit message in your team's format
- Pre-deploy validation checks

Store commands in `.claude/commands/`. Invoke with `/command-name`.

---

## Rule 5 — Turn off reasoning mode for simple tasks

Claude runs extended internal reasoning before every response by default.
For hard problems this is valuable. For renaming a variable it is pure waste.

Use `/model` to swap reasoning mode off for simple tasks. Turn it back on
when planning something complex.

Rule of thumb:
- Architecture decisions, hard bugs, system design → reasoning on, Opus
- Daily feature implementation, refactoring, tests → Sonnet, reasoning default
- Simple lookups, quick questions, file reads → Haiku, reasoning off

---

## Rule 6 — `/btw` for parallel thoughts

When you have a side thought while Claude is working, `/btw` opens a parallel
inference channel. The response never gets injected into the main conversation
history. The main task continues uninterrupted.

Never interrupt Claude mid-task with a new idea. Use `/btw` to capture it,
review it when Claude finishes.

---

## Rule 7 — Right model for the right job

Default model on Max plan is Opus. That is expensive. Use it deliberately.

| Task | Model |
|---|---|
| Planning hard problems, architecture decisions | Opus |
| Feature implementation, refactoring, tests | Sonnet |
| Simple questions, file lookups, quick checks | Haiku |
| Persona reviews (CTO, CEO, Security) | Opus |
| Persona reviews (QA, SRE, Product Owner) | Sonnet |
| CFO cost checks, simple doc updates | Haiku |

The advisor strategy: Opus providing advice to Sonnet on hard decisions gives
frontier-model quality at a fraction of the cost. Use it for persona reviews.

---

## Rule 8 — `@file` references over paste

Never paste entire files into chat. The content becomes dead weight in
conversation history, travelling with every subsequent message.

Use `@filename.md` to reference files. They are pulled in exactly when needed
and do not persist through the session by default.

If you need Claude to read a file, say `@src/lib/auth.ts`. Do not copy its
contents into the prompt.

---

## Rule 9 — Specific prompts over lazy prompts

Vague prompts invite verbose responses and waste tokens on intent-parsing.

**Bad:** "Fix the bug in the login flow"
**Good:** "Fix the 401 error in `@src/api/auth/login.ts` line 47 that returns
401 when the JWT is valid but expired — it should refresh, not reject"

Structure: `Fix [BUG] in @[file] that causes [unexpected outcome] instead of [expected outcome]`

Specificity is not pedantry. It is the difference between 2 turns and 8 turns.

---

## Rule 10 — MCPs are not Pokémon

Every connected MCP server loads its full tool definitions and schema into
your context window at session start, whether you use it or not.

These definitions are not small. Stack four together and you have lost
thousands of tokens before writing a single line.

The Hermes recommended MCP stack:
- `task-master-ai` — always on
- `context7` — always on (lightweight)
- `claude-mem` — always on

Everything else: connect per-project when needed, disconnect when done.
Run `/context` to see the actual token cost of each connected MCP.

---

## Rule 11 — New task = new session

Related tasks can reuse context for efficiency. Genuinely new tasks deserve
a fresh session.

If you just shipped a feature and want to start work on a completely different
part of the codebase: `/clear`, brief context message to orient the new session,
then go. Do not drag a 40-turn session on authentication into a session about
the billing integration.

Use `hermes next` at the start of each session to get oriented without
re-explaining everything.

---

## Rule 12 — Vertical slices, not horizontal phases

AI coding agents default to horizontal phasing: build the whole DB layer, then
the whole API layer, then the whole frontend. This delays end-to-end feedback
until the last phase and makes it nearly impossible to validate that the whole
system works until everything is built.

Build vertical slices: one complete feature end-to-end (DB migration + service
logic + API endpoint + UI component + test) before moving to the next feature.

Every slice is deployable. Every slice is testable. Every slice proves the
system works before you add more to it.

This is enforced in Taskmaster task structure. Every task generated from a PRD
should be a vertical slice, not a layer.

---

## Bonus — Turn management (from Boris Cherny, creator of Claude Code)

Every turn is a branching point. After Claude ends a turn, deliberately choose:

- **Continue** — Claude keeps going on the same task
- **`/rewind`** — go back to a previous state (use when Claude went down a wrong path)
- **`/clear`** — wipe context, start fresh on something new
- **`/compact`** — summarize and compress before continuing
- **Subagent** — hand off a bounded task to a clean-context specialist

The worst thing you can do is let a session drift without intentional turn
management. Every turn compounds. Bad turns compound badly.

Before sending a message in a long session, ask: should this go in this session
at all, or should I compact and continue?

---

## Quick reference card

```
Context window filling up?    → /context to diagnose, /compact to compress
Done with a distinct phase?   → /compact before continuing
Done with the task entirely?  → /clear for the next task
Side thought mid-session?     → /btw (doesn't pollute main history)
Repeated multi-step task?     → define a /command
Reading a file?               → @filename, never paste
Complex planning?             → Opus + reasoning on
Daily implementation?         → Sonnet + reasoning default
Simple question?              → Haiku + reasoning off
Too many MCPs?                → /context, disconnect unused ones
Starting unrelated work?      → new session
Building a feature?           → vertical slice, not a layer
```
