#!/bin/bash
# hermes-session-start.sh — fires on Claude Code SessionStart
#
# Computes the opening banner deterministically from project state and emits
# it on stdout. Claude Code injects stdout into the model's session context;
# CLAUDE.md / HERMES.md instructs the model to render any HERMES banner verbatim.
#
# This is the §2 hook ↔ model contract: hooks compute, model renders. The
# banner content is structured Markdown produced here, not a model improvisation.
#
# v1.0.0 (Session 0): cold-only — reads state on every fire. The cache layer
# (§2.7) lands in the Doctor session; until then, this hook respects the
# spec's "cold-cache relaxed budget" fallback and returns a minimal banner if
# computation runs long.

set -u

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CC_FORGE_DIR="${PROJECT_ROOT}/.cc-forge"
USAGE_LOG="${CC_FORGE_DIR}/usage.log"
STATE_JSON="${CC_FORGE_DIR}/state.json"

# SessionStart matcher source — Claude Code passes this via stdin JSON.
# Capture it for E-1 banner-miss stratification.
SOURCE=""
if [ -t 0 ]; then
  : # interactive — no JSON on stdin
else
  HOOK_INPUT=$(cat 2>/dev/null || true)
  if [ -n "$HOOK_INPUT" ]; then
    SOURCE=$(printf '%s' "$HOOK_INPUT" | python3 -c 'import json,sys
try:
    d=json.loads(sys.stdin.read())
    print(d.get("source","") or "")
except Exception:
    print("")' 2>/dev/null || true)
  fi
fi
if [ -z "$SOURCE" ]; then
  SOURCE="unknown"
fi

# Hard budget — if we exceed this, emit the minimal banner and log a timeout
# event instead of waiting and producing a stale signal.
BUDGET_SECONDS=3

# If the project isn't a cc-forge project, do nothing. This makes the hook
# safe to install plugin-wide.
if [ ! -f "$STATE_JSON" ]; then
  exit 0
fi

# --- Argus staleness (§5.4) ---
# A watcher you must summon isn't watching. Read Argus's durable record
# (status/argus-last-run.md, per DESIGN §4.4) and count how many session_start
# events have been logged since it last ran. If that's >= threshold, the
# opening banner says so. Computed here (not in the bounded subshell below)
# and injected as a pre-formatted line; bounded by its own timeout so a slow
# read never delays the session.
ARGUS_STALE=$(timeout 2s python3 - "$USAGE_LOG" "${PROJECT_ROOT}/status/argus-last-run.md" <<'PY' 2>/dev/null
import json, os, re, sys
usage, record = sys.argv[1], sys.argv[2]
THRESHOLD = 3
last_ts = None
if os.path.isfile(record):
    try:
        txt = open(record, encoding="utf-8", errors="replace").read()
        m = re.search(r'^- Ran at:\s*(\S+)', txt, re.M)
        if m:
            last_ts = m.group(1)
    except OSError:
        pass
n = 0
if os.path.isfile(usage):
    try:
        for line in open(usage, encoding="utf-8", errors="replace"):
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            if not isinstance(e, dict) or e.get("type") != "session_start":
                continue
            ts = e.get("ts")
            if last_ts is None or (isinstance(ts, str) and ts > last_ts):
                n += 1
    except OSError:
        pass
if n >= THRESHOLD:
    where = "has never run" if last_ts is None else "has not run in {0} sessions".format(n)
    print("  ⚠ Argus {0} - framework drift unchecked. Run /hermes-argus.".format(where))
PY
)

# Bounded compute — wrap the body in a timeout so we never block the session.
banner=$(timeout "${BUDGET_SECONDS}s" bash -c '
  set -u
  STATE_JSON="'"$STATE_JSON"'"
  CC_FORGE_DIR="'"$CC_FORGE_DIR"'"
  PROJECT_ROOT="'"$PROJECT_ROOT"'"
  USAGE_LOG="'"$USAGE_LOG"'"
  SOURCE="'"$SOURCE"'"
  ARGUS_STALE="'"$ARGUS_STALE"'"

  # --- project basics from state.json ---
  project_name=$(grep -o "\"project_name\":[[:space:]]*\"[^\"]*\"" "$STATE_JSON" 2>/dev/null \
    | sed "s/.*\"\\([^\"]*\\)\"$/\\1/" || echo "(unnamed)")
  phase=$(grep -o "\"current_pdlc_phase\":[[:space:]]*[0-9]*" "$STATE_JSON" 2>/dev/null \
    | grep -o "[0-9]*$" || echo "?")
  phase_name=$(grep -o "\"current_pdlc_phase_name\":[[:space:]]*\"[^\"]*\"" "$STATE_JSON" 2>/dev/null \
    | sed "s/.*\"\\([^\"]*\\)\"$/\\1/" || echo "")
  stage=$(grep -o "\"current_sdlc_stage\":[[:space:]]*[0-9]*" "$STATE_JSON" 2>/dev/null \
    | grep -o "[0-9]*$" || echo "?")
  stage_name=$(grep -o "\"current_sdlc_stage_name\":[[:space:]]*\"[^\"]*\"" "$STATE_JSON" 2>/dev/null \
    | sed "s/.*\"\\([^\"]*\\)\"$/\\1/" || echo "")

  # --- backlog counts (approximate, cold-cache; full counts come with cache layer) ---
  done_count=0
  total_count=0
  if [ -d "${CC_FORGE_DIR}/backlog" ]; then
    done_count=$(grep -h "^- Status: done" "${CC_FORGE_DIR}/backlog"/*.md 2>/dev/null | wc -l | tr -d " ")
    total_count=$(grep -h "^- Status:" "${CC_FORGE_DIR}/backlog"/*.md 2>/dev/null | wc -l | tr -d " ")
  fi
  pct=0
  if [ "$total_count" -gt 0 ]; then
    pct=$(( done_count * 100 / total_count ))
  fi

  # --- risks (from project root RISKS.md if present) ---
  open_risks=0
  crit_risks=0
  if [ -f "${PROJECT_ROOT}/RISKS.md" ]; then
    open_risks=$(grep -c "| open " "${PROJECT_ROOT}/RISKS.md" 2>/dev/null || echo 0)
    crit_risks=$(grep -c "| critical | open " "${PROJECT_ROOT}/RISKS.md" 2>/dev/null || echo 0)
  fi

  # --- last session_end from usage.log ---
  last_session_close=""
  if [ -f "$USAGE_LOG" ]; then
    last_session_close=$(grep "\"type\":\"session_end\"" "$USAGE_LOG" 2>/dev/null \
      | tail -1 \
      | grep -o "\"ts\":\"[^\"]*\"" \
      | sed "s/\"ts\":\"//;s/\"$//")
  fi

  # --- render banner ---
  ts=$(date -u +"%Y-%m-%d %H:%M")
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  HERMES · ${project_name} · ${ts}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Project state:"
  if [ "$phase" != "?" ]; then
    if [ -n "$phase_name" ]; then
      echo "    PDLC phase:    ${phase} (${phase_name})"
    else
      echo "    PDLC phase:    ${phase}"
    fi
  fi
  if [ "$stage" != "?" ]; then
    if [ -n "$stage_name" ]; then
      echo "    SDLC stage:    ${stage} ${stage_name}"
    else
      echo "    SDLC stage:    ${stage}"
    fi
  fi
  echo "    Backlog:       ${done_count} / ${total_count} done (${pct}%)"
  if [ "$total_count" -eq 0 ]; then
    echo "                   · backlog empty or uninitialised — run /hermes-backlog-init"
  fi
  if [ "$open_risks" -gt 0 ]; then
    echo "    Risks:         ${open_risks} open · ${crit_risks} critical"
  fi
  if [ -n "$last_session_close" ]; then
    echo "  Where we left off:"
    echo "    Last session closed at ${last_session_close}."
  fi
  if [ -n "$ARGUS_STALE" ]; then
    echo "$ARGUS_STALE"
  fi

  # --- log the session_start event with source matcher (E-1) ---
  iso_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "{\"ts\":\"${iso_ts}\",\"type\":\"session_start\",\"data\":{\"source\":\"${SOURCE}\",\"minimal\":false}}" >> "$USAGE_LOG" 2>/dev/null || true

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
') 2>/dev/null

# If timeout fired (exit 124) or compute errored, emit minimal banner per §2.7.
if [ $? -ne 0 ] || [ -z "$banner" ]; then
  iso_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  # Timeout/error path — record the matcher source so E-1 banner-miss
  # stratification can pinpoint which session-start type tends to fail.
  echo "{\"ts\":\"${iso_ts}\",\"type\":\"subset_check_timeout\",\"data\":{\"source\":\"${SOURCE}\",\"minimal\":true}}" >> "$USAGE_LOG" 2>/dev/null || true
  ts=$(date -u +"%Y-%m-%d %H:%M")
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  HERMES · $(basename "$PROJECT_ROOT") · ${ts}"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Full state pending — run /hermes-status."
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  exit 0
fi

echo "$banner"
exit 0
