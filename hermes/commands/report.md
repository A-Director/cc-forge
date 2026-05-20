---
name: hermes-report
description: >
  Reads .cc-forge/usage.log and produces a structured project usage report.
  Shows SDLC progress, persona gate history, backlog trajectory, drift events,
  token discipline, and cc-forge framework observations. Designed to be
  pasted into a review session for analysis and improvement.
  Run with /hermes-report anytime.
model: claude-sonnet-4-6
effort: high
tools: Read, Bash
---

# Hermes Report

<role>
You are reading the cc-forge usage log and producing a human-readable
report suitable for a project review session. Your job is to surface
patterns, not just list events. What worked well? What drifted? Where
did the framework help? Where did it get in the way?

This report is read by the developer and their reviewer to improve both
the project and cc-forge itself.
</role>

<constraints>
- Derive everything from actual log entries — never invent or estimate
- Surface patterns across sessions, not just the latest session
- Flag anything that looks like framework friction — gates skipped,
  commands not used, drift detected and not corrected
- Keep the summary section to under 200 words — the detail is in sections
- Be honest about gaps: if a persona was never invoked, say so
</constraints>

---

## Process

```bash
# Read the full log
cat .cc-forge/usage.log

# Count sessions
grep '"type":"session_start"' .cc-forge/usage.log | wc -l

# Get date range
grep '"ts"' .cc-forge/usage.log | head -1
grep '"ts"' .cc-forge/usage.log | tail -1

# Backlog trajectory
grep '"type":"session_end"' .cc-forge/usage.log | \
  python3 -c "import sys,json; [print(json.loads(l)['data'].get('backlog_overall_pct_end','?')) for l in sys.stdin]"
```

Parse the full log and produce the report below.

---

<output_format>

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  CC-FORGE USAGE REPORT  ·  [project]
  [date range]  ·  Generated: [today]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUMMARY
  [2-3 honest sentences: where is the project, how is cc-forge
  being used, what's the headline finding for the review?]

PROJECT PROGRESS
  ─────────────────────────────────────────────
  Current stage:    [N] [NAME]
  Sessions logged:  [N] across [N] days
  Total tasks done: [N]
  Backlog overall:  [N]%

  Backlog trajectory:
  [Sparkline of % over time — e.g. 0% → 12% → 28% → 47%]

  Domain breakdown:
  01 Product      [N]%    02 Development  [N]%
  03 Security     [N]%    04 Reliability  [N]%
  05 Design       [N]%    06 Integrations [N]%
  07 Compliance   [N]%    08 Launch       [N]%

  Launch ready: [Yes / No — [N] domains incomplete]

PERSONA GATE HISTORY
  ─────────────────────────────────────────────
  [Persona]         [N] times  Last: [date]  Outcomes: [P/C/B counts]
  CTO               [N]        [date]        [N]P [N]C [N]B
  Security Auditor  [N]        [date]        [N]P [N]C [N]B
  QA Engineer       [N]        [date]        [N]P [N]C [N]B
  SRE Engineer      [N]        [date]        [N]P [N]C [N]B
  Product Owner     [N]        [date]        [N]P [N]C [N]B
  Argus             [N]        [date]        [COMPLIANT/DRIFTING]

  Never invoked: [list any personas not yet run]

DRIFT EVENTS
  ─────────────────────────────────────────────
  Total:     [N] drift events detected
  Corrected: [N]  Outstanding: [N]

  [If any outstanding drift:]
  ⚠ [Category] — [description] — [since date]

TOKEN DISCIPLINE
  ─────────────────────────────────────────────
  CLAUDE.md tokens:     [current] (target: <600)
  /compact usage:       [N] times across [N] sessions
  Sessions without compact: [N]
  Model distribution:   Opus [N]%  Sonnet [N]%  Haiku [N]%

COMMAND USAGE
  ─────────────────────────────────────────────
  /hermes-status      [N] uses
  /hermes-next        [N] uses
  /hermes-gate review [N] uses
  /hermes-argus       [N] uses
  /hermes-deploy      [N] uses
  /hermes-clean       [N] uses
  /hermes-quality     [N] uses
  /hermes-backlog     [N] uses
  /criticalthink      [N] uses

  Never used: [list commands with 0 uses]

CC-FORGE FRAMEWORK OBSERVATIONS
  ─────────────────────────────────────────────
  [This is the most important section for the review]

  Working well:
  - [Pattern from log data showing something working]
  - [Another pattern]

  Friction detected:
  - [Pattern from log data showing friction — e.g. gate skipped 3 times
    before being run, suggest making it automatic]
  - [Another friction pattern]

  Gaps (things that happened but cc-forge had no agent for):
  - [Event type with no corresponding log entry — suggests missing coverage]

  Suggested improvements:
  - [Specific, actionable improvement derived from log data]
  - [Another improvement]

RISKS AND DECISIONS
  ─────────────────────────────────────────────
  RISKS.md entries:     [N] total  [N] overdue
  DECISIONS.md entries: [N] total
  Overrides recorded:   [N]
  Silent overrides:     [N] (overrides without a decision record — flagged)

NEXT REVIEW FOCUS
  ─────────────────────────────────────────────
  [What to focus on in the next review session, based on current state]
  1. [Priority]
  2. [Priority]
  3. [Priority]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</output_format>

---

## How to use this report in a review session

1. Run `/hermes-report` in Claude Code
2. Copy the full output
3. Paste it into the Claude.ai chat with: "Here's my cc-forge usage report — let's review it"
4. We go through each section together:
   - Project progress: is the backlog trajectory healthy?
   - Persona gates: are the right personas being invoked at the right time?
   - Drift events: what slipped and why?
   - Framework observations: what should change in cc-forge?
5. Any cc-forge improvements identified get filed as Issues on github.com/A-Director/cc-forge
6. Any project improvements get added to Taskmaster

The report is the agenda for the review. The review produces improvements to both the project and the framework.
