# cc-forge

> Ship real software with Claude Code — not vibes. A complete, opinionated SDLC that runs *inside* Claude Code, built around two pillars: **Hermes** directs, **Argus** watches.

cc-forge gives a solo developer or a small team the discipline of a full engineering org — CTO, Security, SRE, QA, Product — without the headcount. It is not a list of tips or a prompt pack. It is an operating system for building software with AI.

---

## The two pillars

### Hermes — the Conductor
Hermes is the orchestrating agent at the center of every session. Named after the Greek messenger who moved between all the gods, Hermes sits between you and every other agent, persona, and tool. He doesn't write the code — he makes sure the **right agent is doing the right thing at the right time**, and he always speaks last with a single clear next step. You never have to ask "what now?"

### Argus — the Watcher
Argus is Hermes's vigilant counterpart — the hundred-eyed giant who never fully slept. Where Hermes *directs*, Argus *watches*. It is **deterministic**: it checks that the framework's own contracts still hold — backlog integrity, gates actually run, no silent drift — and reports `HEALTHY` / `DEGRADED` / `BROKEN` with exact evidence. Argus **auto-fires at the end of every session** and surfaces a staleness warning at the start of the next one, so the framework can't quietly rot between check-ins.

> **Hermes directs. Argus watches. Personas judge.** Three layers, kept distinct: Hermes orchestrates the session, Argus watches the *framework* (deterministically), and the expert personas judge the *project* at gate reviews. Argus never grades your code — that's the personas' job — and it never edits your backlog. It only reports drift.

---

## Who it's for

- **Solo indie developers and founders** building real products, not demos.
- **Small teams (2–5)** who want consistent, professional engineering standards without a full org.
- **Non-engineers with technical ambition** — founders, PMs, and operators building with Claude Code for the first time.

---

## What you get

- **One-command onboarding** — `/hermes-init` for a new project, `/hermes-adopt` to onboard an existing codebase.
- **13 expert personas** reviewing your work at the right gates — CTO, Security SME, SRE, QA, Product Owner, and more.
- **A 10-domain launch-readiness backlog** grounded in real industry standards (OWASP, Google SRE, WCAG, GDPR…).
- **Deterministic self-checking** via Argus, so framework drift is caught automatically — never discovered too late.
- **Token-disciplined sessions** that stay fast and focused across an entire project, not just the first hour.

---

## Two ways to start

### `/hermes-init` — Greenfield
Starting fresh. Hermes interviews you, understands your idea, recommends a stack, and sets up the entire project: `CLAUDE.md`, a PRD stub, Taskmaster tasks, GitHub Actions, and your backlog. You start building in minutes with everything configured correctly.

### `/hermes-adopt` — Existing project
Already have a codebase? Hermes reads your entire repo — every file, doc, config, and commit pattern — and produces a gap report: what stage you're really at, what's missing, what's inconsistent, what your first tasks should be. Your existing code is the source of truth. Nothing is assumed.

---

## The command surface

cc-forge ships a focused set of `/hermes-*` commands. The ones you'll use daily are at the top.

| Command | What it does |
|---|---|
| `/hermes-status` | Project health: stage, next task, backlog %, flags. Run it first every session. |
| `/hermes-next` | The single highest-priority unblocked task, with full context. |
| `/hermes-init` | Greenfield onboarding interview + full project setup. |
| `/hermes-adopt` | Read an existing repo and produce a gap report. |
| `/hermes-backlog-init` | Customize the 10-domain backlog to your stack; set a Definition of Done per domain. |
| `/hermes-intake` | Triage a new requirement/bug/change before it becomes work-in-flight. |
| `/hermes-gate-review` | Trigger an SDLC gate — the due personas review in clean contexts. |
| `/hermes-phase-gate` | Advance a PDLC phase (MVP → Beta → Pilot → Launch → Growth) via full-panel review. |
| `/hermes-argus` | Run the framework self-check on demand (it also auto-fires at session close). |
| `/hermes-deploy` | Pre-flight checks → gate verification → Railway deploy. |
| `/hermes-dashboard` | Generate `status/dashboard.html` — a single-file project overview. |
| `/hermes-report` | Full usage report for review sessions. |
| `/hermes-update` | Pull the latest cc-forge into this project (never touches your project-specific files). |

See **[CHEATSHEET.md](./CHEATSHEET.md)** for the full "what to run and when."

---

## Two lifecycles that nest: PDLC + SDLC

The **SDLC** (Software Development Life Cycle) is *what activity you're doing right now* — the eleven stages:

```
01 IDEA → 02 SPEC → 03 PLAN → 04 DESIGN → 05 BUILD → 06 AUTH →
07 BILLING → 08 REVIEW → 09 DEPLOY → 10 MONITOR → 11 ITERATE
```

The **PDLC** (Product Development Life Cycle) sits around it — *what maturity bar the product is shooting for*:

```
Phase 1 MVP → Phase 2 Beta → Phase 3 Pilot → Phase 4 Launch → Phase 5 Growth
```

Each PDLC phase consumes many SDLC cycles. Within a phase, run `/hermes-gate-review` after features and before deploys (many per phase). Between phases, run `/hermes-phase-gate` to advance the maturity bar (a few per project). Every backlog item carries a `- Phase:` field, so the backlog naturally rolls up to per-phase target bars.

Full definitions live in `docs-templates/PHASES.md`; the gate distinction is in `session-lifecycle/phase-gates.md`.

---

## How a session works

Every Claude Code session follows the same shape automatically — you don't run these by hand.

```
SESSION OPENS
  Hermes auto-orients: reads state.json · tasks · backlog% · risks
  prints: stage · next task · one flag (and an Argus-staleness note if overdue)
  begins the first action — no question asked

BUILD LOOP
  Taskmaster → next task → code → test → lint → commit
  Hermes closes every action: ✓ done · stage · next

GATE (when due)
  /hermes-gate-review → personas run in clean contexts
  PASS · CONDITIONAL · BLOCK → backlog updated · ADRs + RISKS written

SESSION CLOSES (Hermes speaks last)
  ✓ done this session · → next task · docs to update
  Argus auto-fires: framework self-check → status/argus-last-run.md
```

**The rule:** Hermes always speaks last. Every significant action ends with a summary box — what was done, current stage, backlog %, single next step.

---

## The personas

At key gates, specialist personas review your work. Each has a specific lens and trigger — they activate at milestones, not every session.

| Persona | Lens | Model | Triggers at |
|---|---|---|---|
| CEO | Vision, value, shippability | Opus | Sprint end, before launch |
| CTO | Architecture, tech debt, scale | Opus | After design, before deploy |
| Product Owner | PRD alignment, scope | Sonnet | After each feature |
| UX SME | User flows, friction, a11y | Sonnet | After design, after build |
| QA SME | Test coverage, edge cases | Sonnet | After each feature |
| SRE SME | Reliability, runbook, ops | Sonnet | Before deploy |
| Security SME | OWASP, auth, injection | Opus | Before deploy |
| CFO | Infra cost, burn, revenue | Haiku | Weekly |
| Market Analyst | Competitors, positioning | Sonnet | Monthly, at pivots |
| Research Agent | Tech evaluation, libraries | Opus | On demand |
| Legal SME | GDPR, ToS, data handling | Sonnet | Before launch |
| Growth SME | SEO, analytics, activation | Sonnet | Post-launch |
| **Argus** | **Framework self-check (deterministic) — watches the framework, not your code** | **—** | **Auto-fires at session close · on demand · before deploy** |

---

## The product backlog

Every cc-forge project gets a structured backlog — not just dev tasks, but a launch-readiness view across **10 domains**, each with a Definition of Done.

| Domain | Owner | Blocks |
|---|---|---|
| 01 Product | Product Owner | Stage 03 |
| 02 Development | CTO + QA | Stage 08 |
| 03 Security | Security SME | Deploy |
| 04 Reliability | SRE SME | Deploy |
| 05 Design | UX SME | Launch |
| 06 Integrations | CTO | Deploy |
| 07 Compliance | Legal SME | Launch |
| 08 Launch | Product Owner | Launch |
| 09 Growth | Growth SME | Post-launch |
| 10 Operations | CFO + SRE | Post-launch |

Each item is a single canonical format (parsed by *one* shared parser — Argus, the dashboard, and the write path all agree on what a valid item is):

```markdown
### [SEC-003] All webhook endpoints verify request signatures
- Outcome: No webhook can be spoofed by an external actor
- Standard: OWASP ASVS 4.0 — V9.2.1
- Phase: 1
- Status: not-started
- Owner: sec
- Evidence: [commit / file:line / doc link]
```

`Owner` is the short persona identifier (`sec`, `cto`, `sre`, `ux`, `po`, `qa`, `legal`) — not the display name — per §3.2. Every item references the standard it comes from. Overrides go to `DECISIONS.md`; accepted risks go to `RISKS.md`. **Nothing is silent.** Launch is gated on the Phase-4 domain bars across 01–08 (see `catalogue/master.md`) — graduated targets, not a flat 100%.

**Standards backing the backlog:** OWASP Top 10 / ASVS · Google SRE Book · DORA · WCAG 2.1 AA · GDPR · Pirate Metrics (AARRR) · SOLID · JTBD. See `standards/` for the full set.

---

## The opinionated stack

cc-forge picks services so you don't have to. The onboarding agent adapts if you prefer your own.

| Layer | Choice | Why |
|---|---|---|
| Auth | Clerk | Best DX, pre-built UI, generous free tier |
| Billing | Stripe | Industry standard, best docs |
| Hosting | Railway | One-click deploy, no DevOps overhead |
| DNS / CDN | Cloudflare | Free, fast, DDoS protection |
| Error tracking | Sentry | Free tier, Railway plugin |
| Database | Railway Postgres | Co-located, automatic backups |

---

## Token discipline (the short version)

Token efficiency determines how long a Claude Code session stays useful. cc-forge enforces a handful of rules — the full 11 are in **[CHEATSHEET.md](./CHEATSHEET.md)**:

- `CLAUDE.md` is standing orders — 300–600 tokens, no task state, no docs.
- Right model for the job: Opus for hard planning, Sonnet for daily build, Haiku for simple lookups.
- `/compact` proactively at the end of each phase, not when Claude starts forgetting.
- Vertical slices (one feature end-to-end), not horizontal layers.
- New, unrelated task = new session.

---

## Getting started

**Full guide: [INSTALL.md](./INSTALL.md).** The short version:

**Prerequisites:** [Claude Code](https://claude.ai/code) (Pro or Max), Node.js 20+, Git.

```bash
# 1. Clone cc-forge somewhere permanent
git clone https://github.com/A-Director/cc-forge.git ~/cc-forge
```

```
# 2. Install the plugin (inside Claude Code)
/plugin marketplace add ~/cc-forge
/plugin install cc-forge@cc-forge
```

The plugin system handles command installation, hook registration (SessionStart, Stop, PreCompact, UserPromptSubmit), and version management.

```bash
# 3. Bootstrap your project (idempotent — safe to re-run)
cd ~/your-project
bash ~/cc-forge/scripts/hermes-bootstrap.sh
```

```
# 4. Onboard, then verify
/hermes-init       # (new project)  — or:  /hermes-adopt  (existing)
/hermes-argus      # verify the install: Layer 1 + Layer 2 should be HEALTHY
```

Keep cc-forge current anytime with `/hermes-update` — it pulls the latest personas, standards, and commands, and never touches your backlog, `CLAUDE.md`, `state.json`, decisions, or risks.

---

## What's inside

```
cc-forge/                       (the framework source)
├── .claude-plugin/             ← plugin + marketplace manifests
├── commands/                   ← the /hermes-* command set
├── personas/                   ← 13 expert persona definitions (incl. argus.md)
├── hooks/                      ← SessionStart / Stop / PreCompact / UserPromptSubmit
├── scripts/                    ← hermes-argus.py, hermes-dashboard.py, installers, _hermes_backlog.py (canonical parser)
├── catalogue/                  ← the 10-domain backlog catalogue + master.md
├── standards/                  ← coding, security, api, git, testing, a11y, token rules
├── session-lifecycle/          ← lifecycle + phase-gate definitions
├── doc-templates/ docs-templates/  ← PRD, ARCHITECTURE, RUNBOOK, INCIDENT, MONITORING, PHASES
└── DESIGN.md · README.md · INSTALL.md · CHEATSHEET.md
```

After `/hermes-init` or `/hermes-adopt`, your project gains:

```
your-project/
├── .cc-forge/        ← state.json · usage.log · backlog/ · intake-log.md · cache.json
├── status/           ← dashboard.html (gitignored) · argus-last-run.md (committed)
├── CLAUDE.md         ← standing orders
└── PRD.md · DECISIONS.md · RISKS.md · .env.example
```

---

## Philosophy

Most SDLC frameworks are written for teams with dedicated DevOps, QA, security, and product functions. Solo developers and small teams don't have those people — but they need those disciplines.

cc-forge gives you the disciplines without the headcount. Every persona, every standard, every gate exists because a real product has failed without it. The QA persona catches the edge case you'd ship. The Security SME finds the auth bug before your users do. The CFO flags the Railway bill before it surprises you. Argus catches the framework drift before it quietly corrupts the work.

You're still the one steering. cc-forge just makes sure the right expert is in the room at the right time — and that nothing slips through unnoticed.

---

## Built on the shoulders of giants

cc-forge is an orchestration framework, not an island — it works because of the tools beneath it.

- **[Claude Code](https://claude.ai/code)** — the CLI at the heart of everything; cc-forge is built entirely on its agent, plugin, MCP, and command capabilities.
- **[Taskmaster](https://github.com/eyaltoledano/claude-task-master)** by Eyal Toledano — the task-management backbone; parses your PRD into a dependency-aware task list.
- **[claude-mem](https://github.com/thedotmack/claude-mem)** — session memory across Claude Code sessions.
- **[Context7](https://github.com/upstash/context7)** by Upstash — live, version-specific library docs injected into sessions.
- **[Superpowers](https://github.com/obra/superpowers-dev)** — agentic workflow skills (brainstorm, TDD, subagent execution) powering stage 05 BUILD.
- **[slash-criticalthink](https://github.com/abagames/slash-criticalthink)** by abagames — forces Claude to score confidence and expose assumptions.

If you authored any of the above and something is misattributed, open an Issue — happy to fix it immediately.

---

## License

Open core. The core framework is **MIT** licensed; contributions welcome. Premium components (pre-built Clerk + Stripe agents, the full persona library, the status TUI) are available via [Polar.sh](https://polar.sh) to support ongoing development.

## Security

cc-forge is a collection of markdown instruction files plus a few Python/shell utilities. It sends your code to no cc-forge servers (there are none), stores nothing externally, and makes no network calls beyond npm package installation. When Hermes reads your code, that happens through Claude Code via Anthropic's API — the same as any Claude Code session. Before running on sensitive projects, confirm `.env*` is gitignored and run `npm audit`. Report security issues via a GitHub Issue marked `[SECURITY]`.

## Contributing

Issues, persona improvements, and integrations welcome — see [CONTRIBUTING.md](./CONTRIBUTING.md). Join the conversation in [GitHub Discussions](https://github.com/A-Director/cc-forge/discussions).
