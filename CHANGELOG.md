# Changelog

All notable changes to cc-forge itself are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added — /hermes-dashboard (Session C)
A new read-only dashboard command. Reads the project's standards-grounded
markdown sources and emits a single self-contained `dashboard.html` at the
project root. Markdown stays the source of truth; the dashboard is a
regeneratable view layer.

- **`scripts/hermes-dashboard.py`** — new stdlib-only generator. Reads
  `.cc-forge/state.json`, `PHASES.md`, `.cc-forge/backlog/master.md`, all
  10 domain backlog files, `RISKS.md`, `DECISIONS.md`, `.cc-forge/usage.log`,
  and (best-effort) `~/.claude/projects/<hash>/conversation-*.jsonl` for raw
  Claude Code token data. Degrades gracefully when any source is missing —
  each section shows a tasteful empty state rather than crashing. No
  external dependencies (no jinja2, no markdown library — hand-rolled
  field-line parsing plus string-template substitution).
- **`hermes/commands/dashboard.md`** — `/hermes-dashboard` command spec,
  covering invocation, source files read, output banner, regeneration
  cadence guidance, and per-source degradation behaviour.
- **`hermes/token-weights.json`** — calibration data for the Hermes
  overhead estimate. Editable so users can re-tune for their stack
  (e.g. heavier CLAUDE.md ≠ default). v1 estimates from log; v2 will
  measure directly via a SessionEnd hook.
- **HTML template embedded in the generator script** — derived from
  `docs-templates/dashboard-prototype.html` (the design reference, kept
  pristine). Tabbed layout (Backlog / Risks / Decisions / Usage), KPI
  row, exact CSS/aesthetic from the prototype.
- **PDLC phase rendering** — header now shows a phase pill (e.g. "Phase
  2 · Beta") alongside the stage pill. The Launch-readiness banner
  rebases to "Phase N readiness". Per-domain cards show current % vs
  phase target (e.g. "78% / 80% target") with met/miss colouring and a
  target marker on the progress bar. A new "Phase exit criteria"
  section between readiness and the domain grid renders the parsed
  bullets from PHASES.md plus a "N/M domains met" headline.
- **Drift indicators** — a three-card row on the Backlog tab shows:
  observed orphan items (in-progress backlog items with no Taskmaster
  reference — current state), logged `orphan_task` events (from
  `usage.log`, Session B schema), and logged `missing_coverage` events
  (template gaps). Each card is colour-graded by count. The Usage tab's
  "Hermes session discipline" panel additionally counts
  `standards_strip_detected` events.
- **`README.md`** — `/hermes-dashboard` and `/hermes-phase-gate` added
  to the command list. New "Understanding framework cost" section
  explains the 5–25% Hermes overhead range, the three cost contributors
  (CLAUDE.md context, commands, persona gates), and when to regenerate
  the dashboard.
- **`scripts/hermes-init.sh`** + **`hermes/hermes-init.sh`** —
  `dashboard.html` added to the gitignore template so generated output
  doesn't get committed accidentally.

### Honest about methodology
The Hermes overhead is an **estimate**, not a measurement. Token-weights
are calibrated from cc-forge command file sizes; turns-per-session is a
heuristic. The dashboard says so explicitly: every estimated number
carries a footnote citing source, and the Hermes overhead card is
labelled *"Estimated from .cc-forge/usage.log · per-command weights ×
invocation counts · v2 will measure directly via hook."*

### Fixed / Added — backlog-grounding discipline (Session B)
Two CLARK-dogfooding gaps closed: (#48) `/hermes-backlog-init` was
silently stripping `**Standard:**` lines when it rewrote items per
stack; (#47) persona gate reviews surfaced findings as Taskmaster
tasks but never updated the parent backlog items, so tasks orphaned
from the standards-grounded backlog and CLARK's 22 ticked Phase 1.5
conditions referenced Taskmaster IDs and persona prefixes but no
backlog IDs.

- **`hermes/backlog-init.md`** — added explicit standards-preservation
  rules to Phase 2 customisation logic and a mandatory **Phase 6
  verification** pass that greps for `**Standard:**` lines in every
  customised file, refuses to print the success banner if any
  customised item is missing a Standard, and logs each offender as
  `type=standards_strip_detected`. New failure banner shape returned
  on verification failure with the offending item IDs and their
  expected Standard refs.
- **`personas/_shared/backlog-update-protocol.md`** — new shared
  subroutine. Every gate-review persona references it instead of
  duplicating rules. Defines the mandatory 3-step update: identify
  parent backlog item → mark `in-progress` with Taskmaster task ID
  as in-flight evidence → seed Taskmaster task via the helper with
  Standard copied verbatim. Includes correctly-formed and malformed
  examples; specifies logging shape; covers orphan and
  missing-coverage flows.
- **`hermes/commands/taskmaster-seed.md`** — new internal helper.
  Enforces task title format `[<BACKLOG-ID>] <action>` and a
  structured description (Parent / Standard / Outcome / Phase /
  Acceptance / Source). Errors if the title doesn't lead with a
  backlog ID, if Standard is missing, or if the parent backlog ID
  isn't found at the referenced path. Personas invoke this — they no
  longer craft Taskmaster tasks freehand.
- **`personas/security-auditor.md`** — fully updated as the canonical
  example. New `<backlog_update>` section references the shared
  protocol, lists owned items, mandates a `BACKLOG UPDATES` output
  section, and includes a worked example end-to-end (finding →
  parent identification → backlog edit → taskmaster-seed invocation).
- **`personas/cto.md`** · **`personas/qa-engineer.md`** ·
  **`personas/sre-engineer.md`** · **`personas/ux-expert.md`** ·
  **`personas/product-owner.md`** · **`personas/legal-compliance.md`** —
  each gate-review persona's `<backlog_update>` block rewritten to
  reference the shared protocol, list owned items, and require a
  closing `BACKLOG UPDATES` output section. Product Owner additionally
  audits cross-domain backlog drift.
- **`hermes/log.md`** — schema extended with four new entry types:
  `orphan_task` (persona seeded a task with no backlog parent),
  `missing_coverage` (finding has no matching backlog item — indicates
  cc-forge template gap), `standards_strip_detected` (caught during
  backlog-init Phase 6 verification or by taskmaster-seed), and
  `phase_transition` (Session A — added here so the schema is the
  single source of truth). "When each Hermes command logs" table
  updated with the new triggers.
- **`backlog/master.md`** — new "Standards-grounding guarantee" section
  at the top documenting that every item carries a `**Standard:**`
  line, that `/hermes-backlog-init` Phase 6 verifies this, and that
  personas update items via the shared protocol. Orphan and
  missing-coverage events are called out as framework drift signals.

### Rationale
The backlog can only be standards-grounded if (a) `Standard:` lines
survive customisation at init time and (b) work-in-flight stays
attached to the parent backlog item. (a) is a small bug with a
durable verification step — the verification is the contribution,
since it catches future regressions too. (b) is enforced by routing
all task creation through a shared helper that demands the parent
backlog ID and the Standard reference. The shared-protocol-file
approach (rather than per-persona duplication) keeps the rules in
one place when they evolve.

### Backwards compatibility
- Existing CLARK-shaped backlog files (no `Phase` field) continue to
  parse — the `Phase` line is optional in the task description.
- Existing projects whose backlog items lack `Standard` lines (the
  gap #48 victims) will hit `standards_strip_detected` events when
  they next run init or when a persona tries to seed a task. The
  expected fix path: re-run `/hermes-backlog-init` once it has the
  fix in place; affected items get their Standards restored from the
  template.
- The 3-step protocol is enforced for **new** gate reviews going
  forward. CLARK's existing 22 ticked Phase 1.5 conditions and IMP-*
  tasks are not retrofitted by this work — that's a future CLARK
  session.

### Added — PDLC phases foundation
- **`docs-templates/PHASES.md`** — new template defining five PDLC
  phases (MVP, Beta, Pilot, Launch, Growth) with per-phase goals,
  exit gates, active personas, and per-domain bars. Defaults tuned
  for a typical SaaS-shaped project; `/hermes-backlog-init` tunes
  per stack at init time.
- **`stages/00-phase-gate/phase-gate-agent.md`** — new agent that
  runs PDLC phase transitions: validates exit criteria, invokes
  full-panel persona review, bumps `state.json` `current_phase`,
  writes CHANGELOG entry, requires a dedicated `chore(phase):`
  commit.
- **`hermes/commands/phase-gate.md`** — new `/hermes-phase-gate`
  command, distinct from regular `/hermes gate review` (SDLC).
- **`session-lifecycle/phase-gates.md`** — new file explaining the
  SDLC-vs-PDLC gate distinction with a consolidated trigger map.
- **`backlog/master.md`** — added "Current PDLC phase" header,
  per-phase target-bars view, and `operator-action` as a fifth
  backlog status (alongside `not-started`, `in-progress`, `done`,
  `not-applicable`).
- **`backlog/*.md`** — every backlog item across all 10 domain
  files now carries a `**Phase:**` field (1 MVP, 2 Beta, 3 Pilot,
  4 Launch, 5 Growth). Existing items without a phase remain
  backwards-compatible.
- **`README.md`** + **`CHEATSHEET.md`** — new "PDLC vs SDLC"
  section explaining the nesting and how phases relate to stages.
- **`examples/`** — new folder scaffold for real session captures
  (`session-closures/`, `gate-reviews/`, `status-snapshots/`,
  `phase-transitions/`). Captures are verbatim, not synthesized.

### Rationale
cc-forge today ships eleven SDLC stages (activities — plan, design,
build, test, deploy, monitor) but nothing capturing **what maturity
bar are we shooting for**. PDLC phases fill that gap. Industry
convention: SDLC nests inside PDLC. Each PDLC phase consumes many
SDLC cycles; phase changes the bar each domain must hit. Clark's
informal "Phase 1 / Phase 1.5" terminology proved the pattern in
practice — this release formalizes it as a first-class concept
across templates, agents, and the backlog.

---

## Earlier changes

Earlier changes were tracked via PR history only — see the
[merged PRs on GitHub](https://github.com/A-Director/cc-forge/pulls?q=is%3Apr+is%3Amerged)
for the full trail.
