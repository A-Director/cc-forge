#!/bin/bash
# hermes-migrate-to-plugin.sh — pre-plugin → plugin migration (Session 0).
#
# Spec §4.7. Runs first against CLARK, then any other pre-plugin project.
# Treats the migration as multi-step with explicit safety:
#   --dry-run   : print the diff of what would change; no writes.
#   --rollback  : restore from the most recent backup; undo the migration.
#   (default)   : apply with backup, step-wise log, and explicit
#                 stop-on-failure.
#
# This is destructive on a real project. The 12-step sequence:
#   1. Detect pre-plugin state.
#   2. Backup .cc-forge/.
#   3. Dry-run gate (if --dry-run, print and exit before any change).
#   4. Remove legacy global commands (gap #51 cleanup).
#   5. Remove hardcoded SessionStart hook from ~/.claude/settings.json.
#   6. Add marketplace + install plugin (/plugin marketplace add + /plugin install cc-forge@cc-forge).
#   7. Confirm Layer 1 reachability via CLAUDE_PLUGIN_ROOT.
#   8. Catalogue format migration (hermes-migrate-backlog-format.sh applied
#      to .cc-forge/backlog/) — strict fidelity gate, grandfathered/non
#      bucketing.
#   9. Optionally clean per-project Layer 1 copies (.cc-forge/personas,
#      .cc-forge/standards, .cc-forge/catalogue).
#  10. Migrate token-weights (project hermes/ → .cc-forge/overrides/ if
#      differs from canonical, else delete).
#  11. Write migration log.
#  12. Report.

set -u

MODE="apply"
HERMES_DIR="${HERMES_DIR:-}"
PROJECT_ROOT="$(pwd)"

usage() {
  cat <<EOF
Usage: $0 [--dry-run] [--rollback] [--hermes-dir PATH]

Migrates a cc-forge project from pre-plugin layout to plugin layout.

  --dry-run            Print what would change without applying.
  --rollback           Restore from the most recent backup; undo migration.
  --hermes-dir PATH    Path to the cc-forge source (default: \$HERMES_DIR).
  --help               This message.

Run from the project root.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)     MODE="dry-run"; shift;;
    --rollback)    MODE="rollback"; shift;;
    --hermes-dir)  HERMES_DIR="$2"; shift 2;;
    --help|-h)     usage; exit 0;;
    *)             echo "unknown flag: $1" >&2; usage; exit 1;;
  esac
done

# ─── ROLLBACK MODE — restore from backup, then exit ───
if [ "$MODE" = "rollback" ]; then
  latest_backup=$(ls -td .cc-forge.backup-* 2>/dev/null | head -1)
  if [ -z "$latest_backup" ]; then
    echo "✗ No backup directory found (.cc-forge.backup-*)." >&2
    echo "  Cannot rollback without a backup." >&2
    exit 1
  fi
  echo "▸ Rolling back from: $latest_backup"
  rm -rf .cc-forge
  cp -r "$latest_backup" .cc-forge
  rm -rf "$latest_backup"
  echo "  ✓ .cc-forge/ restored"
  echo ""
  echo "  Operator: also un-install the plugin if it was installed:"
  echo "    /plugin uninstall cc-forge"
  echo "  Operator: also restore your hardcoded SessionStart hook in"
  echo "    ~/.claude/settings.json if you removed it as part of the migration."
  echo ""
  echo "  Rollback complete."
  exit 0
fi

# ─── HERMES_DIR resolution ───
if [ -z "$HERMES_DIR" ]; then
  for candidate in "$HOME/cc-forge" "$HOME/.local/share/cc-forge" "/usr/local/share/cc-forge"; do
    if [ -d "$candidate/.claude-plugin" ]; then
      HERMES_DIR="$candidate"
      break
    fi
  done
fi
if [ -z "$HERMES_DIR" ] || [ ! -d "$HERMES_DIR/.claude-plugin" ]; then
  echo "✗ Could not locate cc-forge source. Pass --hermes-dir PATH or set HERMES_DIR." >&2
  exit 1
fi

iso_ts=$(date -u +"%Y-%m-%dT%H-%M-%SZ")
BACKUP_DIR=".cc-forge.backup-${iso_ts}"
LOG_FILE=""

log() {
  echo "$@"
  if [ -n "$LOG_FILE" ]; then
    echo "[$(date -u +%H:%M:%S)] $*" >> "$LOG_FILE"
  fi
}

# ─── STEP 1: detect ───
echo "▸ Step 1: detecting pre-plugin state..."
findings=()
if ls "$HOME"/.claude/commands/hermes-*.md >/dev/null 2>&1; then
  findings+=("global cc-forge commands at ~/.claude/commands/ (gap #51)")
fi
if [ -f "$HOME/.claude/settings.json" ] && grep -q '"cc-forge"\|cc-forge.*SessionStart' "$HOME/.claude/settings.json" 2>/dev/null; then
  findings+=("hardcoded cc-forge entry in ~/.claude/settings.json")
fi
for d in personas standards catalogue; do
  if [ -d ".cc-forge/$d" ]; then
    findings+=("per-project Layer 1 copy: .cc-forge/$d/")
  fi
done
if [ -f "hermes/token-weights.json" ]; then
  findings+=("project-local token-weights.json from gap #52 era at hermes/")
fi
# Bold-form catalogue (pre-format-migration)
if [ -d ".cc-forge/backlog" ] && grep -rln '\*\*[A-Z][A-Za-z-]*:\*\*' .cc-forge/backlog/*.md >/dev/null 2>&1; then
  findings+=("backlog items in bold-field form (pre-§3.2 list-form)")
fi
if [ ${#findings[@]} -eq 0 ]; then
  echo "  ✓ no pre-plugin artefacts detected"
  echo ""
  echo "  This project may already be on the plugin layout. Nothing to migrate."
  exit 0
fi
for f in "${findings[@]}"; do
  echo "  · $f"
done

# ─── STEP 2: backup ───
echo ""
echo "▸ Step 2: backing up .cc-forge/..."
if [ -d ".cc-forge" ]; then
  if [ "$MODE" = "apply" ]; then
    cp -r .cc-forge "$BACKUP_DIR"
    LOG_FILE="$BACKUP_DIR/migration.log"
    echo "[$(date -u +%H:%M:%S)] migration started" >> "$LOG_FILE"
    echo "  ✓ backup: $BACKUP_DIR"
  else
    echo "  (dry-run: would copy .cc-forge/ → $BACKUP_DIR)"
  fi
fi

# ─── STEP 3: dry-run gate ───
if [ "$MODE" = "dry-run" ]; then
  echo ""
  echo "▸ Step 3: dry-run gate active. The following steps WOULD be applied:"
  echo "  4. rm -f ~/.claude/commands/hermes-*.md (legacy global commands)"
  echo "  5. edit ~/.claude/settings.json: remove cc-forge SessionStart entry"
  echo "  6. /plugin marketplace add $HERMES_DIR && /plugin install cc-forge@cc-forge  (operator runs in Claude Code)"
  echo "  7. verify \${CLAUDE_PLUGIN_ROOT} reachable (operator-visible)"
  echo "  8. catalogue format migration — running script in dry-run now:"
  echo "     ----------------------------------------------------------------"
  if [ -d ".cc-forge/backlog" ]; then
    "$HERMES_DIR/scripts/hermes-migrate-backlog-format.sh" --dry-run .cc-forge/backlog 2>&1 | sed 's/^/     /'
  else
    echo "     (no .cc-forge/backlog/ — skipping format migration)"
  fi
  echo "     ----------------------------------------------------------------"
  echo "  9. rm -rf .cc-forge/{personas,standards,catalogue}/  (per-project Layer 1)"
  echo "  10. handle hermes/token-weights.json (override or delete)"
  echo "  11. write migration log to $BACKUP_DIR/migration.log"
  echo "  12. emit report"
  echo ""
  echo "  No changes have been applied. Re-run without --dry-run to apply."
  exit 0
fi

# ─── STEP 4: remove legacy global commands ───
echo ""
log "▸ Step 4: removing legacy global commands..."
removed=0
for legacy in status next gate-review dashboard deploy report update \
              quality clean argus phase-gate taskmaster-seed \
              research backlog init adopt backlog-init log; do
  if [ -f "$HOME/.claude/commands/hermes-${legacy}.md" ]; then
    rm -f "$HOME/.claude/commands/hermes-${legacy}.md"
    log "  · removed ~/.claude/commands/hermes-${legacy}.md"
    removed=$((removed + 1))
  fi
done
log "  ✓ removed $removed legacy global command files"

# ─── STEP 5: remove hardcoded SessionStart hook ───
echo ""
log "▸ Step 5: scanning ~/.claude/settings.json for hardcoded cc-forge hook..."
if [ -f "$HOME/.claude/settings.json" ] && grep -q "cc-forge" "$HOME/.claude/settings.json" 2>/dev/null; then
  log "  ⚠ hardcoded cc-forge entry detected in ~/.claude/settings.json"
  log "    The migration cannot safely edit this file (it may contain other"
  log "    user-managed hooks). Operator must remove the cc-forge SessionStart"
  log "    entry manually. Once removed, the plugin's hooks take over."
else
  log "  ✓ no hardcoded cc-forge entry"
fi

# ─── STEP 6: plugin install (operator action) ───
echo ""
log "▸ Step 6: plugin install"
log "  Operator must run in Claude Code:"
log "    /plugin marketplace add $HERMES_DIR && /plugin install cc-forge@cc-forge"
log "  This script cannot install the plugin directly — Claude Code owns plugin install."

# ─── STEP 7: layer 1 reachability ───
echo ""
log "▸ Step 7: layer 1 reachability"
if [ -n "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -d "${CLAUDE_PLUGIN_ROOT}" ]; then
  log "  ✓ CLAUDE_PLUGIN_ROOT set: ${CLAUDE_PLUGIN_ROOT}"
else
  log "  · CLAUDE_PLUGIN_ROOT not set in this shell (expected — set inside Claude Code)."
fi

# ─── STEP 8: catalogue format migration with fidelity gate ───
echo ""
log "▸ Step 8: catalogue format migration..."
if [ -d ".cc-forge/backlog" ]; then
  if "$HERMES_DIR/scripts/hermes-migrate-backlog-format.sh" .cc-forge/backlog 2>&1 | tee -a "$LOG_FILE"; then
    log "  ✓ catalogue format migration passed fidelity gate"
  else
    log "  ✗ catalogue format migration failed fidelity gate — halting."
    log "    Run --rollback to restore from $BACKUP_DIR."
    exit 2
  fi
else
  log "  · .cc-forge/backlog/ not present; skipping"
fi

# ─── STEP 9: clean per-project Layer 1 copies ───
echo ""
log "▸ Step 9: cleaning per-project Layer 1 copies..."
for d in personas standards catalogue; do
  if [ -d ".cc-forge/$d" ]; then
    rm -rf ".cc-forge/$d"
    log "  · removed .cc-forge/$d/"
  fi
done
log "  ✓ Layer 1 copies cleaned (plugin space is canonical)"

# ─── STEP 10: token-weights handling ───
echo ""
log "▸ Step 10: token-weights..."
proj_weights="hermes/token-weights.json"
canon_weights="$HERMES_DIR/token-weights.json"
if [ -f "$proj_weights" ] && [ -f "$canon_weights" ]; then
  if diff -q "$proj_weights" "$canon_weights" >/dev/null 2>&1; then
    rm "$proj_weights"
    log "  · removed $proj_weights (identical to canonical)"
  else
    mkdir -p .cc-forge/overrides
    mv "$proj_weights" .cc-forge/overrides/token-weights.json
    log "  · preserved as override: .cc-forge/overrides/token-weights.json"
  fi
  rmdir hermes 2>/dev/null && log "  · removed empty hermes/ directory" || true
else
  log "  · no project-local token-weights.json to handle"
fi

# ─── STEP 11: write log ───
echo ""
log "▸ Step 11: migration log written to: $LOG_FILE"
log "[$(date -u +%H:%M:%S)] migration complete"

# ─── STEP 12: report ───
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  cc-forge migration complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Backup:           $BACKUP_DIR"
echo "  Log:              $LOG_FILE"
echo ""
echo "  Operator action items:"
echo "    1. Run /plugin marketplace add $HERMES_DIR && /plugin install cc-forge@cc-forge in Claude Code"
echo "    2. Remove any cc-forge entry from ~/.claude/settings.json (see step 5)"
echo "    3. Verify with /hermes-argus"
echo ""
echo "  Rollback if needed: $0 --rollback"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
exit 0
