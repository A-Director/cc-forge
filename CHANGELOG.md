# Changelog

All notable changes to cc-forge itself are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Fixed — Session 0 install unblock (marketplace manifest + plugin.json author)

Session 0 shipped `.claude-plugin/plugin.json` but no `.claude-plugin/marketplace.json`, which made cc-forge uninstallable via the standard Claude Code plugin flow — same trap claude-mem hit. `/plugin install <path>` requires a marketplace manifest pointing at the plugin. Without it, install fails.

- **New `.claude-plugin/marketplace.json`** — single-plugin marketplace at the cc-forge repo root. Marketplace name `cc-forge`, plugin entry name `cc-forge`, `source: "./"` (plugin lives at the marketplace root, the common single-plugin-repo pattern). Validated end-to-end with `claude plugin validate`, `claude plugin marketplace add`, `claude plugin install cc-forge@cc-forge`, and `claude plugin list`. Status reports `√ enabled`; `~/.claude/settings.json` `enabledPlugins` populated automatically.
- **Fixed `.claude-plugin/plugin.json`** — `author` was a string in Session 0 (`"author": "A-Director"`); the schema requires an object. `claude plugin validate` was failing with `author: Invalid input: expected object, received string`. Now `"author": {"name": "A-Director"}`. The plugin would have failed to install even with a marketplace until this was fixed.
- **Install commands updated everywhere.** README, CHEATSHEET, `scripts/hermes-install.sh`, `scripts/hermes-bootstrap.sh`, `scripts/hermes-migrate-to-plugin.sh` (steps 6 + log + final report), and `commands/update.md` all now show the two-step `/plugin marketplace add <path>` then `/plugin install cc-forge@cc-forge`, not the broken one-step `/plugin install <path>`.
- **README note on auto-enable bug [#17832](https://github.com/anthropics/claude-code/issues/17832).** The directory-marketplace auto-enable bug ("installed but not in enabledPlugins") is documented as a post-install manual step for users on older CLI versions. Verified clean on CLI v2.1.161 — the bug doesn't manifest in current Claude Code; `enabledPlugins` populates correctly on install. The README note covers the edge case for v2.1.x users on earlier minor versions.

**Verified install flow (v2.1.161):**
```
$ claude plugin marketplace add /home/user/cc-forge
√ Successfully added marketplace: cc-forge
$ claude plugin install cc-forge@cc-forge
√ Successfully installed plugin: cc-forge@cc-forge (scope: user)
$ claude plugin list
  > cc-forge@cc-forge
    Version: 1.0.0
    Status: √ enabled
$ claude plugin details cc-forge@cc-forge
  Skills (14)  adopt, backlog-init, dashboard, deploy, doctor, gate-review,
               init, log, next, phase-gate, report, status, taskmaster-seed, update
  Hooks (4)    SessionStart, Stop, PreCompact, UserPromptSubmit
```

This unblocks the pilot project's reset and any future cc-forge install.

### Session 0 — plugin conversion + format unification + doctor skeleton

Per the v3 plan agreed in design. Major restructuring; the pilot migration is a
separate operator action that runs the shipped migration script under the
spec §4.7 safety (dry-run, backup, rollback).

**Plugin layout (spec §4):**
- New `.claude-plugin/plugin.json` — manifest declaring cc-forge as a
  Claude Code plugin at v1.0.0.
- New `hooks/` directory with `hooks.json` declaring SessionStart, Stop,
  PreCompact, and UserPromptSubmit handlers, plus three executable
  handler scripts. `hermes-session-start.sh` and `hermes-handoff.sh`
  close the §1 "Hermes closure regression" — session_start and
  session_end events now logged deterministically by hooks.
  `hermes-prompt-submit.sh` is a v1.0.0 stub; the full per-prompt
  framing lands in Session D.
- New `migrations/` directory with README documenting the
  forward-only schema-migration convention. No migrations ship at v1.0.0.
- New `personas/_shared/phase-names.json` and `stage-names.json` —
  canonical name maps per §4.3 layout.

**File moves (no `hermes/` directory remains):**
- `hermes/commands/*.md` → `commands/*.md` (9 files).
- `hermes/{init,adopt,backlog-init,log,update}.md` → `commands/` (5
  files).
- `hermes/token-weights.json` → repo root (Layer 1 canonical).
- `backlog/*.md` → `catalogue/*.md` (11 files: 10 domain + master).
- Deleted: duplicate `hermes/hermes-init.sh`.

**Format unification (spec §3.2 strict canonical):**
- Every catalogue item migrated from bold-field form (`**Field:** value`)
  to canonical list-item form (`- Field: value`) per spec §3.2. Standalone,
  re-runnable, dry-run-able transform: `scripts/hermes-migrate-backlog-format.sh`.
- Transform is **fidelity-gated, not conformance-gated** per the v3 plan
  correction: the gate proves the sed preserved every field and every
  value with no stray markers; it does NOT halt on pre-existing data
  gaps (which §3.2 line 644 grandfathers for one transition cycle).
  Carry-forward audit buckets gaps into "grandfathered per §3.2 (missing
  Standard)" vs "pre-existing violation, needs cleanup (other required
  fields)". 90 items × 8 fields = 720 field/value pairs migrated with
  fidelity-passed verdict and zero data gaps in the cc-forge catalogue.
- Writer migration alongside: 13 files updated so personas, commands,
  and the dashboard reader all produce/consume the canonical list form.
  Covers `personas/_shared/backlog-update-protocol.md`, 7 gate-review
  personas, `commands/taskmaster-seed.md`, `commands/backlog-init.md`
  (including the Phase 6 verification regex), `commands/gate-review.md`
  ADR template, `commands/init.md` ADR template,
  `scripts/hermes-dashboard.py` line 219 (`field_pat` regex).
- Completeness verification: `grep -rln '^\*\*[A-Z][A-Za-z-]*:\*\*'` across
  catalogue/commands/personas/scripts returns no line-anchored bold
  declarations. Inline-prose `**Validation:**`-style section headers are
  intentional and not field declarations.

**Doctor skeleton (Layer 1 / Layer 2 file-existence only):**
- New `scripts/hermes-doctor.py` ships Layer-1 and Layer-2 file-existence
  checks per spec §5.3 (subset). Versioned `--json` output (schema_version
  1.0.0) per §5.6 (E-2). Exit codes 0/1/2 for HEALTHY/DEGRADED/BROKEN.
  Full check catalogue (format-violation stratification, cache freshness,
  banner-rendering caveat, intake reconciliation) lands in the Doctor
  session.
- New `commands/doctor.md` declares `/hermes-doctor` with
  `allowed-tools: Read, Bash` and `context: fork`.

**token-weights path migration (spec §4.3 Layer 1):**
- Canonical at `${CLAUDE_PLUGIN_ROOT}/token-weights.json`; per-project
  overrides at `.cc-forge/overrides/token-weights.json`. Override
  consulted first, fall back to canonical, fall back to in-code defaults.
- `scripts/hermes-dashboard.py` updated to read from the canonical path.

**Install / update unification (gap #51):**
- `commands/update.md` rewritten per §4.6: no file copies, delegates to
  `/plugin update`, runs migrations, verifies via doctor, reports. The
  prefix-strip and copy-list-drift failure modes from gap #50/#52 cannot
  recur because there is no copy.
- `scripts/hermes-install.sh` reduced to a thin redirect telling the
  operator to run `/plugin install`. The global-command-install
  responsibility is gone; the plugin owns it.
- `scripts/hermes-bootstrap.sh` (new) handles project-bootstrap
  responsibility split off from the old install script per #4.

**Command frontmatter standardisation (F-3):**
- Every command declares `allowed-tools` (renamed from the previous
  no-op `tools:` field where it existed; added where it didn't).
  Read-only commands (`status`, `next`, `report`, `doctor`) get
  read-only sets; mutating commands (`dashboard`, `gate-review`,
  `phase-gate`, `deploy`, `update`, `taskmaster-seed`, `init`,
  `adopt`, `backlog-init`, `log`) declare exactly what they touch.
- `dashboard`, `gate-review`, `phase-gate`, `doctor` declare
  `context: fork` per F-2 (fork is an optimisation, not a correctness
  mechanism — every forkable command produces correct results when
  silently run inline too).

**Pre-plugin → plugin migration script (the pilot project + future):**
- New `scripts/hermes-migrate-to-plugin.sh` ships the 12-step migration
  with `--dry-run`, `--rollback`, step-wise log, and the fidelity-gated
  catalogue-format migration inside step 8. The pilot migration is a
  separate operator action — this PR ships the script but does not run
  it against any real project.

**README + CHEATSHEET updated** for the plugin install flow.

This PR contains no behaviour against a pilot project or any other real project.
The migration script's dry-run output is the next review checkpoint
before any apply.

### Fixed — gap #52: /hermes-update not propagating Session C deliverables
- `/hermes-dashboard` failed on first use in any project that updated
  after Session C. The command invokes `scripts/hermes-dashboard.py`,
  but `/hermes-update` only copied markdown files (personas, standards,
  commands, catalogue) — it never copied the Python script or the
  `hermes/token-weights.json` calibration file.
- Added `scripts/*.py` and `hermes/token-weights.json` to the
  `/hermes-update` copy list (separate blocks with their own
  existence guards, since older cc-forge clones may not have them).
  Calibration lands at `hermes/token-weights.json` to match the
  read path the dashboard generator already uses
  (`__file__.parent.parent / "hermes" / "token-weights.json"`), so
  the copied file is actually consulted at runtime.
- Added a delivery-verification block at the end that warns loudly
  if Session C deliverables are missing after an update — same
  defense-in-depth pattern as PR #19's gap #50 second pass.
- Banner extended with `✓ [N] scripts → scripts/` and
  `✓ 1 calibration → .cc-forge/token-weights.json` lines (omitted
  when the respective sources don't exist).
- Discovered when the pilot project first ran `/hermes-dashboard` on 2026-05-22.
- Pattern note for future sessions: every session that ships
  non-markdown files (Python scripts, JSON configs, HTML templates,
  etc.) must also extend `/hermes-update`'s copy list. A Session F
  audit item — "what does cc-forge ship that `/hermes-update`
  doesn't copy?" — would surface any other slip-throughs.

### Fixed — gap #50 hotfix, second pass
- The 2026-05-21 hotfix for gap #50 landed in the repo but did not change
  `/hermes-update`'s observable behaviour. The pilot project's 2026-05-22 update run
  produced unprefixed files (`dashboard.md`, `status.md`, `next.md`,
  `update.md`, `report.md`, `gate-review.md`, `deploy.md`,
  `phase-gate.md`, `taskmaster-seed.md`) — the same bug as before.
- Root cause: `hermes/commands/update.md` is a prompt for a Haiku-class
  agent, not a shell script. The bash inside it is suggestive, not
  executed verbatim. Three signals in the file pushed Haiku toward the
  buggy shortcut: (1) the comment contained the buggy `cp *.md` form as
  literal backtick'd syntax, (2) the personas section directly above
  the commands section uses a legitimately-bare `cp "$HERMES_DIR"/personas/*.md
  .cc-forge/personas/` pattern that Haiku mimicked when it reached the
  commands section, and (3) there was no post-copy verification, so a
  slip succeeded silently.
- This pass:
  - Removed the buggy command from the comment (replaced with a
    no-shell-syntax description) so Haiku can't latch onto it.
  - Added an explicit `<constraints>` bullet forbidding the bare-wildcard
    form, calling out the personas-section pattern as the lookalike, and
    requiring the verification step to run.
  - Added a hard verification block after cleanup: greps
    `.claude/commands/` for any unprefixed file in the legacy basename
    list and `exit 2`s with a `✗ FOUND ... — gap #50 regression` message
    if any are found. Silent slip → loud failure.
  - Added `update`, `init`, `adopt`, `backlog-init`, `log` to the
    legacy-cleanup basename list. The pilot project's run showed `update.md`
    surviving, which the previous list missed.
- Added a verification trace requirement in the prompt protocol so
  future hotfixes are walked through end-to-end before being declared
  complete.

### Fixed — gap #50: /hermes-update prefix bug
- `/hermes-update` was silently stripping the `hermes-` prefix when
  copying command files, corrupting the user's command namespace on
  every update. The install script (`hermes-install.sh`) correctly
  added the prefix; the update command did not — producing `/update`,
  `/status`, `/next` without prefix that shadowed the canonical
  `/hermes-*` versions.
- Fixed by matching the install script's prefix-on-copy pattern in
  `hermes/commands/update.md`.
- Added cleanup of unprefixed legacy files from previous
  `/hermes-update` runs. Run `/hermes-update` once to apply both the
  fix and the cleanup to any existing project. The post-update banner
  reports the cleanup count when non-zero (gap #50 hotfix).

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
Two the pilot project-dogfooding gaps closed: (#48) `/hermes-backlog-init` was
silently stripping `**Standard:**` lines when it rewrote items per
stack; (#47) persona gate reviews surfaced findings as Taskmaster
tasks but never updated the parent backlog items, so tasks orphaned
from the standards-grounded backlog and the pilot project's 22 ticked Phase 1.5
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
- Existing the pilot project-shaped backlog files (no `Phase` field) continue to
  parse — the `Phase` line is optional in the task description.
- Existing projects whose backlog items lack `Standard` lines (the
  gap #48 victims) will hit `standards_strip_detected` events when
  they next run init or when a persona tries to seed a task. The
  expected fix path: re-run `/hermes-backlog-init` once it has the
  fix in place; affected items get their Standards restored from the
  template.
- The 3-step protocol is enforced for **new** gate reviews going
  forward. The pilot project's existing 22 ticked Phase 1.5 conditions and IMP-*
  tasks are not retrofitted by this work — that's a future the pilot project
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
SDLC cycles; phase changes the bar each domain must hit. The pilot
project's informal "Phase 1 / Phase 1.5" terminology proved the pattern in
practice — this release formalizes it as a first-class concept
across templates, agents, and the backlog.

---

## Earlier changes

Earlier changes were tracked via PR history only — see the
[merged PRs on GitHub](https://github.com/A-Director/cc-forge/pulls?q=is%3Apr+is%3Amerged)
for the full trail.
