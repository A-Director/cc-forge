#!/bin/bash

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HERMES INSTALL  ·  cc-forge
#  Run: bash ~/cc-forge/scripts/hermes-install.sh
#
#  Installs via shell (this script):
#  - MCP servers: task-master-ai, context7
#  - Commands: criticalthink + all hermes-* + persona-*
#
#  Requires manual install inside Claude Code:
#  - Plugins: claude-mem, superpowers
#  (plugins are Claude Code slash commands, not shell commands)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

set -e

HERMES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HERMES INSTALL  ·  cc-forge"
echo "  Source: $HERMES_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Prerequisites ────────────────────────────────
echo "▸ Checking prerequisites..."

if ! command -v claude &> /dev/null; then
  echo "  ✗ Claude Code not found: https://claude.ai/code"
  exit 1
fi

if ! command -v node &> /dev/null; then
  echo "  ✗ Node.js not found: https://nodejs.org"
  exit 1
fi

NODE_MAJOR=$(node --version | cut -d. -f1 | tr -d 'v')
if [ "$NODE_MAJOR" -lt 20 ]; then
  echo "  ✗ Node.js 20+ required. Found: $(node --version)"
  exit 1
fi

if ! command -v git &> /dev/null; then
  echo "  ✗ Git not found"
  exit 1
fi

echo "  ✓ Claude Code · Node.js $(node --version) · Git"
echo ""

# ── npm cache check ──────────────────────────────
echo "▸ Checking npm cache..."
if ! npx --yes task-master-ai@latest --version &>/dev/null 2>&1; then
  echo "  ⚠ npm cache issue — clearing..."
  npm cache clean --force 2>/dev/null || true
fi
echo "  ✓ npm cache OK"
echo ""

# ── MCP servers ──────────────────────────────────
echo "▸ Installing MCP servers..."

if claude mcp add task-master-ai --scope user \
  --env TASK_MASTER_TOOLS="standard" \
  -- npx -y task-master-ai@latest 2>/dev/null; then
  echo "  ✓ task-master-ai"
else
  echo "  ⚠ task-master-ai failed — run manually:"
  echo "    claude mcp add task-master-ai --scope user -- npx -y task-master-ai@latest"
fi

if claude mcp add context7 --scope user \
  -- npx -y @upstash/context7-mcp 2>/dev/null; then
  echo "  ✓ context7"
else
  echo "  ⚠ context7 failed — run manually:"
  echo "    claude mcp add context7 --scope user -- npx -y @upstash/context7-mcp"
fi
echo ""

# ── Commands ─────────────────────────────────────
echo "▸ Installing commands to ~/.claude/commands/..."
mkdir -p ~/.claude/commands

# 1. hermes/commands/ — operational commands
echo "  → operational commands (status, next, gate-review, deploy, report)"
for f in "$HERMES_DIR"/hermes/commands/*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .md)
  cp "$f" ~/.claude/commands/hermes-${name}.md
  echo "  ✓ /hermes-${name}"
done

# 2. hermes/ root — init, adopt, backlog-init, log, update
echo ""
echo "  → workflow commands (init, adopt, backlog-init, log, update)"
for f in init adopt backlog-init log update; do
  src="$HERMES_DIR/hermes/${f}.md"
  if [ -f "$src" ]; then
    cp "$src" ~/.claude/commands/hermes-${f}.md
    echo "  ✓ /hermes-${f}"
  fi
done

# 3. personas — invokable directly as slash commands
echo ""
echo "  → persona commands"
for f in "$HERMES_DIR"/personas/*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .md)
  cp "$f" ~/.claude/commands/persona-${name}.md
  echo "  ✓ /persona-${name}"
done

# 4. criticalthink
echo ""
echo "  → criticalthink"
if curl -sS -o ~/.claude/commands/criticalthink.md \
  https://raw.githubusercontent.com/abagames/slash-criticalthink/main/.claude/commands/criticalthink.md 2>/dev/null; then
  echo "  ✓ /criticalthink"
else
  echo "  ⚠ criticalthink download failed — install manually"
  echo "    https://github.com/abagames/slash-criticalthink"
fi
echo ""

# ── Summary ──────────────────────────────────────
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  INSTALL COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  ✓ MCPs:     task-master-ai · context7"
echo "  ✓ Commands: /hermes-* · /persona-* · /criticalthink"
echo ""
echo "  ┌──────────────────────────────────────────┐"
echo "  │  ACTION REQUIRED — plugins               │"
echo "  │                                          │"
echo "  │  Open Claude Code and run:               │"
echo "  │                                          │"
echo "  │    /plugin install claude-mem            │"
echo "  │    /plugin install superpowers           │"
echo "  │                                          │"
echo "  │  Then restart Claude Code.               │"
echo "  └──────────────────────────────────────────┘"
echo ""
echo "  After restarting Claude Code:"
echo ""
echo "  New project:"
echo "    mkdir my-project && cd my-project && git init"
echo "    bash $HERMES_DIR/scripts/hermes-init.sh"
echo "    claude  →  /hermes-init"
echo ""
echo "  Existing project:"
echo "    cd your-project"
echo "    cp $HERMES_DIR/hermes/commands/*.md .claude/commands/"
echo "    claude  →  /hermes-adopt"
echo ""
