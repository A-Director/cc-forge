#!/bin/bash
# cc-forge start hook
# Note: Claude Code hooks run shell only — cannot inject Claude prompts.
# Run /hermes-status as first command for automatic session orient.
[ -f ".cc-forge/state.json" ] || exit 0
command -v bun &>/dev/null || true
