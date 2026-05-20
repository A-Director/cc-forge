#!/bin/bash

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HERMES SESSION END HOOK
#  .claude/hooks/stop.sh
#
#  Fires automatically when Claude Code closes
#  or /compact is run. Hermes summarises the session
#  and primes the next one — no manual /compact needed.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Guard: only run if this is a cc-forge project
if [ ! -f ".cc-forge/state.json" ]; then
  exit 0
fi

# Guard: Bun not required — suppress claude-mem warning
command -v bun &>/dev/null || true

# Log session end to usage.log
SESSION_ID="${SESSION_ID:-unknown}"
STAGE=$(python3 -c "import json; d=json.load(open('.cc-forge/state.json')); print(d.get('current_stage',0))" 2>/dev/null || echo 0)
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "{\"ts\":\"$TS\",\"session_id\":\"$SESSION_ID\",\"type\":\"session_end\",\"stage\":$STAGE,\"data\":{\"notes\":\"\"}}" \
  >> .cc-forge/usage.log 2>/dev/null || true
