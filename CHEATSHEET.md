# cc-forge cheat sheet

> What to run and when. Keep this open in a tab.
> First time? See [INSTALL.md](./INSTALL.md) for setup instructions.

**Two pillars:** **Hermes** directs the session (orchestrates, speaks last with one next step); **Argus** watches the framework (deterministic self-check, auto-fires at session close, flags drift). Hermes directs, Argus watches, personas judge your project at gates.

---

## Installation (first time only)

```bash
# 1. Clone cc-forge to a permanent location
git clone https://github.com/A-Director/cc-forge.git ~/cc-forge

# 2. Install the cc-forge plugin (inside Claude Code)
/plugin marketplace add ~/cc-forge
/plugin install cc-forge@cc-forge
# (Plugin system handles commands, hooks, personas, standards, catalogue.)

# 3. Install other plugins you use
/plugin install claude-mem
/plugin install superpowers
# → restart Claude Code after each

# 4a. New project
mkdir my-project && cd my-project && git init
bash ~/cc-forge/scripts/hermes-bootstrap.sh   # creates .cc-forge/, state.json, gitignore
claude                    # open Claude Code
/hermes-init              # complete setup via interview

# 4b. Existing project
cd your-project
bash ~/cc-forge/scripts/hermes-bootstrap.sh   # idempotent
claude                    # open Claude Code
/hermes-adopt             # gap report + setup
```

## Keeping cc-forge updated

```bash
# When cc-forge releases updates — run inside any project:
/hermes-update
# Pulls latest personas, standards, commands from cc-forge
# Never touches: backlog, CLAUDE.md, state.json, decisions, risks
```

---

## Starting a project

| Scenario | Command |
|---|---|
| Brand new project, blank folder | `/hermes-init` |
| Existing codebase, joining mid-project | `/hermes-adopt` |

**`/hermes-init`** — interviews you, recommends a stack, generates `CLAUDE.md` + `PRD.md` stub, initialises Taskmaster, sets up GitHub Actions. Start here for every new project.

**`/hermes-adopt`** — reads your entire repo (code, docs, git history, migrations), produces a gap report, generates `CLAUDE.md` from actual code, seeds Taskmaster from current reality. Run this if cc-forge wasn't there from day one.

---

## Every session

| When | Command | What it does |
|---|---|---|
| First thing every session | `/hermes-status` | Stage, next task, backlog %, flags — run this before anything else |
| What to work on | `/hermes-next` | Highest-priority unblocked task with full context |
| End of session | `/compact` | Compress session into summary before closing |

Run `/hermes-status` before touching any code. Run `/compact` before closing any session.
Never skip `/compact` — a healthy session produces a better summary than a degraded one.

---

## During build

| When | Command | What it does |
|---|---|---|
| Unsure about a decision | `/criticalthink` | Scores confidence, exposes assumptions, flags risks |
| Side thought mid-session | `/btw` | Parallel channel — doesn't interrupt main task |
| Session feels slow | `/context` | Shows every item in context window with token counts |
| Switching to unrelated work | `/clear` | Wipes context, fresh session |

**Rule:** One task per session where possible. Genuinely unrelated work deserves a fresh context.

---

## PDLC vs SDLC — the nesting in one paragraph

cc-forge runs **two** lifecycles. **SDLC** (the 11 stages: idea → iterate) is *what activity you're doing*. **PDLC** (5 phases: MVP → Beta → Pilot → Launch → Growth) is *what maturity bar you're shooting for*. Each PDLC phase consumes many SDLC cycles. Phase changes the bar each backlog domain must hit. See `PHASES.md` for definitions and `session-lifecycle/phase-gates.md` for the gate distinction.

| Lifecycle | Gate command | Frequency |
|---|---|---|
| SDLC (within phase) | `/hermes-gate-review` | Many per phase — features, deploys, design changes |
| PDLC (between phases) | `/hermes-phase-gate` | 3–5 per project total |

Every backlog item carries a `**Phase:**` field — the earliest phase a typical SaaS project needs the item done.

---

## Reviews and gates

| When | Command | What it does |
|---|---|---|
| New requirement/bug/change to triage | `/hermes-intake` | Triage before it becomes work-in-flight; logged for reconciliation |
| Feature merged to main | `/hermes-gate-review` | Triggers QA + Security (if auth/data touched) |
| Design approved | `/hermes-gate-review` | Triggers CTO + UX Expert |
| Before any deploy | `/hermes-gate-review` | Triggers CTO + SRE + Security Auditor |
| Advancing PDLC phase (MVP→Beta etc.) | `/hermes-phase-gate` | Full-panel review, bumps state.json current_phase, dedicated commit |
| Framework self-check on demand | `/hermes-argus` | Deterministic — names every deviation (also auto-fires at session close) |

**Gate outcomes:**
- `PASS` — proceed
- `CONDITIONAL` — proceed, fix named issues by deadline
- `BLOCK` — do not proceed, fix first

**Hard rule:** No deploy without SRE + Security gate. No exceptions.

---

## Deploy and monitor

| When | Command | What it does |
|---|---|---|
| Ready to ship | `/hermes-deploy` | Pre-flight checks → gate verification → Railway push |
| Review session | `/hermes-report` | Full usage report — paste into Claude.ai to review together |
| Need a one-glance view | `/hermes-dashboard` | Generate `dashboard.html` — backlog, risks, decisions, framework cost |
| cc-forge updated | `/hermes-update` | Pull latest personas, standards, commands from cc-forge into this project |

`/hermes-deploy` pre-flight checks: tests passing, build succeeds, TypeScript clean, lint clean, npm audit, RUNBOOK.md exists, SRE gate passed, Security gate passed. Stops if anything fails.

---

## Persona quick reference

| Persona | Model | Activates at |
|---|---|---|
| CTO | Opus | After design · before deploy |
| Security auditor | Opus | Before every deploy · after auth/payment changes |
| SRE engineer | Sonnet | Before every deploy |
| QA engineer | Sonnet | After every feature merge |
| UX expert | Sonnet | After design · after build |
| Product owner | Sonnet | After each sprint |
| CEO | Opus | Sprint end · before launch |
| CFO | Haiku | Weekly · infra cost check |
| Legal / compliance | Sonnet | Before first public launch |
| Market analyst | Sonnet | Monthly · at pivots |
| Growth agent | Sonnet | Post-launch · monthly |
| Research agent | Opus | On demand · technology decisions |
| **Argus** | **deterministic** | **Auto-fires at session close · before deploy · on demand** |

Personas run as independent subagents with clean context windows — they don't see each other's findings, which prevents bias. Argus is the exception: it's a deterministic script (not a judging persona) that watches the *framework*, never your code.

---

## Hermes voice — what to expect

Hermes closes every significant action with a summary. You never need to ask "what next?" — Hermes tells you.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  [what just happened]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ [Completed]
  ✓ [Committed / recorded]
  Stage:    [N] [NAME]
  Backlog:  [N]%
  Next:     [Single clearest next action — stated, not asked]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

| After this | Hermes says |
|---|---|
| Task complete | Next task or gate review due |
| Gate review | Outcome + next task or conditions to close |
| Session start | Stage + next task + one flag if urgent |
| Blocker found | What's blocked + how to unblock |

**One next step. Always stated. Never asked as a question.**

---

## Token golden rules

```
CLAUDE.md          Keep under 600 tokens. No task state. No docs.
                   Only what Claude would get wrong without being told.

Right model        Opus   → hard planning, architecture, personas (CEO/CTO/Security)
                   Sonnet → daily build, refactoring, most personas
                   Haiku  → simple lookups, CFO report, quick checks

Vertical slices    One feature end-to-end (DB → service → API → UI → test)
                   Never horizontal phases (all models first, then all routes...)

@file refs         Never paste files. Use @filename.md — pulled in on demand.

Specific prompts   "Fix [BUG] in @[file] that causes [X] instead of [Y]"
                   Never: "fix the bug"

MCPs               Only connect what you need. Every MCP loads into context
                   at session start whether used or not.

/compact           Run at end of each phase, not when Claude starts forgetting.
                   Proactive, not reactive.

New task           Genuinely unrelated work = new session. /clear and restart.
```

---

## Product backlog

| When | Command | What it does |
|---|---|---|
| After init or adopt | `/hermes-backlog-init` | Customises backlog for your stack, sets DoD per domain |
| Check launch readiness | `/hermes-status` | Shows % completion across all 10 domains |
| After any gate review | Persona updates domain file | Each persona ticks off their items with evidence |
| Override an item | Mark `not-applicable` | Triggers DECISIONS.md + RISKS.md entries automatically |

**The 10 backlog domains:**
```
01 Product        PRD alignment, scope, success metrics
02 Development    Code quality, tests, CI gates
03 Security       OWASP, auth, secrets, hardening
04 Reliability    Monitoring, runbook, incident response
05 Design         UX, accessibility, performance
06 Integrations   Clerk, Stripe, third-party services
07 Compliance     GDPR, ToS, data retention
08 Launch         Domain, SSL, email, beta program
09 Growth         SEO, analytics, activation (post-launch)
10 Operations     Support, FinOps, cost tracking (post-launch)
```

**Launch is blocked until** domains 01-08 are 100% (done or not-applicable with decision record).

---

## Decision log and risk register

| When | Action |
|---|---|
| Technology or architecture choice | Add entry to `DECISIONS.md` |
| Backlog item marked not-applicable | Hermes auto-adds to `DECISIONS.md` |
| Security/reliability item deferred | Hermes auto-adds to `RISKS.md` |
| Gate bypassed | Hermes auto-adds to both |

**The rule:** nothing is silent. Every override has a paper trail.

---

## Session flow (at a glance)

```
SESSION START
  /hermes-status          ← orient (Hermes; surfaces any Argus-staleness flag)
  /hermes-next            ← get the task
  select right model      ← Opus / Sonnet / Haiku

DURING BUILD
  @file refs over paste   ← keep context clean
  /btw for side thoughts  ← don't interrupt flow
  /criticalthink on doubt ← challenge assumptions
  /context if slow        ← diagnose bloat

FEATURE COMPLETE
  /hermes-gate-review     ← QA + Security
  task-master done [id]   ← mark complete

SESSION END
  /compact                ← always
  (Argus auto-fires)      ← framework self-check → status/argus-last-run.md
  note doc updates needed ← ARCHITECTURE.md, API.md, ENV.md etc.
```

---

## The deploy checklist

```
□ All tests passing          npm test
□ Build succeeds             npm run build
□ No TypeScript errors       npx tsc --noEmit
□ No lint errors             npm run lint
□ No critical vulnerabilities npm audit
□ RUNBOOK.md exists and complete
□ SRE gate passed
□ Security gate passed
□ Argus run (no critical drift)

Then: /hermes-deploy
```

---

## When something goes wrong

| Symptom | Action |
|---|---|
| Taskmaster drifted, going ad-hoc | Run `/hermes-adopt` to resync |
| CLAUDE.md feels stale | Run `/hermes-argus` — it will flag exactly what's wrong |
| Context window filling fast | `/context` to diagnose, `/compact` to compress |
| Session producing shallow answers | Raise effort to `xhigh`, switch to Opus |
| Gate reviews being skipped | Run `/hermes-argus` — it checks gate compliance explicitly |
| Production incident | See `RUNBOOK.md` and `INCIDENT.md` — don't improvise |

---

> Full documentation: [github.com/A-Director/cc-forge](https://github.com/A-Director/cc-forge)
