#!/bin/bash
# hermes-handoff.sh — fires on Stop and PreCompact (§2.6).
#
# Records the session_end event in usage.log and emits the closing banner
# on stdout for the model to render. Same hook handles both events because
# they're semantically identical from cc-forge's perspective: the session
# is ending; produce a structured handoff.
#
# The §1 "Hermes closure regression" — zero session_end events ever logged —
# closes here. This script's existence + registration is what makes the
# end-of-session bookend deterministic instead of advisory.

set -u

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
CC_FORGE_DIR="${PROJECT_ROOT}/.cc-forge"
USAGE_LOG="${CC_FORGE_DIR}/usage.log"
STATE_JSON="${CC_FORGE_DIR}/state.json"

# This script is registered on both Stop and PreCompact (§2.6). Read the
# event name from the hook-input JSON so the Argus auto-fire (below) can be
# selective: PreCompact is mid-session (work continues), not a true close.
HOOK_EVENT=""
if [ ! -t 0 ]; then
  HOOK_INPUT=$(cat 2>/dev/null || true)
  if [ -n "$HOOK_INPUT" ]; then
    HOOK_EVENT=$(printf '%s' "$HOOK_INPUT" | python3 -c 'import json,sys
try:
    print(json.loads(sys.stdin.read()).get("hook_event_name","") or "")
except Exception:
    print("")' 2>/dev/null || true)
  fi
fi

# Not a cc-forge project — exit silently.
if [ ! -f "$STATE_JSON" ]; then
  exit 0
fi

iso_ts=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

# --- counts since last session_start ---
commits_since=0
session_start_ts=""
if [ -f "$USAGE_LOG" ]; then
  session_start_ts=$(grep "\"type\":\"session_start\"" "$USAGE_LOG" 2>/dev/null \
    | tail -1 \
    | grep -o "\"ts\":\"[^\"]*\"" \
    | sed 's/"ts":"//;s/"$//')
fi
if [ -n "$session_start_ts" ] && [ -d "${PROJECT_ROOT}/.git" ]; then
  commits_since=$(git -C "$PROJECT_ROOT" log --since="$session_start_ts" --oneline 2>/dev/null | wc -l | tr -d ' ')
fi

# --- write session_end event ---
echo "{\"ts\":\"${iso_ts}\",\"type\":\"session_end\",\"data\":{\"commits\":${commits_since}}}" >> "$USAGE_LOG" 2>/dev/null || true

# --- Argus auto-fire at session-close (§5.4) --------------------------------
# A watcher you must summon isn't watching: Argus runs automatically at the
# end of a session so framework drift is caught without anyone remembering to
# run it. It fires on Stop — a genuine session close — and NOT on PreCompact
# (mid-session compaction; work continues) or PostToolUse (fires constantly);
# neither of those is a session boundary.
#
# Deliberately NOT gated on commits. Framework drift hides precisely in
# uncommitted edits — a hand-edited backlog item that introduces a format
# violation, an intake that never reconciled — and a session can end with that
# drift uncommitted. "Produced commits" is a leaky proxy for "did work" that
# would skip exactly the silent drift Argus exists to catch. Argus is cheap
# and deterministic (a warm cache rehydrates; a stale source recomputes and
# catches the drift), so over-firing costs almost nothing while under-firing
# misses drift — the worse error for a watcher. Cadence is handled separately
# by the SessionStart staleness banner.
#
# Argus writes its own durable record; we surface only a one-line verdict
# here and never let it fail the hook.
ARGUS_LINE=""
if [ "$HOOK_EVENT" = "Stop" ]; then
  SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
  ARGUS_PY="${SCRIPT_DIR}/../scripts/hermes-argus.py"
  if [ -f "$ARGUS_PY" ] && command -v python3 >/dev/null 2>&1; then
    argus_json=$(timeout 15s python3 "$ARGUS_PY" --project-root "$PROJECT_ROOT" \
                   --json --trigger session-close 2>/dev/null || true)
    if [ -n "$argus_json" ]; then
      ARGUS_LINE=$(printf '%s' "$argus_json" | python3 -c 'import json,sys
try:
    s = json.loads(sys.stdin.read()).get("summary", {})
    v = s.get("verdict", "?"); f = s.get("failures", 0); a = s.get("advisories", 0)
    extra = ""
    if v == "DEGRADED":
        extra = " ({0} advisor{1})".format(a, "y" if a == 1 else "ies")
    elif v in ("BROKEN", "CANNOT_LOCATE"):
        extra = " ({0} failure{1})".format(f, "" if f == 1 else "s")
    tail = "" if v == "HEALTHY" else " - see status/argus-last-run.md"
    print("Argus: {0}{1} - record updated{2}".format(v, extra, tail))
except Exception:
    print("Argus: ran - record updated")' 2>/dev/null || true)
    fi
    [ -z "$ARGUS_LINE" ] && ARGUS_LINE="Argus: ran · see status/argus-last-run.md"
  fi
fi

# --- emit banner ---
ts=$(date -u +"%Y-%m-%d %H:%M")
project_name=$(grep -o '"project_name":[[:space:]]*"[^"]*"' "$STATE_JSON" 2>/dev/null \
  | sed 's/.*"\([^"]*\)"$/\1/' || echo "$(basename "$PROJECT_ROOT")")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HERMES · Session closing · ${ts}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$commits_since" -gt 0 ]; then
  echo "  Commits this session: ${commits_since}"
  if [ -d "${PROJECT_ROOT}/.git" ]; then
    git -C "$PROJECT_ROOT" log --since="$session_start_ts" --oneline 2>/dev/null | head -5 | sed 's/^/    /'
  fi
else
  echo "  No commits this session."
fi
echo "  Session: ${project_name}"
if [ -n "$ARGUS_LINE" ]; then
  echo "  ${ARGUS_LINE}"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
