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
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
