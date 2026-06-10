#!/bin/bash
# hermes-init.sh — (deprecated) thin redirect to the plugin onboarding path.
#
# Pre-Session-0, this script scaffolded a project by copying slash commands
# into .claude/commands/, writing .claude/hooks/start.sh + stop.sh, and copying
# personas/standards locally. All of that is now owned by the Claude Code
# plugin system (commands + hooks) and by hermes-bootstrap.sh (project state).
#
# It also copied from ${HERMES_DIR}/hermes/commands/ — a path that no longer
# exists (it's commands/ now) — so the old flow was both obsolete and broken.
#
# Post-plugin, project onboarding is: bootstrap the project, then run the
# /hermes-init COMMAND (the interview) inside Claude Code. This script no
# longer scaffolds anything; it just directs the user to the right path.

set -u

HERMES_DIR="${HERMES_DIR:-$HOME/cc-forge}"

cat <<EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  cc-forge onboarding (post-plugin model)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  This script is deprecated. Command and hook installation is owned by the
  Claude Code plugin; project scaffolding is owned by hermes-bootstrap.sh.

  1. Install the plugin (once, inside Claude Code):

       /plugin marketplace add ${HERMES_DIR} && /plugin install cc-forge@cc-forge

  2. Bootstrap this project (in the project root):

       bash ${HERMES_DIR}/scripts/hermes-bootstrap.sh

  3. Onboard, inside Claude Code:

       /hermes-init     # new project (interview + setup)
       /hermes-adopt    # existing codebase (gap report)

  4. Verify:

       /hermes-argus

  See README.md / INSTALL.md in ${HERMES_DIR} for the full flow.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

exit 0
