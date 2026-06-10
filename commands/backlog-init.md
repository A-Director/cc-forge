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
allowed-tools: Read, Write, Bash, Glob
invocation: user
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
- **Standards preservation is mandatory.** Every backlog item carries a
  `- Standard:` line that anchors the item to a real, externally-defined
  rule (OWASP ASVS, WCAG, GDPR Article, vendor security doc). When you
  customise an item — renaming the ID, rewriting the outcome, or adapting
  the language to this project — the `- Standard:` line MUST be preserved
  verbatim from the template. Phase 6 verifies this; do not skip it.
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

### Standards preservation — non-negotiable

When customising any item (renaming IDs like `SEC-001` → `SEC-UNI-001`,
rewording outcomes to use project-specific language, swapping vendor
names), the following lines MUST be carried over verbatim from the
template:

- `- Standard:`  (the external rule reference — OWASP ASVS, WCAG, GDPR
  Article, vendor security doc, etc.)
- `- Phase:`     (the PDLC phase from Session A, if present in template)
- `- Owner:`     (which persona owns this item)

You may freely rewrite:
- The item ID (to add project-specific suffixes like `-UNI-` for "universal
  in this project's context")
- The `- Outcome:` line (to use project domain language)
- The `- Applicability:` line (to record the per-project decision)
- The `- Status:` and `- Evidence:` lines (project state)
- The `- Blocks:` line if the gate name differs

The rule of thumb: **anything that points outside the project** (Standard,
Phase, Owner) is template-anchored and immutable during customisation.
**Anything that describes this project specifically** (ID suffix, Outcome
wording, Status) can be customised.

If a template item has no `- Standard:` line in the first place, that's a
template bug — log a `type=standards_strip_detected` event (see
`hermes/log.md`) and refuse to customise the item until the template is
fixed. Do not silently propagate a missing-Standard line into the
project.

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
- Date: [today]
- Status: accepted
- Decided by: Hermes backlog-init (automatic)
- Context: Stack configuration at project initialisation
- Decision: [Item ID] marked not-applicable
- Rationale: [Reason — e.g. "Project uses NextAuth, not Clerk"]
- Review trigger: If stack changes to include [service]
```

## Phase 6: Verify standards preservation (MANDATORY)

Before printing the success output, run a verification pass over every
domain file you customised. This catches the gap-#48 class of bug: an
accidental rewrite that strips the `Standard` line off an item.

For each domain file in `.cc-forge/backlog/0*.md`:

```bash
# Count of items in the customised file (each starts with "### [ID]")
PROJ_ITEMS=$(grep -c "^### \[" .cc-forge/backlog/<file>.md)

# Count of Standard lines in the customised file (canonical list form per §3.2)
PROJ_STANDARDS=$(grep -c "^- Standard:" .cc-forge/backlog/<file>.md)

# Count of Standard lines in the source template
TPL_STANDARDS=$(grep -c "^- Standard:" ${CLAUDE_PLUGIN_ROOT}/catalogue/<file>.md)
```

Verification rules:

1. **Every customised item must have a Standard line.**
   If `PROJ_STANDARDS < PROJ_ITEMS`, at least one item was customised
   without preserving its Standard. Identify which item(s) by running:
   ```bash
   awk '/^### \[/{id=$0; std=0} /^- Standard:/{std=1} /^---/{if(id&&!std)print id; id=""}' \
     .cc-forge/backlog/<file>.md
   ```
   Log a `type=standards_strip_detected` entry to `.cc-forge/usage.log`
   for each offender (see `hermes/log.md` schema).
   **ERROR OUT** — do not print the success banner. Fix the missing
   Standards by re-copying from the template, then re-run verification.

2. **Standard counts should match template within tolerance.**
   `PROJ_STANDARDS` should be ≤ `TPL_STANDARDS` (customisation can mark
   items not-applicable but cannot add Standards from thin air). If
   `PROJ_STANDARDS > TPL_STANDARDS`, something duplicated — investigate
   before proceeding.

3. **Spot-check verbatim preservation.**
   For three randomly sampled items per domain, read the customised
   `- Standard:` line and the template `- Standard:` line for the same
   item-by-ID-prefix. They must match character-for-character. If they
   differ (other than trivial whitespace), log
   `type=standards_strip_detected` and error out.

Verification is the durable contribution of this command — even if
future customisation logic introduces a new way to strip Standards, this
phase catches it.

### Verification example — sample customisation

Given template item:
```
### [SEC-001] All API routes protected by authentication middleware
- Outcome: All API routes are protected by authentication middleware
- Standard: OWASP ASVS 4.0 — V4.1.1
- Owner: Security SME
- Phase: 1 (MVP)
```

Correctly-customised project item:
```
### [SEC-UNI-001] All FastAPI routes protected by Clerk middleware
- Outcome: All FastAPI routes are protected by Clerk middleware
- Standard: OWASP ASVS 4.0 — V4.1.1        ← preserved verbatim
- Owner: Security SME                  ← preserved
- Phase: 1 (MVP)                            ← preserved
```

Incorrectly-customised (the gap-#48 case — verification MUST catch this):
```
### [SEC-UNI-001] All FastAPI routes protected by Clerk middleware
- Outcome: All FastAPI routes are protected by Clerk middleware
- Owner: Security SME
- Phase: 1 (MVP)
```
Missing Standard line. Phase 6 errors out, logs
`standards_strip_detected`, refuses to print success banner.

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

  Standards preservation: [N]/[N] items carry Standard lines (verified)
  Standards-strip events: 0   (any non-zero = init refused to complete)

  Next: run /hermes-status to see completion %
        run /hermes-gate-review to begin reviews
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

If Phase 6 verification failed, print the failure banner instead:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  BACKLOG INIT  ·  FAILED  ·  standards preservation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  [N] item(s) customised without preserving the Standard line:

  03-security.md:
    • SEC-UNI-001 — template Standard: OWASP ASVS 4.0 — V4.1.1 (missing)
    • SEC-UNI-006 — template Standard: OWASP ASVS 4.0 — V7.4.1 (missing)

  Each event logged to .cc-forge/usage.log as type=standards_strip_detected.

  Init refused to print success banner. Fix the items above by copying
  the `- Standard:` line back from the template, then re-run
  /hermes-backlog-init.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</output>
