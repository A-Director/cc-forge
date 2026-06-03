---
name: hermes-update
description: >
  Updates the cc-forge plugin in this project. Delegates to Claude Code's
  /plugin update, runs any pending state.json migrations, verifies layer
  reachability via /hermes-doctor, and reports.
allowed-tools: Bash, Read
---

# Hermes Update

<role>
You are updating the cc-forge plugin in the current project. cc-forge runs
as a Claude Code plugin (spec §4): Layer 1 (framework primitives) lives in
the plugin and is referenced via `${CLAUDE_PLUGIN_ROOT}`; Layer 2 (project
state) lives in `.cc-forge/` and is project-specific.

Because Layer 1 is plugin-managed, this command does NOT copy files from
the cc-forge source tree into the project (that was the gap #52 model).
It delegates plugin distribution to Claude Code, then runs migrations and
verification.
</role>

<constraints>
- Never modify Layer 3 user files (CLAUDE.md, PRD.md, RISKS.md,
  DECISIONS.md, CHANGELOG.md) — those are user-owned per §4.5.
- Run migrations forward-only and idempotently per §3.9.
- Surface verification failure loudly — do not declare success on a broken
  Layer 1 reachability check.
- If `${CLAUDE_PLUGIN_ROOT}` is unset, the plugin isn't installed; tell the
  developer to run `/plugin marketplace add <path>; /plugin install cc-forge@cc-forge` first.
</constraints>

---

## Process

```bash
# Step 1: confirm plugin reachable
if [ -z "${CLAUDE_PLUGIN_ROOT:-}" ]; then
  echo "✗ CLAUDE_PLUGIN_ROOT not set — cc-forge plugin is not installed."
  echo "  In Claude Code, run: /plugin marketplace add <path>; /plugin install cc-forge@cc-forge"
  exit 1
fi
if [ ! -d "${CLAUDE_PLUGIN_ROOT}" ]; then
  echo "✗ CLAUDE_PLUGIN_ROOT is set but the directory is missing: ${CLAUDE_PLUGIN_ROOT}"
  exit 1
fi

echo "▸ Plugin root: ${CLAUDE_PLUGIN_ROOT}"
plugin_version=$(grep -o '"version":[[:space:]]*"[^"]*"' \
  "${CLAUDE_PLUGIN_ROOT}/.claude-plugin/plugin.json" 2>/dev/null \
  | head -1 | sed 's/.*"\([^"]*\)"$/\1/')
echo "  Installed plugin version: ${plugin_version:-unknown}"

# Step 2: version check against state.json
required_version=""
if [ -f .cc-forge/state.json ]; then
  required_version=$(grep -o '"cc_forge_required_version":[[:space:]]*"[^"]*"' \
    .cc-forge/state.json 2>/dev/null | sed 's/.*"\([^"]*\)"$/\1/')
fi
if [ -n "$required_version" ] && [ -n "$plugin_version" ]; then
  echo "▸ Required by project: ${required_version}"
  req_major=$(echo "$required_version" | cut -d. -f1)
  inst_major=$(echo "$plugin_version" | cut -d. -f1)
  if [ "$req_major" != "$inst_major" ]; then
    echo "  ⚠ MAJOR VERSION MISMATCH — project requires v${req_major}.x.x,"
    echo "    plugin is v${inst_major}.x.x. State migrations may be required."
  else
    echo "  ✓ major version compatible"
  fi
fi

# Step 3: run pending migrations
ran=0
if [ -d "${CLAUDE_PLUGIN_ROOT}/migrations" ]; then
  echo "▸ Checking for pending migrations..."
  for m in "${CLAUDE_PLUGIN_ROOT}"/migrations/*.sh; do
    [ -f "$m" ] || continue
    bash "$m" && ran=$((ran + 1))
  done
  if [ "$ran" -gt 0 ]; then
    echo "  ✓ ran $ran migration scripts (idempotent)"
  else
    echo "  · no migrations present"
  fi
fi

# Step 4: verify layer reachability via doctor
echo "▸ Verifying with /hermes-doctor..."
if python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hermes-doctor.py" --json 2>/dev/null > /tmp/hermes-doctor-out.json; then
  verdict=$(python3 -c "import json; print(json.load(open('/tmp/hermes-doctor-out.json'))['summary']['verdict'])" 2>/dev/null)
  fails=$(python3 -c "import json; print(json.load(open('/tmp/hermes-doctor-out.json'))['summary']['failures'])" 2>/dev/null)
  echo "  Doctor verdict: ${verdict:-unknown} (${fails:-?} failures)"
  rm -f /tmp/hermes-doctor-out.json
else
  echo "  · doctor not invocable (verification skipped — run /hermes-doctor manually)"
fi

# Step 5: report
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  HERMES UPDATE COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Plugin version:   ${plugin_version:-unknown}"
if [ -n "$required_version" ]; then
  echo "  Project requires: ${required_version}"
fi
echo "  Migrations:       ${ran} run"
echo ""
echo "  Layer 1 (plugin):  ${CLAUDE_PLUGIN_ROOT}"
echo "  Layer 2 (project): .cc-forge/"
echo "  Layer 3 (user):    CLAUDE.md, PRD.md, RISKS.md, DECISIONS.md (untouched)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## Notes

- **No file copies.** Plugin content is referenced live via
  `${CLAUDE_PLUGIN_ROOT}`. The gap #50/#52 prefix-strip and copy-list-drift
  failure modes no longer apply because there is no copy.
- **Migrations are idempotent.** Re-running an already-applied migration is
  a no-op. Safe to run after every plugin update.
- **Doctor is the verification.** If the plugin's Layer 1 surface isn't
  reachable from this project, the doctor catches it. If a migration
  failed to land cleanly, the doctor's Layer 2 checks catch it.
- **No CLAUDE.md mutation.** §2.4 dropped the requirement that CLAUDE.md
  carry a rendering instruction — the hook's stdout is self-contained.
  `/hermes-update` never touches CLAUDE.md.
