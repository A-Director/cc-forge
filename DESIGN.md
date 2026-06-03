# cc-forge — Foundations Design

> **Status:** final · this is the spec
> **Date:** 2026-05-22
> **Audience:** cc-forge contributors
> **Reading time:** ~30 minutes
>
> This document specifies how cc-forge is designed: the session
> lifecycle, file format contracts, physical layout, and the
> self-check tooling. A companion rationale edition, kept by the
> maintainers, records the "why" behind each decision.

---

## §1 — Why this document exists

cc-forge is an open-source framework for Claude Code that orchestrates
software development through a conductor (Hermes), a monitor (Argus),
and a panel of domain expert personas. After two weeks of active
dogfooding on CLARK (realitybyclark.com), the framework has accumulated
significant features — PDLC phases, standards-grounded backlog with
persona linkage, a dashboard generator — and has also surfaced a class
of structural problem that requires deliberate attention before more
features are added.

The pattern visible in CLARK is this: the framework's design decisions
have been made implicitly, in flight, during individual implementation
sessions. Each session produced a working PR. Each PR landed. But the
foundations underneath — what files look like, who's responsible for
what, how lifecycle events fire, what gets distributed to projects —
were never specified anywhere. When subsystems disagree (the dashboard
parser expecting one backlog format, the templates producing another),
the disagreement is silent until something concrete breaks.

The gaps that have been caught so far through dogfooding:

- **Gap #47** — gate-review findings became orphan tasks because nothing
  required them to update parent backlog items.
- **Gap #48** — `/hermes-backlog-init` silently stripped `Standard:`
  references during project customization.
- **Gap #49** — new requirements bypassed PRD, persona review, and ADR
  check entirely (the IMP-* discovery in CLARK).
- **Gap #50** — `/hermes-update` silently corrupted command namespaces
  by stripping the `hermes-` prefix (took two hotfix attempts to
  actually fix).
- **Gap #51** — global vs project-local command directories accumulate
  stale duplicates.
- **Gap #52** — `/hermes-update` didn't propagate non-markdown
  deliverables (Python scripts, JSON config).
- **The Hermes closure regression** — the end-of-session banner pattern
  stopped firing across multiple sessions before being noticed, because
  it depended entirely on the model attending to a CLAUDE.md instruction.
- **The format fork** — the dashboard parser was written against a
  different backlog schema than `/hermes-backlog-init` produces, so
  CLARK's first dashboard render showed all zeroes.

Each gap is individually fixable. But the *pattern* matters more than
the individual instances. cc-forge has been documenting behaviors it
doesn't structurally enforce, defining file formats it doesn't validate,
shipping code that depends on prompts being followed reliably, and
assuming integration works without end-to-end testing.

Anthropic's own documentation is direct on this: *"Unlike CLAUDE.md
instructions which are advisory, hooks are deterministic and guarantee
the action happens."* The framework has been relying on advisory
mechanisms for behaviors that need deterministic guarantees. The Hermes
closure regression was, in retrospect, completely predictable: a
session-close banner enforced only by an instruction in CLAUDE.md works
while attention is fresh and decays as soon as something else competes
for attention. Two weeks was enough to demonstrate the decay.

**An important honesty correction, carried throughout this document.**
A naive reading of "hooks are deterministic" suggests the fix is simply
"move everything into hooks." It is not that simple. A hook fires
deterministically — Claude Code guarantees that. But a hook's *output*
is text injected into the model's context, and whether the model acts
on that text is a soft, statistical behavior, not a guarantee. The
determinism of hooks covers *what runs*, not *what the model does with
what runs*. This document is careful to distinguish the two. The
framework's integrity lives in deterministic side effects (logs written,
files generated, state recorded), with model-rendered output treated as
a high-reliability-but-not-guaranteed signal that the framework verifies
retrospectively. Section 2 develops this in full.

Appendix B maps each gap to the specific `/hermes-doctor` check that
would have caught it in retrospect — the clearest substantiation that
this document's foundations actually close the structural class of bugs
that produced the gaps.

This document specifies the foundations that close this class of
failure. It is deliberately narrow.

**In scope:**

- §2 — Session lifecycle: how Hermes's bookend banners work, where the
  framework's integrity actually lives, and the honest boundary between
  deterministic side effects and model-rendered output.
- §3 — Canonical file contracts for backlog items, RISKS.md,
  DECISIONS.md, state.json, usage.log, and intake-log.md.
- §4 — Three-layer physical layout: cc-forge ships as a Claude Code
  plugin (framework primitives) wrapped around per-project state and
  user-maintained documents.
- §5 — `/hermes-doctor` as concrete regression detection.
- §6 — What this document deliberately does not cover, including §6.9:
  problems the design does NOT solve, named honestly.
- §7 — Design roadmap.
- **Appendix A** — Document conventions.
- **Appendix B** — Each gap mapped to the doctor check that catches it.
- **Appendix C** — Compatibility table: current vs post-migration shape.
- **Appendix D** — Hermes responsibility table.

**Out of scope:**

- Persona behavior details — working well enough.
- PDLC phase model itself — designed in Session A, refinements come
  later.
- Dashboard visuals — the HTML prototype is the spec.
- Specific session contents for D, E, F — those implement against the
  foundations specified here.
- Implementation timelines or schedules — separate concern from design.

This document is the spec. Where existing code conflicts with what's
specified here, the document wins and the code adapts. Where this
document is silent, existing behavior stands. The conversion to plugin
form (Session 0, the next implementation session) is the first major
application of this document.

The work to produce this document is itself a recognition that the
framework's velocity has exceeded its discipline. Sessions A through C
shipped quickly because each one looked complete at the PR level. The
integration between pieces was never verified end-to-end against a real
project until CLARK tried to render a dashboard and found zeroes. The
pause here is the framework re-applying its own discipline standard —
diagnose, specify, verify — to itself.

---

## §2 — Session lifecycle and where integrity lives

This section specifies how every cc-forge session is bookended by
Hermes — an opening banner that establishes situational awareness, and
a closing handoff that records what happened. More importantly, it
specifies *where the framework's integrity actually lives*: in
deterministic side effects, not in model-rendered output.

Appendix D summarizes which Hermes responsibilities are
deterministically enforced, which are best-effort, and what the
fallback is for each.

### 2.2 Where integrity lives

The framework's integrity lives in **deterministic side effects**, not
in model-rendered output.

When the SessionStart hook fires, it deterministically:

- Reads project state and computes the current situation.
- Refreshes the session cache (`.cc-forge/cache.json`).
- Writes a `session_start` event to `usage.log`.
- Writes the computed banner to `status/last-open-banner.md`.

When the Stop / PreCompact hook fires, it deterministically:

- Tallies commits, persona invocations, and backlog changes since the
  last close.
- Writes a `session_end` event to `usage.log`.
- Writes the computed handoff to `status/last-handoff.md`.
- Refreshes dashboard-relevant cached data.

**All of these happen regardless of whether the model renders anything.**
The framework's knowledge of project state, its drift detection, its
dashboard accuracy, and its session-lifecycle integrity all derive from
these side effects. The model rendering a banner is a *user-experience
layer* on top of this deterministic substrate, not the substrate itself.

This is the key reframing: earlier designs treated the visible banner
as the enforcement mechanism. It is not. The visible banner is a
courtesy to the user. The enforcement is the side effects. If the model
never rendered a single banner, the framework's state would still be
correct, the dashboard would still be accurate, and `/hermes-doctor`
would still catch drift. The banner makes that state *visible in the
conversation*; it does not *constitute* the state.

### 2.3 The bookend banners (the visible layer)

On top of the deterministic substrate, the model renders two banners —
one at session open, one at handoff. These are the visible,
user-facing expression of the state the hooks recorded.

**Default opening banner — minimal (4–6 lines):**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES · CLARK · Phase 1.5 · Stage 10 MONITOR
  Backlog 36/63 · 4 critical risks open
  Next: #13 external uptime monitor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The default banner is deliberately minimal. CLARK CC's review noted
that the earlier 25-line banner was too heavy — twenty-five lines of
structured context on every session open (including post-compact
resumes) is a token tax and a wall of text to read past before working.
The minimal default surfaces only: project, phase, stage, backlog
ratio, critical risk count, next task.

**Escalated opening banner — fires only when a critical flag is set:**

When the SessionStart hook detects a critical condition — `/hermes-doctor`
in BROKEN state, a phase exit blocked, an unhandled critical risk, or
Argus drift events accumulating — the banner expands to include the
relevant detail and recommended action:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES · CLARK · Phase 1.5 · Stage 10 MONITOR
  Backlog 36/63 · 4 critical risks open
  Next: #13 external uptime monitor

  ⚠ CRITICAL: last 3 sessions did not close cleanly
    → run /hermes-doctor for diagnosis

  ⚠ Argus has not run in 9 sessions
    → run /hermes-argus (drift detection overdue)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The full situational picture — operator-action items, all flags,
overhead trends, recommended next moves — is available on demand via
`/hermes-status`, not pushed on every session open.

**Handoff banner — fires on Stop and PreCompact:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES · Handoff · 2026-05-22 16:48
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Commits: a7f3d92 (#13), bc1e504 (#37)
  Backlog: REL-002 done, REL-006 done
  Drift:   0 events
  Pending: #39 Fernet key backup off-Railway
  → Phase 2 advance blocked only on #39
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The template is named "Handoff," not "Session closing," because the
same hook fires on both `Stop` (session genuinely ending) and
`PreCompact` (session continuing after context compaction). "Handoff"
is accurate for both: it's the point at which the framework records
what happened and prepares the next stretch of work, whether that's a
new session or a post-compact continuation.

**Cold-start behavior.** The first session after `/hermes-init` (or
after the Session 0 migration) has no prior `session_end` to read from.
The opening banner for cold start is:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES · CLARK · Phase 1 · Stage 1
  New cc-forge project — no prior session history.
  Start with /hermes-status to orient, or /hermes-next.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The hook detects the absence of prior `session_end` events and emits
the cold-start variant rather than an error banner.

### 2.4 The hook ↔ model contract

The hook computes content deterministically and produces side effects
deterministically. The model renders the banner. The honest framing of
the boundary:

**What is guaranteed (deterministic):**

- The hook fires on its registered event. Claude Code guarantees this.
- The hook reads state, computes the banner, and writes side effects
  (`usage.log` event, `status/last-*-banner.md`, cache refresh).
- The computed banner content is injected into the model's context via
  `hookSpecificOutput.additionalContext`.

**What is high-reliability but NOT guaranteed:**

- The model rendering the injected banner as visible output.

**Self-contained payload.** The rendering instruction is included
*inside* the `additionalContext` payload, immediately adjacent to the
banner content, rather than relying on an instruction elsewhere
(CLAUDE.md or HERMES.md). This makes the instruction maximally salient —
it's right next to the content it governs, in the freshest position in
context. The payload looks like:

```json
{
  "hookSpecificOutput": {
    "additionalContext": "[cc-forge] Render the following banner verbatim as the first line(s) of your reply, then proceed normally:\n\n━━━━ HERMES · CLARK · ...\n..."
  }
}
```

This eliminates the CLAUDE.md `@import` dependency that an earlier draft
proposed. CLARK CC correctly noted that the `@import` adds a Layer 3
contract that fails open — no import means no rendering instruction
means silent regression, exactly the failure mode being eliminated. The
self-contained payload has no such dependency: the instruction travels
with the content.

**Why this is still not deterministic, and why that's acceptable.** Even
with a maximally-salient self-contained instruction, the model may
paraphrase, truncate, or skip rendering. This is an irreducible property
of LLM-driven chat — there is no mechanism in Claude Code to force the
model to emit specific tokens. The design accepts this because the
framework's *integrity* does not depend on rendering (it depends on the
side effects, §2.2). Rendering is the user-experience layer; its
failure is detectable (§2.5) but not fatal to the framework's
correctness.

### 2.5 Retrospective verification

Because rendering is not guaranteed, the framework verifies it after
the fact rather than assuming it.

`/hermes-doctor` includes a **banner-rendering sample check**: it reads
recent session transcripts (where available) and compares them against
the banners the hooks recorded in `status/last-*-banner.md` and the
`session_start` / `session_end` events in `usage.log`. If the hook
recorded a banner that does not appear in the corresponding transcript,
that's a rendering miss, surfaced as an advisory:

```
⚠ Banner rendering: 2 of last 10 sessions did not render the
  opening banner (hook fired, model did not display it).
  This is a known soft-failure mode — see DESIGN §2.4.
```

This converts an invisible failure into a visible, quantified one. The
framework cannot prevent rendering misses, but it can measure them and
surface the rate. A rising miss rate is itself a signal worth acting on
(e.g., the banner may be too long, or competing context too heavy).

### 2.6 Hook architecture

Five Claude Code lifecycle events are used or anticipated. Three are
fully specified here; two are forward references.

| Event | Matcher | Purpose | Specified in |
|---|---|---|---|
| `SessionStart` | `startup\|resume\|clear\|compact` | Opening banner + side effects | §2 |
| `Stop` | (no matcher) | Handoff banner + side effects | §2 |
| `PreCompact` | `manual\|auto` | Handoff banner + side effects | §2 |
| `UserPromptSubmit` | (no matcher) | Per-prompt framing + intake detection | §2.8, Session D |
| `PostToolUse` | (selective) | Drift detection (Argus) | Session E |

Declared in `hooks/hooks.json` in the cc-forge plugin:

```json
{
  "hooks": {
    "SessionStart": [{
      "matcher": "startup|resume|clear|compact",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/hermes-session-start.sh"
      }]
    }],
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/hermes-handoff.sh"
      }]
    }],
    "PreCompact": [{
      "matcher": "manual|auto",
      "hooks": [{
        "type": "command",
        "command": "${CLAUDE_PLUGIN_ROOT}/hooks/hermes-handoff.sh"
      }]
    }]
  }
}
```

The same `hermes-handoff.sh` handles `Stop` and `PreCompact` —
semantically the same event (record what happened, prepare the next
stretch).

### 2.7 SessionStart performance: the cache layer

The SessionStart hook reads `state.json`, ten backlog files, RISKS.md,
and tails `usage.log`, then computes flags — every session. CLARK CC's
review correctly flagged that doing all of this in a tight latency
budget every session, with no cache, will routinely exceed any
reasonable budget and trigger timeout fallbacks that mask real
failures.

**The cache.** A `.cc-forge/cache.json` file holds the computed
situational summary (backlog counts by status, open risk counts,
last-session metadata, computed flags). The cache stores the mtime of
every source file it derived from.

**Invalidation.** On SessionStart, the hook compares the mtime of each
source file against the mtimes recorded in the cache. If all match, the
cache is warm — the hook reads the summary directly (sub-50ms). If any
source file is newer, the hook recomputes the affected portion and
refreshes the cache.

**Budget.** With a warm cache, the SessionStart subset completes well
under 500ms. With a cold cache (first session, or after backlog edits),
the hook recomputes with a relaxed budget (up to ~3 seconds) and writes
the fresh cache for next time. The opening banner is allowed to be
slightly slower on the first session after changes; subsequent sessions
are fast.

**Staleness, explicitly.** The mtime comparison is what keeps the cached
summary from going stale: the cache is only trusted while every source
file it derived from is unchanged. A stale cache is never silently
served — any newer source file forces recomputation of the affected
portion. This makes the cache a freshness-checked read, not a
time-to-live guess.

If even the cold-cache computation exceeds its budget, the hook returns
the minimal banner with whatever it computed and logs
`subset_check_timeout` to `usage.log`. The banner notes "full state
pending — run /hermes-status" rather than erroring.

### 2.8 Per-prompt framing (UserPromptSubmit)

The `UserPromptSubmit` hook fires on every user message. cc-forge uses
its `additionalContext` for a **lightweight per-prompt framing** —
roughly 100–200 tokens, not a full persona — that addresses the
in-conversation voice decay problem (named explicitly in §6.9).

The per-prompt framing carries three things:

1. **Phase scope reminder** — the current PDLC phase and a one-line
   reminder of what's in-scope for it (so the model is nudged to defer
   out-of-phase work).
2. **Intake detection** — a lightweight signal to check whether the
   prompt introduces new scope, escalating to `/hermes-intake` if so
   (the `bypass_detected` mechanism; see §3.6 and Session D). This is a
   probabilistic first line; the deterministic backstop that catches
   classifier misses is specified in §3.6 and §5.3.
3. **Closure discipline reminder** — a compact restatement of the
   "one next step, stated not asked" pattern, to counter the
   mid-session decay of Hermes voice.

**This document specifies UserPromptSubmit as the foundational primitive
for per-prompt framing and names the three responsibilities it carries.
The detailed mechanics — exact framing text, the intake-detection
classifier, escalation thresholds — are deferred to Session D, which
owns the UserPromptSubmit hook and the intake protocol.** Naming it here
ensures the voice-decay problem is assigned rather than glossed; the
implementation belongs with intake.

As with all hook output, the per-prompt framing is injected
deterministically but attended to statistically. Its value is in
raising the baseline reliability of in-conversation discipline, not in
guaranteeing it. The framework does not depend on it for integrity.

### 2.9 Failure modes

Hook failure is never silently handled by the model improvising. Three
failure modes are handled explicitly:

**Hook script fails (non-zero exit or runtime error).** Claude Code
surfaces hook errors. The hook's deterministic side effects may be
partial, so the next SessionStart detects the incomplete prior session
(missing `session_end`) and surfaces it. For the immediate session, the
self-contained payload is absent, so no banner is injected; the model
proceeds without one. `/hermes-doctor` reports the hook failure. The
key point: a hook failure degrades the *visible banner*, not the
*framework state*, because state lives in side effects that either
completed or are detectably incomplete.

**Hook produces invalid output.** If the hook returns malformed JSON,
Claude Code surfaces a parse error and injects nothing. Same handling
as above — no banner this session, doctor detects it.

**Hook doesn't fire.** `/hooks` shows what's registered. `/hermes-doctor`
checks `/hooks` output and reports missing cc-forge hooks. This catches
"cc-forge installed but hooks not registered."

The principle: **the framework never silently degrades to
model-improvised behavior. Failures degrade the visible layer and are
detected; they do not corrupt the framework's state.**

### 2.10 What this section does NOT address

- The exact format of `usage.log` entries — §3.
- How `/hermes-update` propagates hook scripts — §4.
- The detailed UserPromptSubmit framing mechanics — Session D.
- Argus session-close mechanics — Session E.
- In-conversation Hermes voice decay as an unsolved problem — named in
  §6.9.

---

## §3 — File contracts

This section specifies the canonical format for every file the cc-forge
framework reads or writes. Every format has a parser contract, a
verbatim example, and explicit failure behavior.

### 3.2 Backlog items

**Location:** `.cc-forge/backlog/<NN>-<domain>.md`, where `NN` is `01`
through `10` and `domain` is one of: `product`, `development`,
`security`, `reliability`, `design`, `integrations`, `compliance`,
`launch`, `growth`, `operations`.

**Item format:** `### [ID]` blocks. Each block is a multi-line section
with one field per line, line-anchored for reliable persona editing.

```markdown
---
domain: 03-security
owner: security-auditor
phase_target_bars:
  1: 30
  2: 80
  3: 95
  4: 100
  5: 100
---

# Domain 03 — Security

## Definition of Done — <project>

This domain is complete when:
- <criterion 1>
- <criterion 2>

## Items

### [SEC-UNI-001] TLS/HTTPS on all production endpoints
- Outcome: All production HTTP endpoints terminate TLS and reject plain HTTP.
- Standard: OWASP ASVS V9.1.1
- Phase: 1
- Status: done
- Owner: sec
- Evidence: railway.toml line 12; tests/integration/test_tls.py

### [SEC-STK-FNT-002] Theory content encrypted before persistence
- Outcome: All theory content written to Postgres is Fernet-encrypted.
- Standard: NIST SP 800-57
- Phase: 1
- Status: in-progress
- Owner: sec
- Evidence: pending — see Taskmaster #41
```

**Field constraints:**

- `[ID]` in heading — `^[A-Z]{2,4}(-[A-Z]{2,4}){0,2}-\d{3}$`.
- `Outcome` — free text, JTBD outcome statement. Required.
- `Standard` — source framework reference (OWASP ASVS, NIST, Google SRE,
  JTBD, WCAG, etc.). Required; `—` only where no standard applies.
- `Phase` — `1`–`5` or `—` (the latter reserved for `not-applicable`).
- `Status` — exactly one of: `not-started`, `in-progress`, `done`,
  `not-applicable`, `operator-action`, `intake-pending`.
- `Owner` — persona identifier (`sec`, `cto`, `qa`, `sre`, `ux`, `po`,
  `legal`).
- `Evidence` — where to verify the claim (file, test, ADR, task ID).
  Required.

**Parser contract:** Split on `^### \[([A-Z][A-Z0-9-]+)\]`; per block,
extract fields via `^- (Outcome|Standard|Phase|Status|Owner|Evidence): (.+)$`.
A block missing a required field is a format violation. The parser
counts violations, logs each as `format_violation`, and returns parsed
items *plus the violation count* (see §3.8 partial-parse safety). Strict
— no fuzzy matching.

**Frontmatter:** Required. `phase_target_bars` is per-project (set at
init) and editable.

**Backwards compatibility:** Items missing `Standard` are grandfathered
with `—` for one transition cycle (the gap #48 fix recently made
`Standard` required), then become violations.

### 3.3 RISKS.md

Layer 3 file (user-maintained); violations are advisories, not strict.

```markdown
# Risks

| ID         | Title                              | Severity | Status | Mitigation                       | Owner | Review     |
|------------|------------------------------------|----------|--------|----------------------------------|-------|------------|
| R-OPS-001  | RUNBOOK.md does not exist          | critical | open   | Draft runbook from incident log  | sre   | 2026-05-28 |
| R-SEC-007  | Fernet key only in Railway secrets | high     | open   | Implement off-Railway backup     | sec   | 2026-06-01 |
```

- `ID` — `^R-[A-Z]{2,4}-\d{3}$`.
- `Severity` — `critical` | `high` | `medium` | `low`.
- `Status` — `open` | `mitigating` | `accepted` | `closed`.
- `Review` — ISO-8601 date.

Table format (not blocks) because users edit this directly and table is
more readable for human review. Personas *suggest* risk additions; they
do not write to RISKS.md (Layer 3 boundary, §4.5). Closed risks stay in
the file but are not shown on the dashboard.

### 3.4 DECISIONS.md

Layer 3 file; violations are advisories.

```markdown
# Decisions

## ADR-018 — Clerk-specific items marked not-applicable
- Date: 2026-05-19
- Status: accepted
- Context: Custom JWT auth chosen in ADR-006. Clerk no longer applies.
- Decision: SEC-STK-CLK-* items marked not-applicable.
- Consequences: Domain 03 reduces by 1 not-applicable line.
```

- Header — `^## (ADR-\d{3,4}) — (.+)$`.
- `Date` — ISO-8601. `Status` — `proposed` | `accepted` | `deprecated`
  | `superseded`. `Context` / `Decision` / `Consequences` — required.
- `superseded` ADRs must include `- Superseded by: ADR-XXX`.

### 3.5 state.json

```json
{
  "schema_version": "1.0",
  "cc_forge_required_version": ">=1.0.0,<2.0.0",
  "project_name": "<string>",
  "current_pdlc_phase": 1,
  "current_sdlc_stage": 10,
  "phase_entered_at": "2026-05-21T18:14:00Z",
  "phase_history": [
    { "phase": 1, "entered": "2026-05-06T...", "exited": "2026-05-20T..." }
  ],
  "operator_action_items": [
    { "id": "#13", "title": "external uptime monitor", "added": "2026-05-21T..." }
  ]
}
```

- `current_pdlc_phase` — integer 1–5. `current_sdlc_stage` — integer
  1–11. Both required.
- `cc_forge_required_version` — semver range the project's state is
  compatible with. `/hermes-update` checks the installed plugin against
  this and warns on a major-version mismatch (see §4.6).
- Names (`MVP`, `Beta`, ..., `MONITOR`) are **not stored**. They derive
  from numeric IDs via canonical maps in Layer 1
  (`personas/_shared/phase-names.json`, `stage-names.json`). This
  eliminates denormalized name/number drift.

Parsed as strict JSON; missing required fields or out-of-range values
are `format_violation`.

**Schema migration:** see §3.9 (covers all formats, not just this one).

### 3.6 usage.log

Newline-delimited JSON, one event per line.

| `type` | Fields | When |
|---|---|---|
| `session_start` | `ts`, `claude_md_tokens` | SessionStart hook |
| `session_end` | `ts`, `duration_min`, `commits`, `personas_invoked` | Handoff hook |
| `command` | `ts`, `name`, `tokens` | `/hermes-*` invocation |
| `persona` | `ts`, `name`, `verdict`, `findings_count` | Persona gate review |
| `gate` | `ts`, `gate_type`, `verdict`, `personas`, `findings_count` | Within-phase gate |
| `phase_transition` | `ts`, `from_phase`, `to_phase`, `panel_verdicts`, `changelog_ref`, `override` | `/hermes-phase-gate` |
| `backlog` | `ts`, `item_id`, `old_status`, `new_status` | Status change |
| `drift` | `ts`, `subtype`, `details` | Argus detection |
| `format_violation` | `ts`, `file`, `line`, `severity`, `expected`, `found` | Parser fail |
| `orphan_task` | `ts`, `task_id`, `finder` | Task without backlog parent |
| `missing_coverage` | `ts`, `finding`, `domain`, `suggested_template_item` | Finding without item |
| `standards_strip_detected` | `ts`, `file`, `item_id` | Standards line missing |
| `intake_step` | `ts`, `intake_id`, `step`, `result` | `/hermes-intake` step |
| `bypass_detected` | `ts`, `prompt_excerpt`, `caught_by`, `confidence` | UserPromptSubmit detection |
| `subset_check_timeout` | `ts`, `elapsed_ms` | SessionStart subset over budget |

**Design principle:** events at different cadences, with different
fields, or treated differently by the dashboard are distinct types.
`gate` (frequent, routine) and `phase_transition` (rare, ceremonial)
are the canonical example of why not to collapse.

**bypass_detected mechanism (sketch; full spec in Session D).** The
UserPromptSubmit hook does not keyword-match (which would be all false
positives on "add"/"build"/"implement"). It makes a cheap classifier
call — a Haiku-class prompt asking "does this user message introduce
work not already represented in the current backlog or in-flight
tasks?" — returning a confidence score. Only above a threshold does it
log `bypass_detected` and inject the intake-escalation framing. The
classifier reads the current backlog summary from the cache (§2.7) so
it can distinguish genuinely-new scope from references to existing
items. Cost is one small model call per prompt; accuracy is far better
than keyword matching.

**Why the classifier is a first line, not the enforcement.** A
confidence-thresholded model call is not a reliable gate for a critical
rule — model self-reported confidence is not a dependable enforcement
signal, so the classifier cannot be the thing that guarantees intake
happens. Consistent with §2.2, the classifier is a probabilistic *first
line* that raises the baseline catch rate, and enforcement lives in a
deterministic, retrospective check. A classifier false negative — new
scope that slips past the per-prompt check — is caught after the fact by
the deterministic drift checks in §5.3 whenever the bypassed work leaves
a structural trace: `orphan_task` (work that produced a task with no
backlog parent), `missing_coverage` (a finding with no backlog item), or
a backlog-state change with no corresponding `intake_step` in the log
(the `intake_reconciliation` check, §5.3). **Residual gap (named, not
solved):** bypassed scope that leaves no structural trace — a pure code
change introducing no task, finding, or backlog edit — is not caught by
these checks. This is the per-prompt classifier's irreducible coverage
limit, recorded here rather than assumed away. Tightening it (e.g.,
commit-message ↔ backlog reconciliation) is deferred to Session D/E.

**Append-only.** Never edited or truncated. Archive at 10MB via
`/hermes-doctor --fix=archive-usage-log` (not automatic): current file
renamed `usage.log.YYYY-MM-DD`, new empty file created, archives never
deleted. Dashboard queries read active + overlapping archives.

### 3.7 intake-log.md

Append-only markdown; each event is a section with YAML frontmatter and
a markdown body. (Full example in Session D scope; contract here.)

- `intake_id` — `^INTAKE-\d{3,4}$`. **Monotonically increasing, never
  reused** — even rejected/withdrawn intakes keep their ID. Next intake
  is always max-existing + 1. `/hermes-doctor` verifies monotonicity.
- `disposition` — `accepted` | `deferred-to-phase-N` | `rejected` |
  `withdrawn`.
- `classification` — `feature` | `bug` | `improvement` | `spike` |
  `other`. The first four are the expected vocabulary; `other` is an
  escape value for an intake that genuinely fits none of them, and when
  used it requires a free-text `classification_detail` stating what it
  actually is. This prevents a persona from forcing an uncategorizable
  intake into a wrong category to satisfy a closed enum — an honest
  `other` is preferred to a fabricated fit, and `other` entries are
  visible for later recategorization. `Status` and `disposition` remain
  closed by contrast: `Status` is a state machine (its values are the
  actual states, not a classification) and `disposition` is procedural,
  so neither has the "doesn't fit" failure mode that motivates an escape
  value.
- `personas_consulted` — array of persona identifiers.

### 3.8 Failure behavior — strict vs advisory

**Layer 2 files (framework-managed) — strict mode.** Violations
indicate framework drift. Parser logs `format_violation`
(`severity: strict`), skips the line, and returns parsed data *plus the
violation count*. A strict violation also carries whether it is
retryable — a persona write that can be re-prompted — or not — an absent
file or a hand-edit, where there is no writer to re-prompt; the
write-path loop below acts on this distinction.

**Layer 3 files (user-maintained) — advisory mode.** Violations may be
in-progress edits or preferences. Parser logs `format_violation`
(`severity: advisory`), skips the line, returns data plus count.
Doctor reports advisories but not as errors.

**Partial-parse safety (both modes).** Every consumer of parsed data
also handles the violation count:

- **Dashboard** — surfaces "N of M items parseable" as a visible
  top-line indicator on any tab driven by parsed data. If N < M, it
  renders the warning *before* any percentages. This is load-bearing,
  not aspirational: the dashboard-zeros incident happened because the
  parser failed silently. The denominator is always visible.
- **`/hermes-next`** — refuses to surface a next item if >5% of items
  in the relevant domain are unparseable; tells the user to run
  `/hermes-doctor` first.
- **`/hermes-doctor`** — surfaces counts in its Layer 2 / Layer 3
  output.

**Write-path validation (persona writes).** The strict/advisory modes
above govern *reads* — what a consumer does when it parses an existing
violation. The write path is the complement: when a persona produces a
structured write (a backlog item, an intake-log entry) that fails its
format contract, the violation is not merely logged and left in place.
The write is validated against the contract at write time, and on
failure the specific violation is fed back to the persona for
self-correction before the write is considered complete — a
validate-and-retry step, not a fire-and-forget append followed by a
later skipped-line log. A `format_violation` originating in a persona
write is *retryable* (re-prompt the writer with the exact failure); a
violation originating from an absent source file or a hand-edit is not
(no writer to re-prompt). Retry has a known limit: it corrects format
and structural errors, but cannot conjure information that was never
present — a write failing because a required input genuinely does not
exist is not fixed by re-prompting. Retrospective read-side validation
(above) remains the backstop for anything the write-path loop does not
catch — for example, a human hand-edit that introduces a violation after
the fact.

This document specifies the *principle and the contract surface*:
structured persona writes are validated at write time and retried with
specific-error feedback on failure. The detailed mechanics — retry
budget, how the feedback is phrased, where the loop sits in the write
protocol — belong with the write protocol itself
(`personas/_shared/backlog-update-protocol.md`) and are specified in
Session D, which owns that path. Naming it here ensures the write path
has a validation contract rather than relying on retrospective detection
alone.

### 3.9 Schema migration — all formats

Schema migration covers every framework-managed format, not just
state.json. CLARK CC correctly noted that usage.log event types,
backlog item format, and other contracts will all evolve.

Each format carries an implicit or explicit version. When a format
changes, a migration script in `${CLAUDE_PLUGIN_ROOT}/migrations/`
transforms old to new. Migrations are forward-only and idempotent.
`/hermes-update` runs pending migrations as part of its sequence (§4.6).

For formats without an explicit version field (backlog items, usage.log
lines), the migration framework detects old-shape content by pattern
and transforms it. Where a format genuinely cannot be safely migrated,
§3 commits to *additive-only* changes to that format (new optional
fields, never renamed or removed required fields) so old content
remains valid.

### 3.10 What this section does NOT address

- Dashboard rendering logic — the prototype is the spec.
- The persona update protocol — `personas/_shared/backlog-update-protocol.md`.
- File locations — §4. Doctor reporting — §5.

---

## §4 — Physical layout

cc-forge ships as a **three-layer system**: a Claude Code plugin
(Layer 1, framework-canonical, read-only), per-project state (Layer 2),
and user-maintained documents (Layer 3, framework reads only).

Appendix C provides a side-by-side current vs post-migration table.

### 4.2 The three layers

```
LAYER 1 — PLUGIN (framework-canonical, read-only)
  hooks · commands · personas · standards · session-lifecycle
  HERMES.md · catalogue · scripts · migrations · token-weights.json
  phase-names.json · stage-names.json
  → plugin space, /plugin update, user cannot edit

LAYER 2 — PROJECT STATE (framework-writable, project-specific)
  state.json · usage.log · backlog/*.md · intake-log.md · cache.json
  overrides/ (advanced escape hatch)
  → .cc-forge/, framework writes during operation, user edits cautiously

LAYER 3 — USER-MAINTAINED (user-owned, framework reads only)
  CLAUDE.md · PRD.md · RISKS.md · DECISIONS.md · CHANGELOG.md
  + the user's application code
  → project root, user owns, framework never writes
```

**Key principle:** ownership is unambiguous at every layer. The question
"who's allowed to edit this file?" — which cc-forge has silently dodged
— now has a clear answer per layer. If you want to change a Layer 1 file
(a persona, say), you instead express the customization in CLAUDE.md
(Layer 3) or, rarely, in `.cc-forge/overrides/` (Layer 2). Personas are
read-only canonical content; `/hermes-update` refreshing them never
clobbers user work, because user work never lives in them.

### 4.3 Layer 1 — Plugin structure

```
cc-forge/                          ← GitHub repo root
├── .claude-plugin/plugin.json
├── commands/                      ← status.md → /hermes-status, etc.
├── hooks/
│   ├── hooks.json
│   ├── hermes-session-start.sh
│   ├── hermes-handoff.sh
│   └── hermes-prompt-submit.sh    ← UserPromptSubmit (Session D)
├── personas/
│   ├── argus.md · security-auditor.md · cto.md · ...
│   └── _shared/
│       ├── backlog-update-protocol.md
│       ├── phase-names.json
│       └── stage-names.json
├── standards/ · session-lifecycle/ · catalogue/ · scripts/
├── migrations/
├── token-weights.json
├── HERMES.md
└── README.md
```

**plugin.json:**

```json
{
  "name": "cc-forge",
  "version": "1.0.0",
  "description": "SDLC framework for Claude Code: Hermes the Conductor, Argus the Monitor, expert personas, structured backlog, dashboard.",
  "homepage": "https://github.com/A-Director/cc-forge",
  "author": "A-Director",
  "license": "MIT"
}
```

Scripts reference plugin files via `${CLAUDE_PLUGIN_ROOT}` — eliminates
hardcoded paths.

**Command naming (technical note):** Claude Code plugins namespace their
commands. The framework configures commands to expose as
`/hermes-<filename>`; the file is `commands/status.md`, the user types
`/hermes-status`. The prefix is kept (despite namespacing making it
optional) for discoverability — typing `/hermes-` autocompletes the
whole command set — and continuity with user muscle memory.

**Tool scoping (technical note):** commands declare `allowed-tools` in
frontmatter to scope what each can do, rather than every command
carrying the full tool surface. Read-only commands (`/hermes-status`,
`/hermes-doctor` without `--fix`) declare a read-only tool set; commands
that mutate state declare only the tools they need. This is the same
least-privilege conservatism as the doctor's `--fix` discipline (§5.5):
a command cannot perform a destructive action it never declared access
to, which bounds the blast radius of a misbehaving command.

**token-weights.json:** Layer 1 at
`${CLAUDE_PLUGIN_ROOT}/token-weights.json`. Per-project overrides
(rare) at `.cc-forge/overrides/token-weights.json`. Consumers check
override first, fall back to canonical.

**Forked execution for verbose and parallel operations.** Several
cc-forge operations produce large volumes of intermediate output that
has no value in the main conversation: `/hermes-doctor` scans every
contract file, `/hermes-dashboard` reads the full backlog and usage log,
and a full persona gate review spawns multiple specialists that each
examine the codebase in depth. Run inline, each floods the session's
context window with scan output, file contents, and per-persona
reasoning — and gate reviews are already the framework's highest
token-consuming activity.

These operations declare `context: fork` so they execute in an isolated
sub-agent: the operation does its verbose work in a separate context
window and returns only its result (a doctor verdict, a
dashboard-generated confirmation, a persona's structured findings) to
the main conversation. Parallel gate reviews are the prime case —
multiple persona reviewers fork simultaneously, each returning only its
verdict, so the main session sees the panel's conclusions without the
panel's deliberation.

*Precondition: forkable operations are self-contained from state.* A
forked sub-agent does not inherit the conversation history — it receives
only its own instructions. cc-forge operations can be forked precisely
because they derive their inputs from Layer 2 state (state.json,
backlog, usage.log), not from the conversation. This is §2.2's principle
paying off: an operation whose integrity lives in state files can run
anywhere, including a fresh context that has never seen the session. An
operation that needed conversation history could not be forked — and
none of cc-forge's verbose operations do.

*Fork is an optimization, not a correctness mechanism.* Whether the
harness honors `context: fork` on a given version is not guaranteed; a
fork that silently runs inline is a known failure mode. cc-forge
therefore treats forking as a token-efficiency optimization only: every
forkable operation must produce a correct result whether it forks or
runs inline. The framework's correctness never depends on the fork
having happened — consistent with the rest of this document, the
determinism lives in the side effects and the state, and fork affects
only where the verbose work is performed.

### 4.4 Layer 2 — Project state

```
user-project/
├── .cc-forge/
│   ├── state.json · usage.log · usage.log.YYYY-MM-DD (archives)
│   ├── intake-log.md · cache.json
│   ├── backlog/01-product.md ... 10-operations.md
│   └── overrides/
│       ├── token-weights.json   (optional)
│       └── personas/            (optional)
└── status/
    ├── dashboard.html           (gitignored)
    ├── last-open-banner.md      (gitignored — regeneratable)
    ├── last-handoff.md          (gitignored — regeneratable)
    └── argus-last-run.md        (committed — durable finding record)
```

`.cc-forge/` is framework state (config-like); `status/` is operational
artifacts (user-facing).

**status/ gitignore (explicit).** The `.gitignore` template includes:

```
status/dashboard.html
status/last-open-banner.md
status/last-handoff.md
status/*.png
```

Generated/regeneratable artifacts are ignored. Durable finding records
(`argus-last-run.md` and other markdown reports) are committed, so
drift findings survive in history and are visible in code review. This
resolves the ambiguity CLARK CC flagged — without an explicit rule,
these files get accidentally committed or accidentally deleted.

### 4.5 Layer 3 — User-maintained

```
user-project/
├── CLAUDE.md · PRD.md · RISKS.md · DECISIONS.md · CHANGELOG.md
└── (application code)
```

Framework reads these; never writes. A persona that identifies a new
risk *surfaces* it for the user to add to RISKS.md — no auto-edit.

**No framework-mandated content in Layer 3.** An earlier draft required
CLAUDE.md to `@import` HERMES.md to carry the rendering instruction.
That's been dropped (§2.4): the rendering instruction now travels inside
the hook's self-contained payload, so no Layer 3 file carries any
framework contract. Layer 3 is purely user-owned. `/hermes-init` may
*offer* to add cc-forge context to CLAUDE.md, but nothing the framework
needs depends on Layer 3 content.

The distinction matters: what's dropped is *framework-mandated*
`@import` — a framework file the user's CLAUDE.md was required to import,
which fails open (no import → no instruction → silent regression, the
exact failure mode being eliminated). User-authored `@import` for the
user's own CLAUDE.md modularity is untouched and unobjectionable — if a
user wants to split their CLAUDE.md into imported standards files, that's
their business and the framework neither requires nor prevents it. The
framework simply never *depends* on a Layer 3 import existing.

### 4.6 The `/hermes-update` contract

```
1. Update plugin (Layer 1)       → /plugin update cc-forge
2. Version check                 → compare installed plugin vs
                                    state.json cc_forge_required_version;
                                    warn/block on major-version mismatch
3. Run pending migrations        → ${CLAUDE_PLUGIN_ROOT}/migrations/*
                                    (all formats, §3.9)
4. Verify Layer 1 ↔ Layer 2      → expected files present; run doctor
                                    subset; exit non-zero with explicit
                                    list if anything missing
5. Report                        → version, migrations applied,
                                    verification result
```

Because Layer 1 is plugin-managed, `/hermes-update` does **not** copy
framework files into the project — plugin content is referenced via
`${CLAUDE_PLUGIN_ROOT}`. This eliminates copy-list drift (gap #52).

**Version pinning.** `state.json.cc_forge_required_version` declares the
plugin version range the project's state is compatible with. If a plugin
auto-update crosses a major version, `/hermes-update` (and the
SessionStart hook) warn that project state may need migration before
proceeding. This prevents silent desync between an auto-updated plugin
and an un-migrated project.

**Migration window.** Pre-plugin → plugin migration is supported through
cc-forge v2.x; removed in v3.0. After removal, `/hermes-update` detects
pre-plugin shape and directs the user to a documented manual path.

### 4.7 The Session 0 migration (CLARK first)

The pre-plugin → plugin migration runs first against CLARK. Because
CLARK is real and the migration has partial-failure modes, the
migration is not treated as binary success. It provides:

- **Dry-run mode** (`--dry-run`) — prints the full diff of what would
  change (files moved, removed, plugin installed, CLAUDE.md touched)
  without applying anything. The operator reviews before committing.
- **Pre-migration backup** — `.cc-forge/` is copied to
  `.cc-forge.backup-YYYY-MM-DD/` before any change.
- **Explicit rollback** (`--rollback`) — restores from the backup and
  uninstalls the plugin, returning the project to its pre-migration
  state.
- **Step-wise application** with a log — each step (remove legacy
  commands, remove hardcoded hook, install plugin, verify) is logged so
  a partial failure is diagnosable rather than mysterious.

The migration:

- Detects the old install (unprefixed commands in `~/.claude/commands/`,
  hardcoded hook in `~/.claude/settings.json`).
- Removes legacy unprefixed command files.
- Removes the hardcoded hook (replaced by plugin-managed hooks).
- Installs the cc-forge plugin.
- Confirms Layer 1 content is reachable (so per-project copies of
  personas/standards are no longer needed).
- Reports what changed and what (if anything) needs operator attention.

### 4.8 What this section does NOT address

- hooks.json schema — §2.6. File format contracts — §3. Doctor logic —
  §5. Marketplace distribution — §7.

---

## §5 — Self-check: `/hermes-doctor`

`/hermes-doctor` runs concrete checks against the contracts in §2–§4
and reports drift. It exists because frameworks that document behavior
without checking it accumulate silent failures.

Appendix B maps each gap to the doctor check that catches it.

### 5.2 What the doctor does

Three check categories (one per layer), a drift summary, and an overall
verdict (`HEALTHY` / `DEGRADED` / `BROKEN`):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES-DOCTOR · CLARK · 2026-05-22
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Layer 1 — Plugin
    ✓ plugin registered (v1.0.0) · 16 commands · 4 hooks
    ✓ 13 personas · HERMES.md · session-lifecycle/ · token-weights.json
  Layer 2 — Project state
    ✓ state.json valid (schema 1.0, version pin satisfied)
    ✓ backlog: 79/79 items parse · 0 standards_strip (30d)
    ✓ session_end in 12/12 last sessions
    ⚠ banner rendering: 2/10 sessions missed (soft-failure, §2.4)
    ⚠ Argus last ran 9 days ago
  Layer 3 — User-maintained
    ✓ CLAUDE.md · PRD.md · RISKS.md (6 open, 0 advisories) · DECISIONS.md
  Drift (30d): 0 strict · 0 advisory · 0 orphan · 0 bypass
  Overall: HEALTHY with 2 advisories
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### 5.3 The check catalogue

**Layer 1:** plugin registration; command availability; hook
registration (via `/hooks`); hook executability; persona presence;
HERMES.md present and non-empty; lifecycle docs present;
token-weights.json at canonical path.

**Layer 2:** state.json validity + consistency + version-pin satisfied;
backlog domain files present; backlog item format (per-file violation
count); frontmatter validity; session_end cadence (wall-clock, §5.4
below); usage.log parseability; intake-log validity + monotonic IDs;
override consistency; **banner-rendering sample check** (§2.5 — compares
recorded banners against recent transcripts, reports miss rate). This is
the one doctor check that is not a clean deterministic predicate: it is
a fuzzy transcript match, so its own measurement carries error (a
model-paraphrased banner can read as a miss when a variant was in fact
rendered). The check reports its rate as approximate for this reason;
every other doctor check is a definite pass/fail.

**Intake reconciliation** — flags backlog-state changes (`backlog`
events) in the window that have no corresponding `intake_step` and no
pre-existing item, i.e. new scope that entered the backlog without
passing through intake. This is the deterministic backstop for the
probabilistic intake classifier (§3.6): a classifier false negative
that nonetheless touched the backlog is caught here after the fact.

**Layer 3:** presence of CLAUDE.md / PRD.md / RISKS.md / DECISIONS.md;
RISKS.md + DECISIONS.md format (advisory); CHANGELOG.md present (warn if
missing). No content enforcement — Layer 3 is user-owned, and with the
`@import` dropped (§4.5) there is no mandated Layer 3 content at all.

**Drift summary:** counts of `format_violation` (strict/advisory split),
`orphan_task`, `missing_coverage`, `standards_strip_detected`,
`bypass_detected`, and `intake_reconciliation` (backlog scope without
intake) over a window (default 30 days).

**Stratified where stratification is actionable.** A single aggregate
number can hide a clustered failure: "2/10 sessions missed the banner"
reads as a mild, diffuse soft-failure, but if all 2 misses are
post-compact resumes it is a specific, fixable signal (the banner is too
heavy for the compact-resume path). Aggregation also hides whether
"150/200 items parse" is one broken domain file or systemic format drift
across all ten. Two drift dimensions are therefore reported broken out,
not only as a total:

- **Banner-miss rate by session-start type** (`startup` / `resume` /
  `clear` / `compact`). The session-start matcher is already recorded,
  so this is a reporting breakdown, not new collection.
- **Format violations by file / domain.** §3.8 already counts violations
  per file; the doctor surfaces that breakdown rather than collapsing it
  to one number.

Stratification is applied only to these two — the dimensions where the
segment is actionable and the data already exists. Low-volume,
single-segment drift (`orphan_task`, `bypass_detected`,
`intake_reconciliation`) is reported as a plain count; breaking it out
by an arbitrary segment would be noise, not signal.

### 5.4 When the doctor runs

**On-demand — `/hermes-doctor`.** Full report; allowed several seconds.

**At session start (subset, cached).** The SessionStart hook runs a
small subset — hook registration (cached), last session_end presence,
recent format_violation count, recent bypass_detected count, and a quick
banner-miss check. Reads from the cache (§2.7) so it stays within
budget. On cold cache, runs with relaxed budget and notes incompleteness
rather than erroring.

**session_end cadence is wall-clock, not prompt-count.** CLARK CC
correctly noted that "once per 5 prompts" is the wrong shape — a long
debugging session has 50 prompts and one close; a quick check has 3. The
check is: a session with more than 90 minutes of activity that produced
no `session_end` is flagged. Cadence measures elapsed active time, not
message count.

**Scheduled (future).** When Claude Code scheduled agents stabilize,
doctor can run on a schedule. Not in v1.

### 5.5 What the doctor can fix

Reports by default; fixes only with explicit `--fix=<category>` (no
`--fix-all`):

| Category | Fixes | Safe because |
|---|---|---|
| `legacy-commands` | Removes unprefixed legacy command files | mechanical |
| `state-migration` | Runs pending schema migrations | forward-only, idempotent |
| `missing-layer2` | Re-copies an accidentally-deleted Layer 2 file from canonical template | template exists in Layer 1 |
| `archive-usage-log` | Archives usage.log over 10MB | well-defined, no data loss |

Will NOT auto-fix: backlog format violations (need human judgment),
missing Standards (need persona consult), hook registration (needs
`/plugin update`), anything in Layer 3.

**Precedence (least invasive first):** `legacy-commands` →
`archive-usage-log` → `missing-layer2` → `state-migration`. Every fix
logged; every skipped-but-fixable category reported with its fix
command.

### 5.6 Implementation notes

Implemented as `scripts/hermes-doctor.py` in the plugin. Uses the *same
parsers* as the dashboard and other consumers — if doctor's parser
disagrees with the dashboard's, the framework has already lost the
discipline doctor enforces. One canonical parser per format.

Modes: human (default) and `--json` (CI). Exit 0 HEALTHY / 1 DEGRADED /
2 BROKEN.

The `--json` output conforms to a declared, versioned schema shipped
with the plugin, not ad-hoc JSON. A CI job consuming the doctor's output
(posting findings as PR comments, gating a pipeline) parses against that
schema and fails loudly if the shape drifts — the same loud-failure
discipline the doctor enforces on every other contract, applied to the
doctor's own output. The schema version travels in the output so a
consumer can detect a doctor upgrade that changed the shape. Declaring
the schema is in scope here; the schema file itself is an implementation
artifact.

### 5.7 What this section does NOT address

Persona-behavior checks (Argus, Session E); on-demand performance beyond
the subset budget; a web view of doctor results; complex auto-remediation
(see §5.5 conservatism).

---

## §6 — Out of scope (this version)

### 6.1 Deferred to subsequent sessions

- **Requirements intake** — Session D specifies `/hermes-intake` and the
  UserPromptSubmit framing mechanics (§2.8). This doc specifies the
  primitive and the `intake-log.md` contract only.
- **Argus session-close + CC scanning** — Session E. This doc specifies
  the `usage.log` drift schema and that Argus reads but never writes
  backlog state.
- **Command standardization** — Session F. This doc specifies path
  conventions only.
- **Plugin conversion mechanics** — Session 0, against this doc.

### 6.2 Persona behaviors

Persona prompts are canonical Layer 1 content, refined in their own
changes, governed by the shared protocol, HERMES.md, and Standards
references. This doc does not specify persona reasoning, additions, or
removals.

### 6.3 The PDLC phase model

The five-phase model is in PHASES.md (Session A). This doc treats phases
as a fact. Refinements happen against PHASES.md.

### 6.4 Dashboard visual design

The prototype is the spec. This doc specifies what the dashboard reads
(§3) and where it writes (§4.4), not how it looks.

### 6.5 User documentation and onboarding

README, CHEATSHEET, INSTALL, tutorials — Session F's documentation pass.

### 6.6 Marketplace and distribution

Publishing destination is a launch decision. The plugin layout makes any
path viable.

### 6.7 Multi-project, team, and CI usage

Single-user, single-project assumed. The architecture enables team /
multi-project / CI futures (see §7) but doesn't specify the workflows.

### 6.8 Deliberate silence

No opinion on language stack (framework infra is Python; user projects
are any language). No opinion on git workflow (reads `git log`; requires
no branching model).

No opinion on session branching. cc-forge tracks a single linear session
history per project (`usage.log` is append-only, state is a single
current snapshot); it has no concept of forking a session for parallel
exploration. Branching, where wanted, is the user's to manage outside
the framework. The framework's state model assumes one line of work per
project.

### 6.9 What this design does NOT solve (acknowledged)

This subsection names problems the design does not fully solve, so they
are tracked honestly rather than glossed.

**In-conversation Hermes voice decay.** The bookend banners (§2.3) are
now backed by deterministic side effects and verified retrospectively.
But the *middle* of a session — Hermes's "one next step, stated not
asked" discipline after each significant action — remains model-driven
and decays over long sessions, exactly as it did in CLARK before this
document. The per-prompt UserPromptSubmit framing (§2.8) raises the
baseline reliability of this discipline by re-injecting a compact
reminder on every prompt, but injection is not attendance: the model
may still drift. This is the most visible regression CLARK experienced,
and the design *reduces* it without *eliminating* it. There is no known
mechanism in Claude Code to make in-conversation voice deterministic.
Tracking: the banner-rendering sample check (§2.5) measures bookend
misses; a future doctor check could sample mid-session discipline
similarly. For now, this is a named, accepted limitation.

**Banner rendering is not deterministic.** As developed in §2.4, the
hook deterministically computes and injects the banner, but the model
renders it only with high reliability, not certainty. The framework's
integrity does not depend on rendering (it depends on side effects,
§2.2), and rendering misses are measured (§2.5), but the visible banner
can be absent on any given session. This is acceptable because the
framework remains correct without it — but it means the user-facing
experience is best-effort, and the document does not claim otherwise.

**Mid-session state changes between bookends.** The opening banner is a
snapshot at session start; the handoff is a snapshot at close. Long
sessions can drift substantially between the two with no structured
re-surfacing except whatever the per-prompt framing carries. A user
deep in a 3-hour session sees the opening banner once and the handoff
once. `/hermes-status` on demand fills this gap, but the framework does
not proactively re-banner mid-session (deliberately — that would be
noise). Named so the limitation is explicit, not assumed-away.

---

## §7 — Design roadmap

A *design* roadmap (what architectural concerns get added), not a
schedule.

### 7.1 Two directions

**Vertical** — deepening enforcement of what's specified (new contracts,
new doctor checks). Mostly mechanical. **Horizontal** — new agents or
concerns (new personas, multi-project, teams). Rare; needs design care.

### 7.2 Near-term horizontal growth

**Code Reviewer persona.** Reviews diffs before commit — line-level
concerns, idiomatic patterns, code smell. Distinct from QA (test
coverage/quality), CTO (architecture/dependencies), and itself (the diff
itself). Triggered by a PreToolUse hook on commit, or `/hermes-code-review`.
Needs its own spec.

**Product Owner KPI-elicitation.** The PO persona expands to elicit KPIs
and success metrics at phase boundaries ("for Phase 2 Beta to succeed,
what metric do you want to move?"). Behavior change, not structural.

### 7.3 Medium-term

Plugin marketplace presence; scheduled Argus (when Claude Code scheduled
agents stabilize); team mode (shared state, authority resolution — its
own design doc); CI integration (gates as blocking CI participants via
`--json`).

**MCP resource exposure.** cc-forge currently has no MCP surface — it is
hooks, commands, and personas. A natural future direction is exposing
project state as read-only MCP *resources*: the backlog, open risks, the
decisions log, and the current phase/stage as content catalogs an agent
can read without exploratory tool calls. This is a consuming-side and
resource-exposure direction, distinct from authoring full MCP servers
for tooling; the latter is not currently planned. Exposing state as
resources fits the framework's existing posture — state already lives in
structured Layer 2 files, so surfacing it as resources is a thin
adapter, not new state.

**Plan mode for high-bar transitions.** cc-forge's phase gates and
persona reviews are its planning discipline today. A future direction is
having the framework invoke Claude Code's plan mode for the largest,
most architectural transitions — a phase advance that implies multi-file
restructuring, say — so the design is explored and reviewed before any
change is committed, complementing (not replacing) the gate review.
Whether plan mode adds value over the existing gate discipline, or only
duplicates it for most transitions, is the open question this item
would settle; it is on the roadmap to evaluate, not yet committed.

### 7.4 Long-term

Cross-project portfolio view; domain-specific variants
(`cc-forge-saas`, etc.); memory/learning from session patterns (per
Anthropic's Dreaming preview).

### 7.5 The deliberate non-roadmap

Not building: visual UI beyond the HTML dashboard; AI agents beyond
Claude (framework is Claude Code-native; outputs are universal markdown);
general workflow automation beyond hooks (cc-forge stops at "develop
with discipline"; deployment platforms are downstream).

### 7.6 How this roadmap evolves

Not a contract. Surface the need in a real project, design it with this
document's discipline, ship it.

---

## Appendix A — Document conventions

**Specification style:** concrete examples over abstraction; every
contract has a verbatim example; every hook has a real config snippet.

**Update mechanism:** the document is the spec. Implementation flaws are
fixed in the document first, then the code. Document↔code drift is itself
a regression worth surfacing.

---

## Appendix B — Gap → check mapping

| Gap | Doctor check | Layer | Section |
|---|---|---|---|
| #47 orphan gate findings | `orphan_task` drift count | 2 | §5.3 |
| #48 standards stripped | `standards_strip_detected` count + backlog format check (missing Standard) | 2 | §5.3 |
| #49 intake bypass | `bypass_detected` count (probabilistic first line) + `intake_reconciliation` deterministic backstop + UserPromptSubmit registration | 1,2 | §3.6,§5.3 |
| #50 update strips prefix | command availability + legacy-command check | 1 | §5.3,§5.5 |
| #51 global/project dup | plugin namespacing makes dup impossible; legacy globals surfaced as fixable | 1 | §5.5 |
| #52 update misses non-md | Layer 1 file-presence checks | 1 | §5.3 |
| Hermes closure regression | session_end cadence check (wall-clock) | 2 | §5.3,§5.4 |
| Format fork (zeros) | backlog format check + partial-parse "N/M parseable" indicator | 2 | §3.8,§5.3 |
| **Rendering not deterministic** (new, from review) | banner-rendering sample check | 2 | §2.5,§5.3 |

Every gap maps to a concrete check. Implementing this design makes the
entire class of silent failures *observable* — surfaced at session start
or by the doctor, rather than waiting for a human to notice. New failure
modes will produce new gaps, but those gaps become detectable; the
rendering-determinism row is itself an example — discovered in review,
now caught by a check.

---

## Appendix C — Compatibility table

**Current (pre-migration):**

```
~/.claude/commands/   ← mixed prefixed/unprefixed (gap #50), drift (gap #51)
~/.claude/settings.json ← hardcoded project path (CLARK)
<project>/.cc-forge/  ← per-project copies of personas/standards (gap #48)
                        no session-lifecycle/, no HERMES.md (never shipped)
<project>/scripts/    ← sometimes (gap #52)
<project>/CLAUDE.md   ← no framework contract
<project>/dashboard.html ← at project root
```

**Post-migration:**

```
${CLAUDE_PLUGIN_ROOT}/  ← Layer 1: single source of truth, plugin-managed
  commands/ hooks/ personas/ standards/ session-lifecycle/
  catalogue/ scripts/ migrations/ token-weights.json HERMES.md
<project>/.cc-forge/    ← Layer 2: state only (state.json, usage.log,
                          backlog/, intake-log.md, cache.json, overrides/)
<project>/status/       ← Layer 2: operational artifacts
                          (dashboard.html + banners gitignored;
                           argus-last-run.md committed)
<project>/CLAUDE.md     ← Layer 3: purely user-owned, no framework contract
~/.claude/settings.json ← plugin-managed, no hardcoded paths, no copied commands
```

**Key differences:** per-project copies of personas/standards/catalogue/
session-lifecycle/HERMES.md go away (live in plugin once); commands
namespaced via plugin; `status/` houses operational artifacts;
`dashboard.html` off project root; no framework-mandated Layer 3 content;
`~/.claude/settings.json` fully plugin-managed.

---

## Appendix D — Hermes responsibility table

| Responsibility | Mechanism | Failure handling |
|---|---|---|
| Opening banner — *content & side effects* | SessionStart hook, deterministic | Side effects complete or detectably incomplete |
| Opening banner — *visible rendering* | Model renders self-contained payload | High-reliability; misses measured by §2.5 |
| Handoff — *content & side effects* | Stop/PreCompact hook, deterministic | session_end written or absence detected |
| Handoff — *visible rendering* | Model renders self-contained payload | High-reliability; misses measured |
| Rendering instruction delivery | Inside hook payload (self-contained) | No external dependency to fail |
| "Where we left off" computation | Hook reads usage.log + state.json (cached) | Hook failure → no banner, doctor detects |
| Flag detection | Hook computes vs thresholds (cached) | Hook failure → no banner, doctor detects |
| Per-prompt framing | UserPromptSubmit hook (Session D) | Injection deterministic; attendance statistical |
| In-conversation voice | Model-driven, HERMES.md-guided | **Not solved** — §6.9; decays, per-prompt framing reduces |
| Phase advancement | `/hermes-phase-gate` + state.json | Doctor checks state consistency |
| Drift surfacing | `/hermes-doctor` (on-demand + subset) | Doctor failures surface in own output |
| Intake enforcement | Classifier (first line) + `intake_reconciliation` doctor check (backstop) | Classifier miss caught retrospectively if it touched the backlog; residual gap named §3.6 |
| Structured write integrity | Write-path validate-and-retry (§3.8) + retrospective parser | Malformed write re-prompted; hand-edits caught on read |
| Verbose/parallel ops | `context: fork` (§4.3) | Optimization only; correct whether forked or inline |

**The principle:** the framework's *integrity* (what it knows, what it
records, what it surfaces as drift) is deterministic — it lives in side
effects. The framework's *visible expression* (banners, voice) is
high-reliability but not guaranteed, and its misses are measured rather
than assumed away. The honest boundary between these two is the central
correction this document makes to earlier drafts.

---

