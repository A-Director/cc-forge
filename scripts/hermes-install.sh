#!/bin/bash

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HERMES INSTALL
#  Sets up the complete Hermes SDLC tool stack
#  Run from your project root
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HERMES INSTALL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Check prerequisites ──────────────────────────
echo "▸ Checking prerequisites..."

if ! command -v claude &> /dev/null; then
  echo "  ✗ Claude Code not found. Install it first:"
  echo "    https://claude.ai/code"
  exit 1
fi

if ! command -v node &> /dev/null; then
  echo "  ✗ Node.js not found. Install Node 20+ first:"
  echo "    https://nodejs.org"
  exit 1
fi

if ! command -v git &> /dev/null; then
  echo "  ✗ Git not found."
  exit 1
fi

echo "  ✓ Claude Code found"
echo "  ✓ Node.js found ($(node --version))"
echo "  ✓ Git found"
echo ""

# ── Install Claude Code plugins ──────────────────
echo "▸ Installing Claude Code plugins..."

echo "  → claude-mem (session memory)"
/plugin marketplace add thedotmack/claude-mem && /plugin install claude-mem 2>/dev/null || \
  echo "  ⚠ claude-mem: install manually with /plugin install claude-mem"

echo "  → superpowers (agentic workflow)"
/plugin install superpowers@claude-plugins-official 2>/dev/null || \
  echo "  ⚠ superpowers: install manually with /plugin install superpowers@claude-plugins-official"

echo ""

# ── Install MCP servers ──────────────────────────
echo "▸ Installing MCP servers..."

echo "  → taskmaster (task management)"
claude mcp add task-master-ai --scope user \
  --env TASK_MASTER_TOOLS="standard" \
  -- npx -y task-master-ai@latest 2>/dev/null || \
  echo "  ⚠ taskmaster: install manually — see README"

echo "  → context7 (live library docs)"
claude mcp add context7 --scope user \
  -- npx -y @upstash/context7-mcp 2>/dev/null || \
  echo "  ⚠ context7: install manually — see README"

echo ""

# ── Install criticalthink command ────────────────
echo "▸ Installing criticalthink command..."

mkdir -p ~/.claude/commands
curl -sS -o ~/.claude/commands/criticalthink.md \
  https://raw.githubusercontent.com/abagames/slash-criticalthink/main/.claude/commands/criticalthink.md && \
  echo "  ✓ criticalthink installed (~/.claude/commands/criticalthink.md)" || \
  echo "  ⚠ criticalthink: download failed, install manually"

echo ""

# ── Install Hermes commands ──────────────────────
echo "▸ Installing Hermes commands..."

HERMES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mkdir -p ~/.claude/commands

# Copy hermes commands to global claude commands
for cmd_file in "$HERMES_DIR"/hermes/commands/*.md; do
  cmd_name=$(basename "$cmd_file")
  cp "$cmd_file" ~/.claude/commands/"hermes-$cmd_name"
  echo "  ✓ /hermes-${cmd_name%.md}"
done

echo ""

# ── Summary ──────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HERMES INSTALL COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Plugins:  superpowers · claude-mem"
echo "  MCPs:     task-master-ai · context7"
echo "  Commands: /criticalthink · /hermes-*"
echo ""
echo "  Next steps:"
echo "  ┌─ New project:      cd your-project && /hermes-init"
echo "  └─ Existing project: cd your-project && /hermes-adopt"
echo ""
echo "  Start Claude Code:  claude"
echo ""
