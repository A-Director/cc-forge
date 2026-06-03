---
name: hermes-doctor
description: >
  Framework self-check. Verifies Layer 1 (plugin) and Layer 2 (project
  state) integrity per spec §5. Read-only by default; --fix applies a
  conservative set of safe auto-fixes (§5.5).
allowed-tools: Read, Bash
context: fork
---

# Hermes Doctor

Runs `scripts/hermes-doctor.py` from the plugin and surfaces the result.

## What it does (v1.0.0 skeleton)

Per spec §5.2, the doctor runs a sequence of checks against the three
architectural layers and reports any drift. The v1.0.0 skeleton ships
Layer 1 and Layer 2 file-existence checks only — the full §5.3 check
catalogue (format-violation stratification, cache freshness, banner
rendering caveat, intake reconciliation) lands in the Doctor session.

## Invocation

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hermes-doctor.py" \
  --project-root "${PWD}" "$@"
```

## Output modes

- Default (human): a structured banner per §5.2.
- `--json`: a versioned machine-mode payload per §5.6, conforming to
  schema declared in the JSON itself (`schema_version` field).

## Exit codes (per §5.6)

- `0` HEALTHY
- `1` DEGRADED (advisories present, no failures)
- `2` BROKEN (one or more failures)

## When to run

- On-demand whenever something feels off.
- Optionally on session start (subset run by `hooks/hermes-session-start.sh`
  in a future revision).
- Pre-commit / CI (the `--json` mode is CI-friendly).

## Notes

- This is a forked operation per §4.3 — the doctor's verbose scan doesn't
  flood the main session context. Fork is an optimization; doctor must
  produce correct results whether forked or run inline.
- Doctor does not modify state by default. `--fix` is conservative and
  scoped to specific safe categories per §5.5; full destructive recovery
  is operator-driven, not doctor-driven.
