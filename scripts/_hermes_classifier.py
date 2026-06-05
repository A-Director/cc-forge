"""
Hermes intake-bypass classifier (Session D, Phase B).

Two-stage pipeline per spec §3.6 and the Session D brief:

  1. Pre-filter — deterministic heuristics, runs on every prompt. Decides
     ONLY whether to spend a model call; it does NOT decide whether bypass
     occurred. The pre-filter is intentionally NOT keyword-matching-for-
     bypass (that would be all false positives on "add"/"build"/"implement").
     It rules out trivial prompts (too short, bare acknowledgement, no
     request-like shape) so we don't burn a Haiku call on "thanks".

  2. Classifier — Haiku-class model call on prompts that pass the pre-
     filter. Asks "does this user message introduce work not already
     represented in the current backlog or in-flight tasks?" with the
     backlog summary as context. Returns confidence (0.0–1.0). Above
     threshold → bypass detected.

Honesty: the classifier is a probabilistic FIRST line. The framework's
integrity lives in the deterministic backstop (intake_reconciliation in
the Doctor session), never in the classifier being right.

Testable in isolation: HERMES_CLASSIFIER_STUB env var overrides the
model call with a fixed confidence so verification can run without
burning real tokens. Production invokes `claude -p` from a project-
free temp dir (cwd switch avoids picking up the active session's
context — that would cause classifier-into-classifier recursion).

CLI:
  python3 _hermes_classifier.py classify --prompt "..." --project-root /path
  python3 _hermes_classifier.py prefilter --prompt "..."
  python3 _hermes_classifier.py summary --project-root /path
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

# Confidence threshold above which we log bypass_detected.
BYPASS_THRESHOLD = 0.70

# Bare-acknowledgement set. Pre-filter rules these out — explicit,
# enumerated, not heuristic. A length/word-count threshold would create
# the dangerous failure mode the pre-filter must avoid: a short-but-
# substantive prompt ("add OAuth", "drop the cache layer") being
# silently suppressed and never reaching the classifier, which is
# exactly a silent bypass — the thing intake exists to prevent.
#
# So the pre-filter is conservative: only enumerated bare acks AND
# empty prompts are suppressed. Everything else hits the classifier.
# This costs a few more Haiku calls; the cost of over-suppression
# (silent bypass) is much higher than the cost of an extra cheap call.
BARE_ACKS = {
    "ok", "okay", "yes", "yeah", "yep", "sure", "no", "nope",
    "thanks", "thank you", "ty", "thx", "ack", "got it", "right",
    "good", "great", "perfect", "nice", "cool", "fine",
    "continue", "go", "go ahead", "proceed", "next",
    "done", "finished", "k",
}


def prefilter(prompt: str) -> tuple[bool, str]:
    """
    Return (should_classify, reason). True means "spend a model call";
    False means "don't bother — this is trivially not a scope-change".

    The pre-filter is NOT scope detection. Suppression is enumerated and
    conservative; short-substantive prompts like "add OAuth" MUST pass
    through to the classifier. Over-suppression is the one dangerous
    failure mode — it would create silent bypass.
    """
    if not prompt or not prompt.strip():
        return False, "empty prompt"

    stripped = prompt.strip().lower().rstrip(".!?")
    if stripped in BARE_ACKS:
        return False, f"bare acknowledgement ({stripped!r})"

    # No length or word-count threshold by design. A 2-word
    # scope-introducing prompt ("add OAuth") reaches the classifier;
    # the classifier decides whether it's new scope.
    return True, "qualifies for classification"


def parse_backlog_summary(project_root: Path) -> dict[str, Any]:
    """
    Build a compact backlog summary the classifier uses to distinguish
    "new scope" from "references existing work". Compact on purpose —
    the classifier prompt has a token budget too.

    Returns dict with:
      items: list of {id, outcome, status} (truncated to keep prompt small)
      total: int
      in_progress: list of item_ids
    """
    backlog_dir = project_root / ".cc-forge" / "backlog"
    items: list[dict[str, str]] = []
    in_progress: list[str] = []
    total = 0

    if not backlog_dir.is_dir():
        return {"items": items, "total": 0, "in_progress": in_progress,
                "note": ".cc-forge/backlog/ not initialised"}

    header = re.compile(r"^###\s+\[([A-Z][A-Z0-9-]+)\]\s*(.*)$")
    field = re.compile(r"^- ([A-Z][A-Za-z-]*):\s*(.+)$")

    for f in sorted(backlog_dir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
        except OSError:
            continue
        cur_id = None
        cur_outcome = ""
        cur_status = ""
        cur_title = ""
        for ln in text.split("\n"):
            h = header.match(ln)
            if h:
                # Finalise previous
                if cur_id:
                    total += 1
                    items.append({
                        "id": cur_id,
                        "outcome": cur_outcome or cur_title,
                        "status": cur_status or "unknown",
                    })
                    if cur_status == "in-progress":
                        in_progress.append(cur_id)
                cur_id = h.group(1)
                cur_title = h.group(2).strip()
                cur_outcome = ""
                cur_status = ""
                continue
            fm = field.match(ln)
            if fm and cur_id:
                if fm.group(1) == "Outcome":
                    cur_outcome = fm.group(2).strip()
                elif fm.group(1) == "Status":
                    cur_status = fm.group(2).strip()
        if cur_id:
            total += 1
            items.append({
                "id": cur_id,
                "outcome": cur_outcome or cur_title,
                "status": cur_status or "unknown",
            })
            if cur_status == "in-progress":
                in_progress.append(cur_id)

    return {"items": items, "total": total, "in_progress": in_progress}


# ─────────────────────────────────────────────────────────────────────
# Cache-mediated summary
# ─────────────────────────────────────────────────────────────────────

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))
try:
    from _hermes_cache import HermesCache  # type: ignore[no-redef]
except ImportError:
    HermesCache = None  # type: ignore[assignment]


def get_summary_cached(project_root: Path) -> dict[str, Any]:
    """
    Read backlog summary via the cache (§2.7) when available. The hook
    fires on every prompt; computing the summary every time without a
    cache is the slow path. Falls back to direct parse if cache module
    missing.
    """
    backlog_dir = project_root / ".cc-forge" / "backlog"
    cache_path = project_root / ".cc-forge" / "classifier-cache.json"
    sources = sorted(backlog_dir.glob("*.md")) if backlog_dir.is_dir() else []

    if HermesCache is None or not sources:
        return parse_backlog_summary(project_root)

    cache = HermesCache(cache_path)
    cached = cache.read_if_warm(sources)
    if cached is not None:
        return cached

    summary = parse_backlog_summary(project_root)
    try:
        cache.write(summary, source_files=sources)
    except OSError:
        pass
    return summary


# ─────────────────────────────────────────────────────────────────────
# Classifier — the model call
# ─────────────────────────────────────────────────────────────────────

# Compact prompt — the classifier only needs item IDs + outcomes + statuses,
# not full backlog text. Keep token cost minimal.
CLASSIFIER_SYSTEM_PROMPT = (
    "You are a binary classifier. Given a user message and a compact summary "
    "of an existing project backlog, decide whether the message introduces "
    "work that is NOT already represented in the backlog or in-flight tasks. "
    "Reply with ONLY a JSON object: "
    '{"introduces_new_scope": true|false, "confidence": 0.0-1.0, '
    '"reason": "one short sentence"}. '
    "Be conservative: if the message clearly references an existing item "
    "or its outcome (matching by ID, by outcome wording, or by topic), "
    "answer false. Treat tangential follow-ups ('also add OAuth', "
    "'while we're here, also...') as introducing new scope."
)


def classifier_user_prompt(prompt: str, summary: dict[str, Any]) -> str:
    """Compact user-side prompt with the backlog summary."""
    # Truncate items to keep the prompt small — the classifier sees enough
    # to recognise references, not the whole backlog.
    items = summary.get("items", [])[:30]
    lines = ["BACKLOG SUMMARY:"]
    if not items:
        lines.append("  (empty)")
    else:
        for it in items:
            lines.append(f"  - {it['id']} [{it['status']}] {it['outcome'][:80]}")
    in_progress = summary.get("in_progress", [])
    if in_progress:
        lines.append(f"IN-PROGRESS: {', '.join(in_progress[:10])}")
    lines.append("")
    lines.append("USER MESSAGE:")
    lines.append(prompt[:500])  # cap user prompt length too
    return "\n".join(lines)


def _ensure_isolated_classifier_cwd() -> Path:
    """Return a dedicated project-free cwd for the classifier's claude
    call. Created on first call, reused on subsequent calls. Uses a
    deterministic path under tempfile.gettempdir() so we don't leak
    dirs over a long-running session.

    The dir is explicitly empty of any .cc-forge/ — guarantees the
    `claude -p` call from this cwd sees no project, so there's no
    session-context recursion risk."""
    import tempfile
    path = Path(tempfile.gettempdir()) / "hermes-classifier-isolated"
    try:
        path.mkdir(exist_ok=True, parents=True)
    except OSError:
        # Fall back to system tempdir root; still better than the
        # caller's cwd, which IS a cc-forge project.
        return Path(tempfile.gettempdir())
    # Defensive: if someone managed to place a .cc-forge/ in our
    # isolated dir, remove the marker so claude doesn't see a project.
    marker = path / ".cc-forge"
    if marker.exists():
        try:
            import shutil
            shutil.rmtree(marker)
        except OSError:
            pass
    return path


def call_classifier(prompt: str, summary: dict[str, Any]) -> dict[str, Any]:
    """
    Returns dict with introduces_new_scope, confidence, reason, source.

    Stub override: HERMES_CLASSIFIER_STUB=<json> bypasses the model call
    and returns the JSON verbatim (used by behavioral tests so they can
    deterministically verify pipeline behavior without burning tokens).

    Real call: `claude --bare -p '<user_prompt>'` with --bare to avoid
    hook recursion. The classifier prompt is built and passed via stdin.
    """
    stub = os.environ.get("HERMES_CLASSIFIER_STUB")
    if stub:
        try:
            parsed = json.loads(stub)
            parsed["source"] = "stub"
            return parsed
        except json.JSONDecodeError:
            pass

    user_prompt = classifier_user_prompt(prompt, summary)
    # Compose a single message that includes the system framing inline —
    # `claude --bare -p` accepts a single prompt argument.
    full = f"{CLASSIFIER_SYSTEM_PROMPT}\n\n{user_prompt}"

    try:
        # Run `claude -p` from a dedicated isolated tempdir so the call
        # doesn't pick up an active session's context (which would cause
        # classifier-into-classifier recursion). Three robustness rules:
        #
        # 1. Don't reuse tempfile.gettempdir() directly — on the off-
        #    chance the user has a .cc-forge/ inside /tmp, that cwd
        #    would itself be a cc-forge project and the call would
        #    recurse. We use a dedicated subdir that we own.
        # 2. Create-on-first-call, cache, reuse. mkdtemp leaks dirs on
        #    crash; a deterministic path under /tmp is fine because
        #    the dir contains nothing — it's just a project-free cwd.
        # 3. Clear PWD env so any heuristics that look at PWD see the
        #    explicit tempdir, not the parent shell's cwd.
        #
        # Timeout: 15s. Haiku responses are typically 1-3s. 15s catches
        # cold-start + slow-network but doesn't pin the SessionStart
        # hook for too long. The classifier returning "error" on
        # timeout is safe — bypass is logged false, and the
        # deterministic backstop (C-1) catches misses retrospectively.
        isolated_cwd = _ensure_isolated_classifier_cwd()
        env = dict(os.environ)
        env["PWD"] = str(isolated_cwd)
        r = subprocess.run(
            ["claude", "-p", full],
            capture_output=True, text=True, timeout=15,
            cwd=str(isolated_cwd),
            env=env,
        )
        if r.returncode != 0:
            return {
                "introduces_new_scope": False,
                "confidence": 0.0,
                "reason": f"classifier call failed (exit {r.returncode})",
                "source": "error",
            }
        out = r.stdout.strip()
        # Extract first JSON object from the output (model may wrap with prose).
        m = re.search(r"\{.*?\}", out, re.DOTALL)
        if not m:
            return {
                "introduces_new_scope": False,
                "confidence": 0.0,
                "reason": "classifier returned no JSON",
                "source": "parse_error",
            }
        parsed = json.loads(m.group(0))
        parsed["source"] = "claude-bare"
        # Coerce types defensively.
        parsed["introduces_new_scope"] = bool(parsed.get("introduces_new_scope"))
        parsed["confidence"] = float(parsed.get("confidence", 0.0))
        return parsed
    except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError) as e:
        return {
            "introduces_new_scope": False,
            "confidence": 0.0,
            "reason": f"classifier error: {type(e).__name__}",
            "source": "error",
        }


def log_bypass_detected(project_root: Path, prompt: str, classifier_result: dict[str, Any]) -> None:
    """Append a bypass_detected event to usage.log per §3.6."""
    usage_log = project_root / ".cc-forge" / "usage.log"
    excerpt = prompt.strip().replace("\n", " ")[:160]
    entry = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "type": "bypass_detected",
        "data": {
            "prompt_excerpt": excerpt,
            "caught_by": "userpromptsubmit_classifier",
            "confidence": classifier_result.get("confidence", 0.0),
            "reason": classifier_result.get("reason", ""),
            "source": classifier_result.get("source", "unknown"),
        },
    }
    try:
        with usage_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def run_pipeline(prompt: str, project_root: Path) -> dict[str, Any]:
    """
    Full pipeline: pre-filter → (maybe) classify → (maybe) log + flag.

    Returns dict with:
      stage: "prefiltered" | "classified"
      bypass: bool
      classifier: result dict (only when classified)
      message: optional escalation framing text
    """
    should_classify, reason = prefilter(prompt)
    if not should_classify:
        return {"stage": "prefiltered", "bypass": False, "reason": reason}

    summary = get_summary_cached(project_root)
    result = call_classifier(prompt, summary)
    bypass = (result.get("introduces_new_scope", False)
              and result.get("confidence", 0.0) >= BYPASS_THRESHOLD)
    out: dict[str, Any] = {"stage": "classified", "bypass": bypass, "classifier": result}
    if bypass:
        log_bypass_detected(project_root, prompt, result)
        out["escalation_framing"] = (
            f"HERMES intake flag — the message above looks like new scope "
            f"(classifier confidence {result.get('confidence', 0):.2f}: "
            f"{result.get('reason', '')}). Before treating it as in-scope "
            f"work, surface it via /hermes-intake so it goes through "
            f"triage, classification, and persona consultation. If the "
            f"classifier is wrong (the work IS in scope or already a "
            f"backlog item), say so and reference the matching item."
        )
    return out


# ─────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Hermes intake-bypass classifier")
    sub = p.add_subparsers(dest="cmd", required=True)

    pf = sub.add_parser("prefilter", help="Run pre-filter only")
    pf.add_argument("--prompt", required=True)

    cls = sub.add_parser("classify", help="Run full pipeline (pre-filter + classifier)")
    cls.add_argument("--prompt", required=True)
    cls.add_argument("--project-root", default=".")

    sm = sub.add_parser("summary", help="Print backlog summary (cached)")
    sm.add_argument("--project-root", default=".")

    args = p.parse_args(argv)

    if args.cmd == "prefilter":
        ok, reason = prefilter(args.prompt)
        print(json.dumps({"should_classify": ok, "reason": reason}))
        return 0

    if args.cmd == "classify":
        result = run_pipeline(args.prompt, Path(args.project_root).resolve())
        print(json.dumps(result, indent=2))
        return 0

    if args.cmd == "summary":
        summary = get_summary_cached(Path(args.project_root).resolve())
        print(json.dumps(summary, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
