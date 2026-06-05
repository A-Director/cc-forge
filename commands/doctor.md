---
name: hermes-doctor
description: >
  Framework self-check. Verifies Layer 1 (plugin) and Layer 2 (project
  state) integrity per spec §5. Stratified drift report (E-1), C-1
  intake reconciliation, versioned --json output (E-2), banner-rendering
  approximate caveat (E-3), freshness-checked Layer-2 cache (§2.7).
  Read-only by default; --fix applies a conservative set of safe
  auto-fixes (§5.5).
allowed-tools: Read, Bash
context: fork
---

# Hermes Doctor

Runs `scripts/hermes-doctor.py` from the plugin and surfaces the result.

## What it checks

**Layer 1 (plugin):** expected files present and reachable.

**Layer 2 (project state):**
- `state.json` present and parseable
- 10 backlog domain files present
- `usage.log` present
- Catalogue items conform to spec §3.2 list-form (with §3.2 line-644
  grandfathering for missing `Standard` only — bucketed separately
  from other required-field gaps)
- C-1 intake reconciliation: backlog events with no matching
  `intake_step` flagged
- Banner-rendering approximate rate (the one fuzzy check — labeled
  "approximate" because we measure SessionStart hook success, not
  model render verification)

**Drift summary (stratified per E-1):**
- Format violations broken out by file AND domain (not aggregate)
- Banner-miss rate by session-start source (startup/resume/clear/compact)
- Low-volume drift (orphan_task, missing_coverage, bypass_detected,
  standards_strip_detected) reported as aggregate counts only — brief
  explicitly excludes from arbitrary stratification

**Cache (§2.7):** a `.cc-forge/cache.json` holds the computed Layer-2
output, keyed by source-file mtimes. Warm cache → fast path. Any source
newer than its recorded mtime → recompute (a stale cache is never
silently served). C-2: the mtime comparison is the freshness check;
this is a freshness-checked read, not a TTL guess.

## Verdict shape

| Verdict | Exit | Meaning |
|---|---|---|
| `HEALTHY` | 0 | All checks pass, no advisories |
| `DEGRADED` | 1 | Advisories present, no failures |
| `BROKEN` | 2 | Root resolved AND at least one check failed |
| `CANNOT_LOCATE` | 3 | Plugin root could not be located — structurally distinct from BROKEN |

CI consumers must key on all four. Treating only exit 2 as failure
mis-handles `CANNOT_LOCATE`.

## Plugin root resolution cascade

The doctor resolves Layer 1 without depending on environment
inheritance — required because `CLAUDE_PLUGIN_ROOT` doesn't survive
into a forked subshell:

1. `CLAUDE_PLUGIN_ROOT` if set AND points at `.claude-plugin/plugin.json`
2. Walk up from `__file__` to find an ancestor containing
   `.claude-plugin/plugin.json`
3. `CANNOT_LOCATE` — explicit "I couldn't find Layer 1", never silently
   reported as "Layer 1 is broken"

## Invocation

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hermes-doctor.py" \
  --project-root "${PWD}" "$@"
```

Useful flags:
- `--json` — versioned machine-readable output (E-2). `$schema` URL
  embedded in the payload; schema artifact ships at
  `scripts/hermes-doctor-output-schema.json`.
- `--no-cache` — bypass the Layer-2 cache; always recompute. Useful
  when debugging the cache itself.

## Notes

- Forkable per §4.3 — verbose scan happens in a fresh sub-agent context.
  Fork is an optimization, not a correctness mechanism: the doctor
  produces the same result whether forked or run inline.
- Self-discovering Layer 1 — does not require `CLAUDE_PLUGIN_ROOT` to
  be set. Per §4.3 rewrite: forkable operations are self-contained
  from state and environment.
- Conservative `--fix` (when implemented in a later session): every
  auto-fix is logged. Every category the doctor *could* fix but didn't
  is reported with the explicit suggestion `/hermes-doctor --fix=<category>`.
