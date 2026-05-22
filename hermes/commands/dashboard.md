---
name: hermes-dashboard
description: >
  Generates dashboard.html in the project root — a single self-contained
  HTML view of backlog completion, risks, decisions, and Hermes
  framework usage. Markdown stays source of truth; the dashboard is a
  read-only regeneratable view. Run after phase transitions, mid-project
  sanity checks, or before major reviews.
---

# Hermes Dashboard

`/hermes-dashboard` invokes `scripts/hermes-dashboard.py`, which reads
the project's standards-grounded markdown sources and emits a single
self-contained HTML file at `./dashboard.html` (project root).

The dashboard is **read-only** — it never modifies project files. The
generated `dashboard.html` is gitignored (cc-forge `.gitignore` template
covers it) since it's project-specific output.

## What this command does

1. Runs `python3 scripts/hermes-dashboard.py` from the project root.
2. The script reads:
   - `.cc-forge/state.json` — current PDLC phase + current SDLC stage
   - `.cc-forge/backlog/master.md` — per-domain bars + phase targets
   - `.cc-forge/backlog/0*.md` — all backlog items with Status, Phase,
     Owner, Standard
   - `PHASES.md` — current phase definition + exit criteria
   - `RISKS.md` — risk register with severity, owner, review dates
   - `DECISIONS.md` — ADR list with status and rationale
   - `.cc-forge/usage.log` — session counts, command usage, gate
     history, drift events (`orphan_task`, `missing_coverage`,
     `standards_strip_detected`, `phase_transition`)
   - `~/.claude/projects/<hash>/conversation-*.jsonl` — Claude Code raw
     token usage. Degrades gracefully if not found.
3. Loads `hermes/token-weights.json` to estimate Hermes overhead.
4. Writes `dashboard.html` (single file, no external dependencies — all
   CSS, JS, data inlined).
5. Logs the command run to `.cc-forge/usage.log` with
   `type=command` and `data.command="/hermes-dashboard"`.

## Output banner

After the script completes, surface:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES  ·  Dashboard generated
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Wrote: dashboard.html

  Phase:    [N] [Phase Name]   (exit progress: [N]/[M] criteria met)
  Backlog:  [N]%               ([N] applicable items)
  Risks:    [N] active         ([H] high, [M] medium, [L] low)
  Drift:    orphan_task=[N]    missing_coverage=[N]    standards_strip=[N]
  Hermes:   ~[N]% overhead     (estimated — v2 will measure directly)

  Open dashboard.html in your browser.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## When to regenerate

- **After every PDLC phase transition.** The phase indicator and target
  bars rebase to the new phase.
- **Mid-project sanity check.** Once a sprint or once a week — quick
  read on what's drifting.
- **Before major reviews.** Hands a single artefact to stakeholders.
- **After resolving drift events.** Confirms the orphan_task / missing_coverage
  counts went down.

The dashboard does not auto-regenerate — it's a snapshot command. Re-run
whenever you want a fresh view.

## Degradation rules

Each section degrades gracefully if its source is missing:

| Source missing | Behaviour |
|---|---|
| `.cc-forge/state.json` | Header shows "stage unknown" / "phase unknown"; KPIs still render from backlog |
| Backlog files | "Backlog unavailable — run /hermes-backlog-init" empty state |
| `PHASES.md` | Phase pill shows "phase unknown"; exit-progress section hidden |
| `RISKS.md` | Risks tab shows "no risk register found" empty state |
| `DECISIONS.md` | Decisions tab shows "no ADRs found" empty state |
| `.cc-forge/usage.log` | Usage tab shows "no session history yet" empty state |
| CC conversation jsonl | CC token panel shows "raw token data unavailable on this machine" footnote |

## Notes on methodology

Every estimated number on the dashboard carries a footnote citing source.
The Hermes overhead card explicitly notes: *"Estimated from .cc-forge/
usage.log · per-command weights × invocation counts · v2 will measure
directly via hook."* Plausible range for a normally-disciplined project
is 5–25%. Values outside that range usually mean a calibration mismatch
or unusual project shape — re-tune `hermes/token-weights.json`.

## Related

- `scripts/hermes-dashboard.py` — the generator
- `hermes/token-weights.json` — overhead calibration
- `docs-templates/dashboard-prototype.html` — the design reference
- `hermes/log.md` — schema for the usage events the dashboard reads
