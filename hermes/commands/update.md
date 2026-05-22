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
- **Command-file copies MUST be prefixed.** For files in
  `$HERMES_DIR/hermes/commands/*.md`, you MUST iterate the directory and
  write each file out as `.claude/commands/hermes-<basename>.md`. You MUST
  NOT use `cp "$HERMES_DIR"/hermes/commands/*.md .claude/commands/` — that
  bare wildcard form is gap #50 and silently strips the prefix. The
  personas and standards directories *do* use bare `cp *.md` because those
  files keep their names; the commands directory does not. Do not mimic
  the personas pattern in the commands section.
- **Always run the verification step at the end.** If it fails, surface
  the failure to the developer — do not declare success.
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
# IMPORTANT — gap #50: source files in hermes/commands/ are stored without
# the hermes- prefix (status.md, next.md, dashboard.md …). The .claude/commands/
# slash-command namespace expects them prefixed (hermes-status.md, …).
# The loop below renames on copy; do NOT replace it with a bare-wildcard cp.
echo "▸ Updating commands..."
mkdir -p .claude/commands

for f in "$HERMES_DIR"/hermes/commands/*.md; do
  [ -f "$f" ] || continue
  name=$(basename "$f" .md)
  cp "$f" .claude/commands/hermes-${name}.md
done
cp "$HERMES_DIR"/hermes/init.md .claude/commands/hermes-init.md
cp "$HERMES_DIR"/hermes/adopt.md .claude/commands/hermes-adopt.md
cp "$HERMES_DIR"/hermes/backlog-init.md .claude/commands/hermes-backlog-init.md
cp "$HERMES_DIR"/hermes/log.md .claude/commands/hermes-log.md
echo "  ✓ $(ls .claude/commands/hermes-*.md | wc -l) hermes commands updated"

# Cleanup: remove unprefixed legacy command files from previous
# /hermes-update runs (pre-fix bug #50). Hardcoded basename list — historical
# set of hermes/commands/ + hermes/ root files — so future renames don't leave
# stale shadows. Add new basenames here when new commands are added.
echo "▸ Cleaning up legacy unprefixed commands..."
cleaned=0
for legacy in status next gate-review dashboard deploy report update \
              quality clean argus phase-gate taskmaster-seed \
              research backlog init adopt backlog-init log; do
  if [ -f ".claude/commands/${legacy}.md" ]; then
    rm -f ".claude/commands/${legacy}.md"
    echo "  · removed legacy /${legacy} (use /hermes-${legacy})"
    cleaned=$((cleaned + 1))
  fi
done
if [ $cleaned -eq 0 ]; then
  echo "  ✓ no legacy commands found — namespace clean"
fi

# Verification (gap #50, second pass). If any unprefixed legacy command
# still exists after the cleanup, the prefix-on-copy step above was
# bypassed or skipped — fail loudly rather than silently succeeding.
echo "▸ Verifying command namespace..."
violations=0
for legacy in status next gate-review dashboard deploy report update \
              quality clean argus phase-gate taskmaster-seed \
              research backlog init adopt backlog-init log; do
  if [ -f ".claude/commands/${legacy}.md" ]; then
    echo "  ✗ FOUND unprefixed .claude/commands/${legacy}.md — gap #50 regression"
    violations=$((violations + 1))
  fi
done
if [ $violations -gt 0 ]; then
  echo ""
  echo "  Refusing to declare /hermes-update complete."
  echo "  Re-run the prefix-on-copy loop above and the cleanup pass."
  echo "  Files in hermes/commands/*.md MUST land as hermes-<name>.md, not <name>.md."
  exit 2
fi
echo "  ✓ namespace clean — only hermes-* command files present"

# Update backlog catalogue (default items only — not project backlog)
echo "▸ Updating backlog catalogue reference..."
mkdir -p .cc-forge/catalogue
cp "$HERMES_DIR"/backlog/*.md .cc-forge/catalogue/
echo "  ✓ $(ls .cc-forge/catalogue/*.md | wc -l) catalogue files updated"
echo "  (Project backlog in .cc-forge/backlog/ unchanged)"

# Update Python scripts (Session C onward).
# Non-markdown deliverables like scripts/hermes-dashboard.py need to land
# in the project too, otherwise /hermes-dashboard fails on first use
# with "scripts/hermes-dashboard.py: No such file or directory" — gap #52.
echo "▸ Updating scripts..."
mkdir -p scripts
if [ -d "$HERMES_DIR/scripts" ]; then
  cp "$HERMES_DIR"/scripts/*.py scripts/ 2>/dev/null || true
  script_count=$(ls scripts/*.py 2>/dev/null | wc -l)
  echo "  ✓ $script_count script files updated"
else
  echo "  · no scripts/ directory in cc-forge source"
fi

# Update Hermes calibration files (token-weights, etc.).
# Same gap #52 concern: non-markdown configs need explicit copy.
# Destination is hermes/ (not .cc-forge/) because scripts/hermes-dashboard.py
# reads token-weights.json via __file__.parent.parent / "hermes" / "token-weights.json"
# — i.e. <project>/hermes/token-weights.json relative to scripts/.
echo "▸ Updating Hermes calibration..."
mkdir -p hermes
if [ -f "$HERMES_DIR/hermes/token-weights.json" ]; then
  cp "$HERMES_DIR/hermes/token-weights.json" hermes/
  echo "  ✓ token-weights.json updated"
fi

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

# Verify Session C deliverables landed correctly (gap #52).
# Same defense-in-depth pattern as the gap #50 second pass: catch the
# failure loudly here rather than letting /hermes-dashboard fail later.
echo "▸ Verifying Session C deliverables..."
missing=0
if [ ! -f "scripts/hermes-dashboard.py" ]; then
  echo "  ✗ scripts/hermes-dashboard.py missing — /hermes-dashboard will fail"
  missing=$((missing + 1))
fi
if [ ! -f "hermes/token-weights.json" ]; then
  echo "  ✗ hermes/token-weights.json missing — overhead calc will use defaults"
  missing=$((missing + 1))
fi
if [ $missing -eq 0 ]; then
  echo "  ✓ Session C deliverables present"
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
  ✓ [N] scripts      → scripts/                        ← omit if cc-forge has no scripts/
  ✓ 1 calibration  → hermes/token-weights.json       ← omit if source file missing

  Cleaned:                                              ← only when cleaned > 0
  ✓ [N] legacy unprefixed commands removed (gap #50 hotfix)

  Not touched (project-specific):
  · .cc-forge/backlog/     (your project backlog)
  · .cc-forge/state.json   (project state)
  · CLAUDE.md, PRD.md      (your documents)
  · DECISIONS.md, RISKS.md (your decisions)

  Restart Claude Code to activate updated commands.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

When `cleaned == 0`, omit the **Cleaned:** block entirely — a clean
namespace doesn't need a callout.

</output_format>

---

## Session orient hook

To enable automatic Hermes status at session start, add the hook from
`templates/hooks/settings-hook.json` to your `~/.claude/settings.json`
manually. This is a one-time setup per machine, not per project.

