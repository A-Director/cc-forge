# Changelog

All notable changes to cc-forge itself are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

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
