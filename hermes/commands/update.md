---
name: hermes-update
description: >
  Updates cc-forge personas, standards, and commands in the current project
  from the cc-forge source repo. Run this whenever cc-forge is updated on
  GitHub to get the latest persona definitions, backlog items, and standards
  without re-running the full init. Safe to run on any project at any time.
model: claude-haiku-4-5
effort: low
tools: Bash, Write
---

# Hermes Update

<role>
You are updating the cc-forge files in the current project from the source
repo. This is a maintenance operation — fast, silent, and safe. You copy
the latest persona definitions, standards, and commands into the project's
.cc-forge/ directory and .claude/commands/ directory.
</role>

<constraints>
- Never overwrite project-specific files (CLAUDE.md, PRD.md, state.json,
  backlog files, DECISIONS.md, RISKS.md) — only update cc-forge source files
- Always show what was updated so the developer knows what changed
- If cc-forge source not found at ~/cc-forge, tell the developer how to fix it
- Run silently and quickly — this should take under 30 seconds
</constraints>

---

## Process

```bash
# Locate cc-forge source
HERMES_DIR="${HERMES_DIR:-$HOME/cc-forge}"

if [ ! -d "$HERMES_DIR" ]; then
  echo "cc-forge not found at $HERMES_DIR"
  echo "Pull latest: git clone https://github.com/A-Director/cc-forge.git ~/cc-forge"
  echo "Or set HERMES_DIR to your cc-forge location"
  exit 1
fi

# Pull latest from GitHub first
echo "▸ Pulling latest cc-forge..."
cd "$HERMES_DIR" && git pull origin main --quiet && cd - > /dev/null

# Update personas
echo "▸ Updating personas..."
mkdir -p .cc-forge/personas
cp "$HERMES_DIR"/personas/*.md .cc-forge/personas/
echo "  ✓ $(ls .cc-forge/personas/*.md | wc -l) persona files updated"

# Update standards
echo "▸ Updating standards..."
mkdir -p .cc-forge/standards
cp "$HERMES_DIR"/standards/*.md .cc-forge/standards/
echo "  ✓ $(ls .cc-forge/standards/*.md | wc -l) standard files updated"

# Update commands
echo "▸ Updating commands..."
mkdir -p .claude/commands
cp "$HERMES_DIR"/hermes/commands/*.md .claude/commands/
cp "$HERMES_DIR"/hermes/init.md .claude/commands/hermes-init.md
cp "$HERMES_DIR"/hermes/adopt.md .claude/commands/hermes-adopt.md
cp "$HERMES_DIR"/hermes/backlog-init.md .claude/commands/hermes-backlog-init.md
cp "$HERMES_DIR"/hermes/log.md .claude/commands/hermes-log.md
echo "  ✓ $(ls .claude/commands/hermes-*.md | wc -l) hermes commands updated"

# Update backlog catalogue (default items only — not project backlog)
echo "▸ Updating backlog catalogue reference..."
mkdir -p .cc-forge/catalogue
cp "$HERMES_DIR"/backlog/*.md .cc-forge/catalogue/
echo "  ✓ $(ls .cc-forge/catalogue/*.md | wc -l) catalogue files updated"
echo "  (Project backlog in .cc-forge/backlog/ unchanged)"

# Create hooks if missing — safe to run on existing projects
echo "▸ Checking Claude hooks..."
mkdir -p .claude/hooks
if [ ! -f ".claude/hooks/start.sh" ]; then
  cat > .claude/hooks/start.sh << 'HOOKEOF'
#!/bin/bash
[ -f ".cc-forge/state.json" ] || exit 0
command -v bun &>/dev/null || true
HOOKEOF
  chmod +x .claude/hooks/start.sh
  echo "  ✓ .claude/hooks/start.sh (created)"
else
  echo "  · .claude/hooks/start.sh (already exists)"
fi
if [ ! -f ".claude/hooks/stop.sh" ]; then
  cat > .claude/hooks/stop.sh << 'HOOKEOF'
#!/bin/bash
command -v bun &>/dev/null || true
if [ -f ".cc-forge/state.json" ]; then
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  echo "{\"ts\":\"$TS\",\"type\":\"session_end\"}" >> .cc-forge/usage.log 2>/dev/null || true
fi
HOOKEOF
  chmod +x .claude/hooks/stop.sh
  echo "  ✓ .claude/hooks/stop.sh (created)"
else
  echo "  · .claude/hooks/stop.sh (already exists)"
fi
```

---

<output_format>

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  HERMES UPDATE COMPLETE  ·  [date]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  cc-forge: [latest commit hash]

  Updated:
  ✓ [N] personas     → .cc-forge/personas/
  ✓ [N] standards    → .cc-forge/standards/
  ✓ [N] commands     → .claude/commands/
  ✓ [N] catalogue    → .cc-forge/catalogue/

  Not touched (project-specific):
  · .cc-forge/backlog/     (your project backlog)
  · .cc-forge/state.json   (project state)
  · CLAUDE.md, PRD.md      (your documents)
  · DECISIONS.md, RISKS.md (your decisions)

  Restart Claude Code to activate updated commands.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

</output_format>
