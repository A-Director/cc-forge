# Hermes SDLC

> From first idea to production — a complete, Claude Code-native software development lifecycle for solo developers and small teams.

---

## What this is

Hermes is an opinionated SDLC framework built entirely around Claude Code. It gives you a structured, repeatable way to go from idea to running production app — with Hermes — the Conductor — orchestrating the process, a set of expert personas reviewing your work at each stage, and token-optimized workflows that keep Claude Code fast and focused across multiple projects.

It is not a list of tips. It is not another X thread. It is a complete operating system for building software with AI.

---

## Who it's for

- **Solo indie developers and founders** building real products, not demos
- **Small teams (2–5 people)** who want consistent, professional engineering standards without a full engineering org
- **Non-engineers with technical ambition** — founders, PMs, and operators who are building with Claude Code for the first time

---

## Two modes

### `hermes init` — Greenfield
Starting a new project from scratch. Hermes interviews you, understands your idea, recommends a stack, and sets up your entire project: CLAUDE.md, Taskmaster tasks, GitHub Actions, MCP servers, and your first PRD stub. You start building in minutes with everything already configured correctly.

### `hermes adopt` — Existing project
Already have a codebase? Hermes reads your entire repo — every file, doc, config, and commit pattern — and produces a gap report: what stage you're actually at, what's missing, what's inconsistent, and what your first tasks should be. Your existing code becomes the source of truth. Nothing is assumed.

---

## The lifecycle

```
01  IDEA       →  Hermes interviews you, understands the problem
02  SPEC       →  PRD Agent writes the product requirements document
03  PLAN       →  Taskmaster breaks PRD into dependency-aware tasks
04  DESIGN     →  Superpowers brainstorm + architecture decisions
05  BUILD      →  Subagent-driven development with TDD
06  AUTH       →  Clerk setup agent (standard, pre-baked)
07  BILLING    →  Stripe setup agent (standard, pre-baked)
08  REVIEW     →  Persona gate: CTO + QA + Security review
09  DEPLOY     →  Railway deploy agent (CI/CD, env vars, domain)
10  MONITOR    →  Sentry + Cloudflare + uptime setup agents
11  ITERATE    →  Back to Taskmaster — next task, next sprint
```

Each stage has a dedicated agent. Stages feed into each other. Nothing is manual unless you want it to be.

---

## Hermes — the Conductor

Hermes is the orchestrating agent at the center of your SDLC. Named after the Greek messenger god who coordinated between all other gods — Hermes sits between you and every other agent, persona, and tool in this framework.

He doesn't write the code. He makes sure the right agent is doing the right thing at the right time.

```
hermes init          # start a new project
hermes adopt         # onboard an existing project  
hermes status        # project health: stage, tasks, personas, docs
hermes next          # what should I work on right now?
hermes gate review   # trigger a persona gate review
hermes deploy        # run the deploy agent
```

---

## The personas

At key phase gates, specialist personas review your work. Each has a specific lens, a specific model, and specific trigger conditions. They do not all run every session — that would be chaos. They activate at milestones.

| Persona | Lens | Model | Triggers at |
|---|---|---|---|
| CEO | Vision, value, shippability | Opus | Sprint end, before launch |
| CTO | Architecture, tech debt, scale | Opus | After design, before deploy |
| Product Owner | PRD alignment, scope | Sonnet | After each feature |
| UX Expert | User flows, friction, a11y | Sonnet + Claude Design | After design, after build |
| QA Engineer | Test coverage, edge cases | Sonnet + Outcomes | After each feature |
| SRE Engineer | Reliability, runbook, ops | Sonnet | Before deploy |
| Security Auditor | OWASP, auth, injection | Opus + Claude Security | Before deploy |
| CFO | Infra cost, burn, Stripe revenue | Haiku | Weekly |
| Market Analyst | Competitors, positioning | Sonnet | Monthly, at pivots |
| Research Agent | Tech evaluation, library choices | Opus + Context7 | On demand |
| Legal / Compliance | GDPR, ToS, data handling | Sonnet | Before launch |
| Growth Agent | SEO, analytics, activation | Sonnet | Post-launch |
| **Argus** | **Framework compliance monitor — watches all other agents** | **Opus** | **Weekly + before deploy** |

---

## The standards

Every project using Hermes follows the same standards. They load automatically into your CLAUDE.md at init or adopt time.

- `standards/coding.md` — naming, structure, complexity, comments
- `standards/security.md` — OWASP top 10, secrets management, auth rules
- `standards/api.md` — REST conventions, versioning, error formats
- `standards/git.md` — branching strategy, commit messages, PR rules
- `standards/testing.md` — coverage minimums, unit vs integration vs e2e
- `standards/accessibility.md` — WCAG basics, baked in from day one
- `standards/token-rules.md` — 12 golden rules for token-optimized CC sessions

---

## The minimum document set

Every Hermes project maintains a living set of documents. Hermes creates them, keeps them updated, and reviews them at each gate.

**Created at init/adopt:**
- `CLAUDE.md` — Claude Code standing orders (kept under 600 tokens)
- `PRD.md` — product requirements
- `ARCHITECTURE.md` — system design and decisions
- `DECISIONS.md` — architecture decision records (ADRs)
- `CHANGELOG.md` — auto-updated on every merge

**Created during build:**
- `API.md` — endpoint documentation
- `ENV.md` — environment variables (non-secret values + descriptions)

**Created before deploy:**
- `RUNBOOK.md` — how to operate the app in production
- `INCIDENT.md` — what to do when things break
- `MONITORING.md` — what's watched, alert thresholds, escalation

---

## How a session works

Not everything fires every session. That would fill your context window and produce noise, not signal.

**Every session — automatic:**
- CLAUDE.md loads (standing orders, ~400 tokens)
- claude-mem injects last session context
- Taskmaster surfaces the next task
- Right model selected for the task type

**During build — triggered by task:**
- Superpowers brainstorm activates on new features
- Context7 activates when touching a library
- criticalthink available on-demand via `/criticalthink`
- `/btw` for parallel thoughts without interrupting flow

**Phase gates — triggered by milestone:**
- After design → CTO + UX review
- After feature → QA + Security review
- After sprint → Product Owner alignment
- Weekly → CFO cost check + Market Analyst scan
- Before deploy → SRE + full Security audit

**Every session end — automatic:**
- `/compact` summarizes the session
- Taskmaster marks completed tasks
- GitHub Action syncs updated docs
- Dreaming scheduled for overnight memory refinement

---

## The product backlog

Every cc-forge project gets a structured product backlog — not just a list of development tasks, but a complete launch-readiness view across every domain.

**10 domains, each with a Definition of Done:**

| Domain | Owner | Blocks |
|---|---|---|
| 01 Product | Product Owner | Stage 03 |
| 02 Development | CTO + QA | Stage 08 |
| 03 Security | Security Auditor | Deploy |
| 04 Reliability | SRE Engineer | Deploy |
| 05 Design | UX Expert | Launch |
| 06 Integrations | CTO | Deploy |
| 07 Compliance | Legal / Compliance | Launch |
| 08 Launch | Product Owner | Launch |
| 09 Growth | Growth Agent | Post-launch |
| 10 Operations | CFO + SRE | Post-launch |

**Backlog item format:**
```markdown
### [SEC-003] All webhook endpoints verify request signatures

**Outcome:** No webhook can be spoofed by an external actor
**Standard:** OWASP ASVS 4.0 — V9.2.1
**Owner:** Security Auditor
**Blocks:** Stage 09 DEPLOY
**Applicability:** Stack: Stripe, Clerk
**Status:** not-started | in-progress | done | not-applicable
**Evidence:** [commit / file:line / doc link]
```

Every item references the standard it comes from. Override decisions go into `DECISIONS.md`. Accepted risks go into `RISKS.md`. Nothing is silent.

**Methodology:** outcome-oriented items (JTBD), Kanban flow states, single Product Owner accountability. See `standards/prompt-standards.md` for the full standards map.

## Standards referenced

cc-forge backlog items are grounded in established industry standards.

| Domain | Standards |
|---|---|
| Security | OWASP Top 10 · OWASP ASVS 4.0 · NIST CSF |
| Reliability | Google SRE Book · DORA metrics · AWS Well-Architected |
| Design | WCAG 2.1 AA · Nielsen's 10 Heuristics · Core Web Vitals |
| Compliance | GDPR Articles · CCPA · ePrivacy Directive |
| Growth | Pirate Metrics (AARRR) · Google HEART Framework |
| Operations | FinOps Foundation principles |
| Development | Google Engineering Practices · SOLID · TypeScript Strict |
| Product | JTBD Framework · Google HEART |
| Launch | cc-forge opinionated standard |

## The stack

Hermes is opinionated about services so you don't have to decide:

| Layer | Choice | Why |
|---|---|---|
| Auth | Clerk | Best DX, pre-built UI, generous free tier |
| Billing | Stripe | Industry standard, best docs |
| Hosting | Railway | One-click deploy, no DevOps overhead |
| DNS / CDN | Cloudflare | Free, fast, DDoS protection |
| Error tracking | Sentry | Free tier, Railway plugin |
| Uptime | UptimeRobot | Free, reliable |
| Domain | Namecheap | Agent can check availability and suggest names |
| DB | Railway Postgres | Co-located, automatic backups |

The onboarding agent asks about your stack. If you want to deviate from defaults, it adapts. If you don't have a preference, it configures everything above automatically.

---

## Token rules (the golden 12)

Token efficiency is not optional — it determines how long Claude Code stays useful in a session before hitting limits. These 12 rules are enforced by Hermes across every session:

1. **CLAUDE.md is your standing orders** — 300–600 tokens, no task state, no docs
2. **`/context` is your memory profiler** — know what's in your window
3. **`/compact` proactively** — run at end of each phase, not when degrading
4. **`/commands` for repeated sequences** — deterministic beats probabilistic
5. **Reasoning mode off for simple tasks** — renaming a variable needs no deep thought
6. **`/btw` for parallel thoughts** — never interrupt the main task thread
7. **Right model for the job** — Opus for hard planning, Sonnet for daily build, Haiku for simple queries
8. **`@file` references over paste** — never paste entire files into chat
9. **Specific prompts over lazy prompts** — name the file, the bug, the expected outcome
10. **MCPs are not Pokémon** — every connected MCP loads into context; only connect what you need
11. **New task = new session** — genuinely unrelated work deserves a fresh context
12. **Vertical slices, not horizontal phases** — build end-to-end features, not DB-then-API-then-UI layers

---

## What's inside

```
hermes-sdlc/
├── README.md                     ← you are here
├── HERMES.md                     ← Hermes agent definition
├── hermes/
│   ├── init.md                   ← greenfield onboarding flow
│   ├── adopt.md                  ← existing project onboarding flow
│   └── commands/
│       ├── status.md
│       ├── next.md
│       ├── gate-review.md
│       └── deploy.md
├── standards/
│   ├── coding.md
│   ├── security.md
│   ├── api.md
│   ├── git.md
│   ├── testing.md
│   ├── accessibility.md
│   └── token-rules.md
├── personas/
│   ├── ceo.md
│   ├── cto.md
│   ├── product-owner.md
│   ├── ux-expert.md
│   ├── qa-engineer.md
│   ├── sre-engineer.md
│   ├── security-auditor.md
│   ├── cfo.md
│   ├── market-analyst.md
│   ├── research-agent.md
│   ├── legal-compliance.md
│   └── growth-agent.md
├── stages/
│   ├── 01-idea/
│   ├── 02-spec/
│   ├── 03-plan/
│   ├── 04-design/
│   ├── 05-build/
│   ├── 06-auth/
│   ├── 07-billing/
│   ├── 08-review/
│   ├── 09-deploy/
│   ├── 10-monitor/
│   └── 11-iterate/
├── docs-templates/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── DECISIONS.md             ← decision log (upgraded to first-class)
│   ├── RISKS.md                 ← risk register (new)
│   ├── RUNBOOK.md
│   ├── INCIDENT.md
│   └── MONITORING.md
├── backlog/                     ← product backlog catalogue (new)
│   ├── master.md                ← overall % completion view
│   ├── 01-product.md
│   ├── 02-development.md
│   ├── 03-security.md
│   ├── 04-reliability.md
│   ├── 05-design.md
│   ├── 06-integrations.md
│   ├── 07-compliance.md
│   ├── 08-launch.md
│   ├── 09-growth.md
│   └── 10-operations.md
├── session-lifecycle/
│   ├── session-start.md
│   ├── phase-gates.md
│   └── session-end.md
└── scripts/
    ├── hermes-install.sh
    └── hermes-init.sh
```

---

## Getting started

**New project:**
```bash
git clone https://github.com/yourusername/hermes-sdlc
cd your-new-project
/hermes init
```

**Existing project:**
```bash
cd your-existing-project
/hermes adopt
```

Hermes will take it from there.

---

## Philosophy

Most SDLC frameworks are written for teams with dedicated DevOps, QA, security, and product functions. Solo developers and small teams don't have those people — but they need those disciplines.

Hermes gives you the disciplines without the headcount.

Every persona, every standard, every gate exists because a real product has failed without it. The QA persona catches edge cases you'd ship. The Security Auditor finds the auth bug before your users do. The CFO flags the Railway bill before it surprises you. The SRE engineer writes the runbook before 3am when you need it.

You're still the one steering. Hermes just makes sure the right expert is in the room at the right time.

---

## Built on the shoulders of giants

cc-forge is an orchestration framework, not an island. It works because of
the tools it sits on top of. Full credit where it's due:

### Open source tools

**[Taskmaster](https://github.com/eyaltoledano/claude-task-master)** by Eyal Toledano
The task management backbone of cc-forge. Taskmaster parses your PRD into a
dependency-aware task list and keeps Claude Code oriented across sessions.
cc-forge would not have a persistent planning layer without it.

**[claude-mem](https://github.com/thedotmack/claude-mem)**
Session memory for Claude Code. Captures what happened in each session,
compresses it intelligently, and injects relevant context into future sessions.
Solves the "Claude forgot what we built last week" problem.

**[Context7](https://github.com/upstash/context7)** by Upstash
Injects live, version-specific library documentation directly into Claude Code
sessions. Stops Claude from hallucinating outdated APIs. Used every time you
touch a library.

**[Superpowers](https://github.com/obra/superpowers-dev)**
Structured agentic workflow skills for Claude Code — brainstorming, TDD,
subagent execution, and code review. Powers the stage 05 BUILD workflow.

**[slash-criticalthink](https://github.com/abagames/slash-criticalthink)** by abagames
A `/criticalthink` command that forces Claude to score its own confidence,
expose hidden assumptions, and flag risks in any response. Used throughout
cc-forge whenever a decision needs scrutiny.

### Anthropic products and features

**[Claude Code](https://claude.ai/code)** — the CLI at the heart of everything.
cc-forge is a framework built entirely around Claude Code's agent, plugin,
MCP, and command capabilities.

**[Claude Code Action](https://github.com/anthropics/claude-code-action)** —
the GitHub Action that auto-syncs docs on PR merge and enables `@claude`
in issues and PRs. Powers the documentation stewardship in cc-forge.

**[Claude Design](https://claude.ai/design)** — Anthropic Labs product used
by the UX Expert persona for visual outputs, prototypes, and design reviews.

**[Claude Security](https://claude.ai/security)** — scans codebases for
security flaws and writes patches via Claude Code. Augments the Security
Auditor persona with Anthropic-native scanning capability.

**[Managed Agents / Agent Teams](https://docs.anthropic.com/claude/docs/agents)**
— the multi-agent orchestration layer that makes persona gate reviews possible.
Each persona runs as an independent subagent with its own clean context window.

**[Dreaming](https://docs.anthropic.com/claude/docs/dreaming)** — Anthropic's
scheduled memory refinement feature. cc-forge's session-end protocol triggers
Dreaming to extract patterns and improve context quality over time.

### Standards and inspiration

**Token rules** — informed by the community post
*"10 Tips to Stop Burning Your Tokens in Claude Code"* by Habib Mohammed,
and Boris Cherny's (creator of Claude Code) public guidance on session management.

**Prompt standards** — sourced directly from Anthropic's official
[Claude 4 Prompting Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
documentation, distilled for the cc-forge context.

---

If you're the author of any of the above and something is incorrectly
attributed or described, please open an Issue — happy to fix it immediately.

## License

Open core. Core framework is MIT licensed. Contributions welcome.

Premium components (pre-built Clerk + Stripe agents, full persona library, hermes status TUI) available via [Polar.sh](https://polar.sh) for a small monthly fee that supports ongoing development.

---

## Security

cc-forge is a collection of markdown instruction files. It contains no
executable code beyond two shell scripts for installation that install
well-known open source packages via npm.

**What cc-forge does NOT do:**
- Send your code to any cc-forge servers (there are none)
- Store any project data externally
- Execute automatically without your input
- Make any network calls beyond npm package installation

**What happens to your code:**
When Hermes reads your codebase during `hermes adopt` or any session,
that code is processed by Claude Code via Anthropic's API — the same
as any standard Claude Code session. Review
[Anthropic's privacy policy](https://www.anthropic.com/privacy) if
this is a concern for your project.

**Before running on sensitive projects:**
- Confirm `.env` and `.env.local` are in `.gitignore`
- Confirm no secrets are hardcoded in source files
- Run `npm audit` to check for vulnerable dependencies

**Reporting a security issue:**
If you find a security vulnerability in cc-forge itself, please open
a GitHub Issue marked `[SECURITY]` rather than a public discussion.

## Contributing

Issues, persona improvements, stage agents, and MCP integrations welcome. See `CONTRIBUTING.md`.

Join the conversation: [GitHub Discussions](https://github.com/yourusername/hermes-sdlc/discussions)
