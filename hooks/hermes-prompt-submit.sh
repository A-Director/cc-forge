#!/bin/bash
# hermes-prompt-submit.sh — UserPromptSubmit hook (Session D, Phase A).
#
# Spec §2.8. The UserPromptSubmit hook fires on every user message and
# injects a lightweight per-prompt framing via additionalContext to
# counter in-conversation voice decay (§6.9).
#
# Phase A responsibilities (this script, no model call):
#   1. Phase scope reminder — current PDLC phase + one-line in-scope hint.
#   2. Closure-discipline reminder — "one next step, stated not asked".
#
# Phase B responsibility (added in Phase B of Session D):
#   3. Intake detection — pre-filter then cheap classifier; on bypass,
#      log bypass_detected and inject escalation framing.
#
# Output contract (Claude Code UserPromptSubmit hook):
#   stdin   JSON {session_id, transcript_path, cwd, prompt}
#   stdout  JSON {hookSpecificOutput: {hookEventName: "UserPromptSubmit",
#                                       additionalContext: "..."}}
#   Exit 0 always (hook failure must not interrupt the prompt).

set -u

PROJECT_ROOT="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE_JSON="${PROJECT_ROOT}/.cc-forge/state.json"
USAGE_LOG="${PROJECT_ROOT}/.cc-forge/usage.log"

# Safety: hook installed plugin-wide — only act on cc-forge projects.
if [ ! -f "$STATE_JSON" ]; then
  exit 0
fi

# Read stdin (Claude Code passes JSON). We mostly care about `prompt`
# in Phase B; Phase A just needs to fire reliably.
HOOK_INPUT=""
if [ ! -t 0 ]; then
  HOOK_INPUT=$(cat 2>/dev/null || true)
fi

# Extract phase from state.json. Use python for robust JSON parsing.
read -r PHASE PHASE_NAME <<<"$(python3 - "$STATE_JSON" <<'PYEOF' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1]) as f:
        s = json.load(f)
    phase = s.get("current_pdlc_phase")
    name = s.get("current_pdlc_phase_name") or ""
    print(f"{phase or '?'} {name}")
except Exception:
    print("? ")
PYEOF
)"

# Phase scope hints (one-line) per PHASES.md. Keep these terse — the
# whole framing budget is ~100–200 tokens per spec §2.8.
case "$PHASE" in
  1) SCOPE_HINT="prove the core user journey end-to-end; defer scale, formal compliance, growth motions, public marketing." ;;
  2) SCOPE_HINT="get real users on it, iterate on feedback; defer scale work, public marketing, full GDPR." ;;
  3) SCOPE_HINT="paid customers + production ops; defer public marketing, full accessibility certification." ;;
  4) SCOPE_HINT="public availability; meet compliance + accessibility bars; defer experimentation infrastructure." ;;
  5) SCOPE_HINT="sustained growth + optimization + scale; all domains in scope." ;;
  *) SCOPE_HINT="phase unknown — run /hermes-status to check state.json." ;;
esac

# Compose framing. Two short blocks; under the §2.8 token budget.
PHASE_LABEL="$PHASE"
if [ -n "${PHASE_NAME:-}" ]; then
  PHASE_LABEL="$PHASE ${PHASE_NAME}"
fi

FRAMING=$(cat <<EOF
HERMES per-prompt framing (deterministic, injected by UserPromptSubmit hook).

· Phase: ${PHASE_LABEL} — ${SCOPE_HINT}
· Closure: when this exchange closes, state one next step. Phrase it as a statement ("I'll next ..." / "we should next ..."), not a question ("want me to ...?"). The pattern is "stated, not asked."
EOF
)

# Phase B — intake-bypass classifier. Pre-filter then optional Haiku
# call; on bypass detection, append escalation framing and log
# bypass_detected. The classifier is a probabilistic FIRST line; the
# deterministic backstop (intake_reconciliation) catches misses.
PROMPT_TEXT=""
if [ -n "$HOOK_INPUT" ]; then
  PROMPT_TEXT=$(printf '%s' "$HOOK_INPUT" | python3 -c 'import json,sys
try:
    d=json.loads(sys.stdin.read())
    print(d.get("prompt","") or "")
except Exception:
    print("")' 2>/dev/null || true)
fi

if [ -n "$PROMPT_TEXT" ]; then
  # Locate the classifier script relative to this hook. Hooks live at
  # <plugin_root>/hooks/; classifier at <plugin_root>/scripts/.
  HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  CLASSIFIER="${HOOK_DIR}/../scripts/_hermes_classifier.py"
  if [ -f "$CLASSIFIER" ]; then
    # Cap the hook's own time spend so a stuck classifier never blocks
    # the prompt. The deterministic backstop catches anything we skip.
    CLASSIFIER_OUT=$(PROMPT_TEXT="$PROMPT_TEXT" timeout 20s python3 "$CLASSIFIER" classify \
      --prompt "$PROMPT_TEXT" --project-root "$PROJECT_ROOT" 2>/dev/null || true)
    if [ -n "$CLASSIFIER_OUT" ]; then
      ESCALATION=$(printf '%s' "$CLASSIFIER_OUT" | python3 -c 'import json,sys
try:
    d=json.loads(sys.stdin.read())
    if d.get("bypass") and d.get("escalation_framing"):
        print(d["escalation_framing"])
except Exception:
    pass' 2>/dev/null || true)
      if [ -n "$ESCALATION" ]; then
        FRAMING="${FRAMING}

· INTAKE FLAG (probabilistic first line — see /hermes-intake): ${ESCALATION}"
      fi
    fi
  fi
fi

# Emit hook output JSON. additionalContext is appended to the model's
# context for this turn only — not persisted.
export FRAMING
python3 - <<'PYEOF'
import json, os
framing = os.environ.get("FRAMING", "")
print(json.dumps({
    "hookSpecificOutput": {
        "hookEventName": "UserPromptSubmit",
        "additionalContext": framing
    }
}))
PYEOF

exit 0
