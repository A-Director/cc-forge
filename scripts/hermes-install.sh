#!/bin/bash
# hermes-install.sh — (deprecated) thin redirect to the plugin install path.
#
# Pre-Session-0, this script copied slash commands into ~/.claude/commands/.
# That was gap #51: install wrote to the global directory, /hermes-update
# wrote to the project-local directory, projects accumulated duplicates.
#
# Post-Session-0, command installation is owned by the Claude Code plugin
# system. This script no longer copies anything; it just directs the user
# to the right path.

set -u

HERMES_DIR="${HERMES_DIR:-$HOME/cc-forge}"

cat <<EOF
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  cc-forge install (post-plugin model)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  cc-forge now installs as a Claude Code plugin. This script no longer
  copies slash commands into ~/.claude/commands/ — the plugin system
  handles that.

  To install cc-forge as a plugin, open Claude Code and run:

    /plugin marketplace add ${HERMES_DIR} && /plugin install cc-forge@cc-forge

  To bootstrap a project for cc-forge use, run in the project root:

    bash ${HERMES_DIR}/scripts/hermes-bootstrap.sh

  To verify the install:

    /hermes-doctor

  See README.md in ${HERMES_DIR} for the full install + bootstrap flow.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EOF

exit 0
