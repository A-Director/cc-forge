#!/bin/bash

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HERMES SESSION START HOOK
#  .claude/hooks/start.sh
#
#  Fires automatically when Claude Code opens.
#  Tells Hermes to orient the session — no manual
#  /hermes-status needed.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

# Guard: only run if this is a cc-forge project
if [ ! -f ".cc-forge/state.json" ]; then
  exit 0
fi

# Guard: Bun not required
command -v bun &>/dev/null || true

# Tell Claude Code to run the session start protocol
# This injects the /hermes-status output at session open
cat << 'PROMPT'
Run the Hermes session start protocol from .cc-forge/personas/
or ~/.claude/commands/hermes-status.md:

1. Read .cc-forge/state.json, .taskmaster/tasks/tasks.json,
   .cc-forge/backlog/master.md, CLAUDE.md, RISKS.md
2. Print the HERMES STATUS summary (stage, tasks, backlog %, flags)
3. Close with: Next: [single clearest next action]

Keep it under 150 words. The developer is here to build.
PROMPT
