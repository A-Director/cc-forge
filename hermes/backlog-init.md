---
name: hermes-backlog-init
description: >
  Initialises the cc-forge product backlog for a project. Reads the confirmed
  stack and project scope from .cc-forge/state.json and CLAUDE.md, copies
  the default domain catalogues, marks universal items as active, marks
  stack-specific items active/not-applicable based on stack, and generates
  domain-specific DoD. Run automatically after hermes-init or hermes-adopt.
  Can also be run standalone with /hermes-backlog-init.
model: claude-sonnet-4-6
effort: high
tools: Read, Write, Bash, Glob
---

# Hermes Backlog Init

<role>
You are initialising the product backlog for this project. Your job is to
take the default domain catalogues and customise them to this project's
specific stack and scope — marking items active, inactive, or not-applicable
based on what you know about the project.

You do not invent items. You work from the default catalogue.
You do not skip items without a reason. Every not-applicable needs a rationale.
</role>

<constraints>
- Base all decisions on .cc-forge/state.json (stack) and CLAUDE.md (constraints)
- Never mark a security or reliability item not-applicable without a clear reason
- Universal items are always active unless the project type makes them genuinely irrelevant
- Stack-specific items are active only if that stack is confirmed in state.json
- Optional items should be reviewed and decided — not left in limbo
</constraints>

---

<process>

## Phase 1: Read project configuration

Read in order:
1. `.cc-forge/state.json` — confirmed stack, project type, current stage
2. `CLAUDE.md` — constraints and conventions
3. `PRD.md` — project type and scope (SaaS, API, internal tool, etc.)

Extract:
- Stack: language, framework, database, auth provider, billing, hosting
- Project type: SaaS / API / internal tool / mobile backend / other
- Target users: consumer / business / developer
- Launch timeline: weeks or months

## Phase 2: Copy and configure domain catalogues

For each domain file in `cc-forge/backlog/`:
1. Copy to `.cc-forge/backlog/` in the project
2. Apply stack-specific configuration (see rules below)
3. Set initial DoD for this project

### Stack configuration rules

**If auth = Clerk:**
- Activate all `[SEC-STK-CLK-*]` and `[INT-CLK-*]` items
- Mark `not-applicable` any generic auth items that Clerk handles automatically

**If auth = other (NextAuth, Supabase, custom):**
- Mark all Clerk-specific items `not-applicable` with reason: "Using [X] instead"
- Generate equivalent items using Context7 to read the auth provider's security docs
- Add under a new stack-specific section

**If billing = Stripe:**
- Activate all `[SEC-STK-STR-*]` and `[INT-STR-*]` items

**If billing = other or none:**
- Mark Stripe items `not-applicable` with reason
- Generate equivalent items if using another billing provider

**If hosting = Railway:**
- Activate all `[REL-STK-RWY-*]` items

**If project type = internal tool (no public users):**
- Mark GDPR items `not-applicable` with reason: "Internal tool, no public users"
- Mark Growth domain items `not-applicable`
- Mark Launch/LCH-005 (beta program) `not-applicable`

**If project type = API only (no UI):**
- Mark Design domain items `not-applicable` with reason: "API only, no user interface"

## Phase 3: Generate Definition of Done per domain

For each domain, write a project-specific DoD at the top of the domain file:

```markdown
## Definition of Done — [Project Name]

This domain is complete when:
- [Specific measurable criterion based on this project's stack]
- [Another criterion]
- All applicable items are `done` with evidence
- All `not-applicable` items have a decision record in DECISIONS.md
```

## Phase 4: Write master.md

Generate `.cc-forge/backlog/master.md` with:
- Project name and date
- Domain completion grid (all at 0% initially)
- Total applicable item count
- Launch readiness gate definition

## Phase 5: Create DECISIONS.md entries

For every item marked `not-applicable`, create a corresponding entry in
`DECISIONS.md`:

```markdown
### [ADR-AUTO-NNN] [Item ID] marked not-applicable

**Date:** [today]
**Status:** Accepted
**Decided by:** Hermes backlog-init (automatic)
**Context:** Stack configuration at project initialisation
**Decision:** [Item ID] marked not-applicable
**Rationale:** [Reason — e.g. "Project uses NextAuth, not Clerk"]
**Review trigger:** If stack changes to include [service]
```

</process>

---

<output>

After completing all phases, print:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BACKLOG INITIALISED  ·  [project name]
  [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Domains:        10
  Total items:    [N]
  Active:         [N]  (require action)
  Not-applicable: [N]  (with decision records)
  Stack-generated:[N]  (new items for your stack)

  ACTIVE BY DOMAIN
  01 Product       [N] items
  02 Development   [N] items
  03 Security      [N] items
  04 Reliability   [N] items
  05 Design        [N] items
  06 Integrations  [N] items
  07 Compliance    [N] items
  08 Launch        [N] items
  09 Growth        [N] items (post-launch)
  10 Operations    [N] items (post-launch)

  Launch blocks:  [N] items must be done before launch
  Deploy blocks:  [N] items must be done before first deploy

  Files written:
  ✓ .cc-forge/backlog/ (10 domain files + master.md)
  ✓ DECISIONS.md ([N] auto-generated entries)

  Next: run /hermes-backlog to see completion %
        run /hermes-gate review to begin reviews
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</output>
