#!/usr/bin/env python3
"""hermes-argus.py — framework self-check (Argus, the watcher).

Argus is the deterministic counterpart to Hermes: Hermes directs the
session; Argus watches the framework. This script performs the §5
check catalogue: C-1 intake_reconciliation, format-violation
stratification per file/domain (E-1), banner-rendering approximate
caveat (E-3), and a freshness-checked cache for Layer-2 re-reads
(§2.7 / C-2).

Historical note: this code originally shipped under "hermes-doctor"
during the Doctor session. The function is the same; the name was
unified with the Argus persona (who was always meant to be the
framework-watcher) in Session E. The Argus persona file is at
`personas/argus.md`; the slash command is `/hermes-argus`.

Stdlib only. Two output modes: human (default), JSON (`--json`).

Exit code contract (versioned in the JSON schema; CI consumers must key
on all four — treating only one as failure mis-handles the rest):
  0  HEALTHY
  1  DEGRADED (advisories present, no failures)
  2  BROKEN (root resolved AND checks failed)
  3  CANNOT_LOCATE (root could not be located — distinct from BROKEN)
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

# Schema version — bump when the JSON output shape changes in a
# consumer-visible way. The shipped schema artifact at
# scripts/hermes-argus-output-schema.json must match this version.
SCHEMA_VERSION = "1.1.0"

# Durable run record — "Argus's memory" (§5.4). Path is fixed by DESIGN §4.4:
# project-root status/argus-last-run.md, the one operational artifact that is
# committed (not gitignored) so drift findings survive in history. Written on
# every run unless --no-record. This is the ONLY project file Argus writes
# besides its own freshness cache: Argus reports framework drift, it never
# mutates backlog state (.cc-forge/backlog/*.md) or state.json. The record is
# what the SessionStart staleness check reads to compute "Argus hasn't run in
# N sessions."
RUN_RECORD_REL = "status/argus-last-run.md"
# Machine-readable block embedded in the record so the next run can compute
# "what changed since last run" without re-parsing prose.
_RECORD_STATE_OPEN = "<!-- argus-machine-state: do not edit by hand"
_RECORD_STATE_CLOSE = "-->"

# Make the cache module importable when run from the plugin tree.
_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))
try:
    from _hermes_cache import HermesCache  # noqa: E402
except ImportError:  # pragma: no cover — degrades gracefully if module missing
    HermesCache = None  # type: ignore[assignment]

# Layer 1 (plugin) artifacts we expect to be reachable via CLAUDE_PLUGIN_ROOT.
LAYER1_EXPECTED = [
    ".claude-plugin/plugin.json",
    "hooks/hooks.json",
    "hooks/hermes-session-start.sh",
    "hooks/hermes-handoff.sh",
    "hooks/hermes-prompt-submit.sh",
    "token-weights.json",
    "HERMES.md",
    "catalogue/01-product.md",
    "catalogue/02-development.md",
    "catalogue/03-security.md",
    "catalogue/04-reliability.md",
    "catalogue/05-design.md",
    "catalogue/06-integrations.md",
    "catalogue/07-compliance.md",
    "catalogue/08-launch.md",
    "catalogue/09-growth.md",
    "catalogue/10-operations.md",
    "personas/_shared/backlog-update-protocol.md",
    "personas/_shared/phase-names.json",
    "personas/_shared/stage-names.json",
]

# Layer 2 (project state) artifacts.
LAYER2_EXPECTED = [
    ".cc-forge/state.json",
    ".cc-forge/usage.log",
]

# Layer 2 backlog domain files (presence-only here; format checks land in Doctor session).
LAYER2_BACKLOG_FILES = [f".cc-forge/backlog/{n}-*.md" for n in
                        ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]]


def resolve_plugin_root() -> tuple[Path | None, str, str | None]:
    """
    Resolve the plugin root via a cascade — env var first, then self-discovery.

    1. CLAUDE_PLUGIN_ROOT — if set AND it contains .claude-plugin/plugin.json.
       If set but invalid, fall through to discovery so a broken env var
       doesn't trap us.
    2. Walk up from this script's __file__ looking for a directory that
       contains .claude-plugin/plugin.json. Argus lives at
       <plugin_root>/scripts/hermes-argus.py so the parent of parent is
       the usual hit; we walk further as a safety margin.
    3. None — distinct "cannot locate" condition, NOT BROKEN. The caller
       reports this as its own verdict.

    Returns (root_path, source, note) where:
      source ∈ {"env", "self-discovered", "env-then-self", "not-found"}
      note   is a short human-readable explanation when relevant.

    Critical: the brief's #4 finding (forked Argus reports false BROKEN
    because CLAUDE_PLUGIN_ROOT doesn't survive the forked subshell) is
    closed by step 2 — Argus finds its own plugin root from __file__
    when the env var is missing, instead of declaring everything broken.
    """
    env_value = os.environ.get("CLAUDE_PLUGIN_ROOT")
    env_root: Path | None = None
    env_was_set_but_invalid = False

    if env_value:
        candidate = Path(env_value).resolve()
        if (candidate / ".claude-plugin" / "plugin.json").is_file():
            return candidate, "env", None
        env_was_set_but_invalid = True
        env_root = candidate  # Recorded for diagnostic, not authoritative.

    # Walk up from __file__. The script lives at <root>/scripts/hermes-argus.py;
    # parent.parent is the usual answer. Walk further for symlink / nested cases.
    here = Path(__file__).resolve()
    ancestors = [here.parent] + list(here.parents)
    for anc in ancestors:
        if (anc / ".claude-plugin" / "plugin.json").is_file():
            if env_was_set_but_invalid:
                note = (f"CLAUDE_PLUGIN_ROOT={env_root} did not contain "
                        f".claude-plugin/plugin.json — self-discovered "
                        f"plugin root from script location")
                return anc, "env-then-self", note
            return anc, "self-discovered", None

    # Cascade exhausted.
    if env_was_set_but_invalid:
        note = (f"CLAUDE_PLUGIN_ROOT={env_root} did not contain "
                f".claude-plugin/plugin.json and self-discovery from "
                f"{here} found no plugin root in any ancestor")
    else:
        note = (f"CLAUDE_PLUGIN_ROOT not set and self-discovery from "
                f"{here} found no .claude-plugin/plugin.json in any ancestor")
    return None, "not-found", note


def check_layer1(plugin_root: Path | None, root_source: str) -> tuple[list[dict[str, Any]], int]:
    """Return (checks, fail_count). Each check is {name, status, detail}."""
    checks: list[dict[str, Any]] = []
    fails = 0

    # The "cannot locate" condition is handled at the verdict level — it is
    # NOT a Layer-1 failure. If plugin_root is None we return no Layer-1
    # checks at all; the verdict logic in main() reports CANNOT_LOCATE.
    if plugin_root is None:
        return checks, fails

    if not plugin_root.is_dir():
        # Edge case: resolver returned a path that doesn't exist as a dir
        # (e.g. file deleted between resolution and check). Treat as fail.
        checks.append({"name": "plugin_root_exists", "status": "fail",
                       "detail": f"plugin root resolved but not a directory: {plugin_root}"})
        fails += 1
        return checks, fails

    checks.append({"name": "plugin_root_resolved", "status": "pass",
                   "detail": f"{plugin_root} (via {root_source})"})

    # Expected files present
    for rel in LAYER1_EXPECTED:
        full = plugin_root / rel
        if full.exists():
            checks.append({"name": f"layer1::{rel}", "status": "pass",
                           "detail": str(full)})
        else:
            checks.append({"name": f"layer1::{rel}", "status": "fail",
                           "detail": f"missing: {full}"})
            fails += 1

    return checks, fails


def check_layer2(project_root: Path) -> tuple[list[dict[str, Any]], int, int]:
    """Return (checks, fail_count, advisory_count)."""
    checks: list[dict[str, Any]] = []
    fails = 0
    advisories = 0

    # Required state files
    for rel in LAYER2_EXPECTED:
        full = project_root / rel
        if full.exists():
            checks.append({"name": f"layer2::{rel}", "status": "pass",
                           "detail": str(full)})
        else:
            checks.append({"name": f"layer2::{rel}", "status": "fail",
                           "detail": f"missing: {full}"})
            fails += 1

    # state.json parseable
    state_path = project_root / ".cc-forge" / "state.json"
    if state_path.is_file():
        try:
            json.loads(state_path.read_text(encoding="utf-8"))
            checks.append({"name": "state.json_valid", "status": "pass",
                           "detail": "parses as JSON"})
        except (json.JSONDecodeError, OSError) as e:
            checks.append({"name": "state.json_valid", "status": "fail",
                           "detail": f"parse error: {e}"})
            fails += 1

    # Backlog domain files — count rather than enumerate (glob)
    backlog_dir = project_root / ".cc-forge" / "backlog"
    if backlog_dir.is_dir():
        domain_files = sorted(backlog_dir.glob("0*.md")) + sorted(backlog_dir.glob("1*.md"))
        if len(domain_files) == 10:
            checks.append({"name": "layer2::backlog::10_domains", "status": "pass",
                           "detail": f"{len(domain_files)} domain files"})
        else:
            checks.append({"name": "layer2::backlog::10_domains", "status": "advisory",
                           "detail": f"found {len(domain_files)} domain files (expected 10)"})
            advisories += 1
    else:
        checks.append({"name": "layer2::backlog::10_domains", "status": "advisory",
                       "detail": ".cc-forge/backlog/ not initialised — run /hermes-backlog-init"})
        advisories += 1

    return checks, fails, advisories


# ─────────────────────────────────────────────────────────────────────────────
# Phase-B checks: C-1 intake_reconciliation, format violations, drift,
# banner-rendering (approximate).
# ─────────────────────────────────────────────────────────────────────────────


# Spec §3.2 list-item field regex. Single canonical form; strict per §3.8.
FIELD_PATTERN = re.compile(r"^- ([A-Z][A-Za-z-]*):\s*(.+)$")
ITEM_HEADER_PATTERN = re.compile(r"^### \[([A-Z][A-Z0-9-]+)\]")
# Required fields per §3.2. Standard is grandfathered per §3.2 line 644 for
# one transition cycle — Argus lists missing-Standard separately from
# the other required-field gaps to preserve the spec's bucketing.
REQUIRED_FIELDS = {"Outcome", "Standard", "Phase", "Status", "Owner", "Evidence"}
GRANDFATHERED_FIELD = "Standard"


def parse_backlog_items_strict(text: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Run the spec §3.2 strict parser over a backlog/catalogue file.

    Returns (items, violations) where each violation is one of:
      {"kind": "field_not_recognised", "line": int, "text": str}
      {"kind": "required_field_missing", "id": str, "field": str,
       "grandfathered": bool}
      {"kind": "no_items", ...}

    Crucially: this is the parser-strict-fail surface §3.8 names. Every
    violation it emits feeds the E-1 stratified format-violation report.
    """
    items: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []

    cur_id: str | None = None
    cur_fields: dict[str, str] = {}
    cur_line_start = 0

    def finalise_current(end_line: int) -> None:
        nonlocal cur_id, cur_fields
        if cur_id is None:
            return
        # Check required fields
        for required in REQUIRED_FIELDS:
            if required not in cur_fields:
                violations.append({
                    "kind": "required_field_missing",
                    "id": cur_id,
                    "field": required,
                    "grandfathered": required == GRANDFATHERED_FIELD,
                })
        items.append({"id": cur_id, "fields": dict(cur_fields),
                      "line_start": cur_line_start, "line_end": end_line})
        cur_id = None
        cur_fields = {}

    for ln_idx, line in enumerate(text.split("\n"), start=1):
        header = ITEM_HEADER_PATTERN.match(line)
        if header:
            finalise_current(ln_idx - 1)
            cur_id = header.group(1)
            cur_line_start = ln_idx
            continue
        if cur_id is None:
            # Not inside an item block — only validate field-syntax lines
            # that look field-like (start with "- " and a capital).
            continue
        if not line.strip():
            continue
        # Lines beginning with "- " inside an item block must match the field
        # pattern. Anything else (sub-bullet, prose) is allowed without flag.
        if line.startswith("- ") and re.match(r"^- [A-Z]", line):
            fm = FIELD_PATTERN.match(line)
            if fm:
                cur_fields[fm.group(1)] = fm.group(2).strip()
            else:
                violations.append({
                    "kind": "field_not_recognised",
                    "line": ln_idx,
                    "text": line,
                })
    finalise_current(len(text.split("\n")))

    if not items and "### [" in text:
        violations.append({
            "kind": "no_items",
            "detail": "file contains '### [' headers but parser extracted zero items",
        })

    return items, violations


def check_catalogue_format(project_root: Path) -> tuple[list[dict[str, Any]], int, int, list[dict[str, Any]]]:
    """
    Per-file format check over .cc-forge/backlog/*.md. Returns:
      (checks, fail_count, advisory_count, raw_violations_per_file)

    raw_violations_per_file feeds E-1's stratification. The check itself is
    a single advisory if any non-grandfathered violations exist (we don't
    halt Argus — see §3.8 strict-but-not-blocking for Layer 2 data).
    """
    checks: list[dict[str, Any]] = []
    fails = 0
    advisories = 0
    per_file_violations: list[dict[str, Any]] = []

    backlog_dir = project_root / ".cc-forge" / "backlog"
    if not backlog_dir.is_dir():
        # Absence handled by check_layer2 — don't double-report.
        return checks, fails, advisories, per_file_violations

    domain_files = sorted(backlog_dir.glob("*.md"))
    if not domain_files:
        return checks, fails, advisories, per_file_violations

    total_items = 0
    total_violations = 0
    files_with_violations = 0

    for f in domain_files:
        try:
            text = f.read_text(encoding="utf-8")
        except OSError as e:
            checks.append({"name": f"format::{f.name}", "status": "fail",
                           "detail": f"unreadable: {e}"})
            fails += 1
            continue

        items, violations = parse_backlog_items_strict(text)
        total_items += len(items)
        total_violations += len(violations)
        domain = f.stem  # e.g. "03-security"

        per_file_violations.append({
            "file": str(f.relative_to(project_root)),
            "domain": domain,
            "items": len(items),
            "violations": violations,
            "non_grandfathered_count": sum(
                1 for v in violations
                if not (v.get("kind") == "required_field_missing" and v.get("grandfathered"))
            ),
        })
        if violations:
            files_with_violations += 1

    if total_violations == 0:
        checks.append({"name": "format::all_catalogue_items", "status": "pass",
                       "detail": f"{total_items} items parsed cleanly across {len(domain_files)} files"})
    else:
        non_grand = sum(p["non_grandfathered_count"] for p in per_file_violations)
        if non_grand > 0:
            advisories += 1
            checks.append({"name": "format::catalogue_violations", "status": "advisory",
                           "detail": f"{non_grand} non-grandfathered violations across "
                                     f"{files_with_violations} files (see stratified drift report)"})
        else:
            # Everything that violated was Standard-grandfathered — pass with note.
            checks.append({"name": "format::catalogue_violations", "status": "pass",
                           "detail": f"{total_violations} grandfathered violations (missing Standard, "
                                     f"§3.2 line 644); zero non-grandfathered."})

    return checks, fails, advisories, per_file_violations


def check_intake_reconciliation(project_root: Path) -> tuple[list[dict[str, Any]], int, int, list[dict[str, Any]]]:
    """
    C-1: backlog events in usage.log with no matching intake_step.

    Deterministic backstop for the probabilistic intake classifier (Session
    D). Reports zero until intake events actually flow — that's correct;
    the check ships working and quiet, ready to catch when there's
    something to catch.

    Algorithm:
      - Walk usage.log. Collect set of item_ids that ever appeared as
        intake_step events (intake_id field if present, item_id if present).
      - For each backlog event with an item_id: if that item_id never
        appeared as an intake_step, flag it as unintaken.

    A future refinement (Session D): also check whether the item existed
    in the backlog *before* the event (pre-existing items are exempt — they
    were in the original catalogue). v1 is the simpler item_id-matching
    check; that's enough to catch the gap the brief targets.

    Returns: (checks, fail_count, advisory_count, raw_unmatched_events)
    """
    checks: list[dict[str, Any]] = []
    fails = 0
    advisories = 0
    unmatched: list[dict[str, Any]] = []

    usage_log = project_root / ".cc-forge" / "usage.log"
    if not usage_log.is_file():
        # No log → no possible reconciliation events. Pass quietly.
        checks.append({"name": "intake_reconciliation", "status": "pass",
                       "detail": "no usage.log to scan (nothing to reconcile)"})
        return checks, fails, advisories, unmatched

    intake_seen_ids: set[str] = set()
    backlog_events: list[dict[str, Any]] = []

    try:
        with usage_log.open(encoding="utf-8") as fh:
            for ln_idx, raw_line in enumerate(fh, start=1):
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue  # Malformed lines are out of scope here.
                if not isinstance(entry, dict):
                    continue
                etype = entry.get("type")
                data = entry.get("data") or {}
                if etype == "intake_step":
                    # Collect any identifier the intake step may reference.
                    for k in ("item_id", "intake_id", "id"):
                        v = data.get(k)
                        if isinstance(v, str):
                            intake_seen_ids.add(v)
                elif etype == "backlog":
                    item_id = data.get("item_id")
                    if isinstance(item_id, str):
                        backlog_events.append({
                            "line": ln_idx, "ts": entry.get("ts"), "item_id": item_id
                        })
    except OSError as e:
        checks.append({"name": "intake_reconciliation", "status": "fail",
                       "detail": f"usage.log unreadable: {e}"})
        return checks, 1, advisories, unmatched

    for ev in backlog_events:
        if ev["item_id"] not in intake_seen_ids:
            unmatched.append(ev)

    if not backlog_events:
        checks.append({"name": "intake_reconciliation", "status": "pass",
                       "detail": "no backlog events recorded (nothing to reconcile)"})
    elif not unmatched:
        checks.append({"name": "intake_reconciliation", "status": "pass",
                       "detail": f"{len(backlog_events)} backlog events all matched to intake_step"})
    else:
        advisories += 1
        # Cap the detail line; full list goes into raw_unmatched_events for JSON.
        sample_ids = sorted({u["item_id"] for u in unmatched})[:5]
        checks.append({"name": "intake_reconciliation", "status": "advisory",
                       "detail": f"{len(unmatched)} backlog event(s) with no matching intake_step "
                                 f"(e.g. {', '.join(sample_ids)}). See drift report."})

    return checks, fails, advisories, unmatched


def check_banner_rendering(project_root: Path) -> tuple[list[dict[str, Any]], int, int, dict[str, Any]]:
    """
    E-3: banner-rendering check — approximate.

    Honest about methodology: we can measure whether the SessionStart hook
    fired successfully (logged session_start) vs whether it fell back to
    the minimal banner (logged subset_check_timeout). We CANNOT measure
    whether the model actually rendered the hook's output (that would
    require transcript inspection cc-forge doesn't have). So the rate this
    check reports is the rate of HOOK SUCCESS, not model render success.

    The brief: 'The banner-rendering check (the one fuzzy, non-deterministic
    check) reports its rate as approximate; every other check is a definite
    pass/fail.' This is the one labeled approximate.

    Stratified by session-start source (startup/resume/clear/compact) when
    the hook records it — feeds E-1.

    Returns: (checks, fail_count, advisory_count, raw_per_source_stats)
    """
    checks: list[dict[str, Any]] = []
    fails = 0
    advisories = 0
    per_source: dict[str, dict[str, int]] = {}

    usage_log = project_root / ".cc-forge" / "usage.log"
    if not usage_log.is_file():
        checks.append({"name": "banner_rendering", "status": "pass",
                       "detail": "no usage.log to scan (approximate; no data yet)"})
        return checks, fails, advisories, {"per_source": per_source}

    total_starts = 0
    total_timeouts = 0
    try:
        with usage_log.open(encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                etype = entry.get("type")
                if etype not in ("session_start", "subset_check_timeout"):
                    continue
                data = entry.get("data") or {}
                source = data.get("source") if isinstance(data, dict) else None
                if not isinstance(source, str):
                    source = "unknown"
                bucket = per_source.setdefault(source, {"started": 0, "timeout": 0})
                if etype == "session_start":
                    total_starts += 1
                    bucket["started"] += 1
                else:
                    total_timeouts += 1
                    bucket["timeout"] += 1
    except OSError as e:
        checks.append({"name": "banner_rendering", "status": "fail",
                       "detail": f"usage.log unreadable: {e}"})
        return checks, 1, advisories, {"per_source": per_source}

    if total_starts == 0 and total_timeouts == 0:
        checks.append({"name": "banner_rendering", "status": "pass",
                       "detail": "approximate — no session-start events recorded yet"})
        return checks, fails, advisories, {"per_source": per_source}

    total = total_starts + total_timeouts
    rate = round(total_starts / total * 100) if total else 0
    # Threshold: if timeouts are >20% of starts, surface an advisory. The
    # value of this is "is the hook routinely failing fast?", not "did the
    # model render the banner verbatim?" — different question.
    if total_timeouts > 0 and total_timeouts / total >= 0.2:
        advisories += 1
        checks.append({"name": "banner_rendering", "status": "advisory",
                       "detail": f"approximate — {rate}% hook success rate "
                                 f"({total_starts} ok / {total_timeouts} timeout); investigate"})
    else:
        checks.append({"name": "banner_rendering", "status": "pass",
                       "detail": f"approximate — {rate}% hook success rate "
                                 f"({total_starts} ok / {total_timeouts} timeout)"})

    return checks, fails, advisories, {
        "per_source": per_source,
        "total_starts": total_starts,
        "total_timeouts": total_timeouts,
        "rate_approximate": rate,
        "methodology_note": "rate measures SessionStart hook success vs timeout — "
                            "NOT model render verification (transcript inspection unavailable)",
    }


def compute_drift_summary(format_violations: list[dict[str, Any]],
                          unmatched_intake: list[dict[str, Any]],
                          banner_rendering: dict[str, Any]) -> dict[str, Any]:
    """
    E-1: stratified drift report.

    Two stratifications carried as separate keys (not a generic 'drift'
    bucket):
      - format_violations_by_file_and_domain
      - banner_misses_by_source

    Plus a third aggregate-only bucket for low-volume drift the brief
    explicitly says NOT to stratify (orphan_task, missing_coverage,
    bypass_detected, standards_strip_detected, etc.) — those land in
    'low_volume_aggregate' from usage.log so consumers see them but no
    arbitrary segmentation.
    """
    # Format violations, stratified by file and domain
    per_file = []
    for entry in format_violations:
        if entry.get("non_grandfathered_count", 0) == 0 and not entry.get("violations"):
            continue
        per_file.append({
            "file": entry["file"],
            "domain": entry.get("domain"),
            "items_parsed": entry["items"],
            "violations_total": len(entry["violations"]),
            "violations_non_grandfathered": entry["non_grandfathered_count"],
            "violations_grandfathered": (
                len(entry["violations"]) - entry["non_grandfathered_count"]
            ),
        })

    banner_per_source = banner_rendering.get("per_source", {}) if banner_rendering else {}

    return {
        "format_violations_by_file_and_domain": per_file,
        "banner_misses_by_source": banner_per_source,
        "intake_reconciliation_unmatched": unmatched_intake,
        # Counts of low-volume drift events from usage.log (not stratified
        # arbitrarily; the brief explicitly excludes these from segmentation).
        # Populated by main() reading usage.log once.
        "low_volume_aggregate": {},
    }


def count_low_volume_drift(project_root: Path) -> dict[str, int]:
    """Counts of low-volume drift event types from usage.log. Brief calls
    out NOT stratifying these — aggregate only."""
    counts = {
        "orphan_task": 0,
        "missing_coverage": 0,
        "bypass_detected": 0,
        "standards_strip_detected": 0,
    }
    usage_log = project_root / ".cc-forge" / "usage.log"
    if not usage_log.is_file():
        return counts
    try:
        with usage_log.open(encoding="utf-8") as fh:
            for raw_line in fh:
                line = raw_line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(entry, dict):
                    continue
                etype = entry.get("type")
                if etype in counts:
                    counts[etype] += 1
    except OSError:
        pass
    return counts


def compute_verdict(plugin_root: Path | None,
                    l1_fails: int, l2_fails: int, l2_advisories: int) -> str:
    """
    Distinct verdicts:
      HEALTHY        — all checks pass, no advisories.
      DEGRADED       — advisories present, no failures.
      BROKEN         — at least one check failed and root was resolvable.
      CANNOT_LOCATE  — plugin root could not be located (env not set AND
                       self-discovery missed). NOT BROKEN: we don't know
                       whether Layer 1 is broken; we couldn't even find it.
    """
    if plugin_root is None:
        return "CANNOT_LOCATE"
    if l1_fails + l2_fails > 0:
        return "BROKEN"
    if l2_advisories > 0:
        return "DEGRADED"
    return "HEALTHY"


def render_human(plugin_root: Path | None, root_source: str, root_note: str | None,
                 project_root: Path,
                 l1_checks: list[dict[str, Any]], l1_fails: int,
                 l2_checks: list[dict[str, Any]], l2_fails: int, l2_advisories: int,
                 drift: dict[str, Any],
                 cache_state: dict[str, Any] | None) -> str:
    """Render the §5.2 banner."""
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    name = project_root.name
    out: list[str] = []
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"  HERMES-ARGUS · {name} · {ts}")
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if plugin_root is None:
        out.append("  Plugin root: CANNOT LOCATE")
        out.append(f"      {root_note}")
        out.append("      Layer 1 checks skipped — root not discoverable.")
    else:
        out.append(f"  Plugin root: {plugin_root}")
        out.append(f"      resolved via: {root_source}"
                   + (f" — {root_note}" if root_note else ""))
        out.append("  Layer 1 — Plugin (framework primitives)")
        for c in l1_checks:
            glyph = {"pass": "✓", "fail": "✗", "advisory": "⚠"}.get(c["status"], "?")
            out.append(f"    {glyph} {c['name']}")
            if c["status"] != "pass":
                out.append(f"        {c['detail']}")

    out.append("  Layer 2 — Project state (machine-managed)")
    for c in l2_checks:
        glyph = {"pass": "✓", "fail": "✗", "advisory": "⚠"}.get(c["status"], "?")
        out.append(f"    {glyph} {c['name']}")
        if c["status"] != "pass":
            out.append(f"        {c['detail']}")

    # Stratified drift report (E-1)
    out.append("  Drift summary (stratified per E-1)")
    fv = drift.get("format_violations_by_file_and_domain", [])
    if fv:
        out.append(f"    Format violations by file/domain ({sum(p['violations_total'] for p in fv)} total):")
        for entry in fv:
            non = entry["violations_non_grandfathered"]
            grand = entry["violations_grandfathered"]
            note = ""
            if grand and not non:
                note = " (all grandfathered per §3.2)"
            out.append(f"      · {entry['file']}: {non} non-grandfathered, {grand} grandfathered{note}")
    else:
        out.append("    Format violations: 0")
    bm = drift.get("banner_misses_by_source", {})
    if bm:
        out.append("    Banner-miss by session-start source (approximate — see banner_rendering check):")
        for source, counts in sorted(bm.items()):
            total = counts["started"] + counts["timeout"]
            out.append(f"      · {source}: {counts['started']}/{total} ok, {counts['timeout']} timeout")
    else:
        out.append("    Banner-miss by source: no session-start events yet")
    lva = drift.get("low_volume_aggregate", {})
    if lva:
        nonzero = {k: v for k, v in lva.items() if v}
        if nonzero:
            out.append(f"    Low-volume drift (aggregate, not stratified): {nonzero}")
        else:
            out.append("    Low-volume drift (aggregate): 0 of each kind")

    if cache_state is not None:
        out.append("  Layer-2 cache (freshness-checked read per §2.7)")
        if cache_state.get("used"):
            warm = cache_state.get("warm")
            if warm:
                out.append(f"    ✓ warm cache served (mtime match on all sources)")
            else:
                out.append(f"    · cold/stale → recomputed and refreshed cache")
                if cache_state.get("stale_sources"):
                    out.append(f"      stale sources: {', '.join(cache_state['stale_sources'])}")
        else:
            out.append("    · cache disabled or module unavailable")

    verdict = compute_verdict(plugin_root, l1_fails, l2_fails, l2_advisories)
    suffix = ""
    if verdict == "DEGRADED":
        suffix = f" with {l2_advisories} advisor{'y' if l2_advisories == 1 else 'ies'}"
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"  Overall: {verdict}{suffix}")
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out.append("")
    out.append("  Note: 'approximate' on the banner-rendering check reflects that we measure")
    out.append("        SessionStart hook success, not model render verification. Every other")
    out.append("        check is a definite pass/fail.")
    return "\n".join(out)


# JSON Schema artifact URL — versioned alongside Argus. Consumers can
# fetch the schema and validate the output's shape.
SCHEMA_URL = (
    "https://raw.githubusercontent.com/A-Director/cc-forge/main/"
    "scripts/hermes-argus-output-schema.json"
)


def render_json(plugin_root: Path | None, root_source: str, root_note: str | None,
                project_root: Path,
                l1_checks: list[dict[str, Any]], l1_fails: int,
                l2_checks: list[dict[str, Any]], l2_fails: int, l2_advisories: int,
                drift: dict[str, Any],
                cache_state: dict[str, Any] | None) -> str:
    """Render the versioned JSON output (E-2). Conforms to the schema at
    scripts/hermes-argus-output-schema.json — fetchable via the $schema
    URL embedded in the payload.

    Schema covers (per Phase B carryforward): CANNOT_LOCATE verdict, exit
    codes 0/1/2/3, plugin_root_source, plugin_root_note, drift
    stratifications, cache_state."""
    verdict = compute_verdict(plugin_root, l1_fails, l2_fails, l2_advisories)
    exit_code = {"HEALTHY": 0, "DEGRADED": 1, "BROKEN": 2, "CANNOT_LOCATE": 3}[verdict]
    payload = {
        "$schema": SCHEMA_URL,
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "project_root": str(project_root),
        "plugin_root": str(plugin_root) if plugin_root else None,
        "plugin_root_source": root_source,
        "plugin_root_note": root_note,
        "checks": {
            "layer1": l1_checks,
            "layer2": l2_checks,
        },
        "drift": drift,
        "cache_state": cache_state,
        "summary": {
            "verdict": verdict,
            "exit_code": exit_code,
            "failures": l1_fails + l2_fails,
            "advisories": l2_advisories,
        },
    }
    return json.dumps(payload, indent=2)


def _layer2_source_files(project_root: Path) -> list[Path]:
    """Source files the cache tracks for freshness. Caller-side, so we can
    pass the same list to read_if_warm and write."""
    backlog_dir = project_root / ".cc-forge" / "backlog"
    sources = [
        project_root / ".cc-forge" / "state.json",
        project_root / ".cc-forge" / "usage.log",
        project_root / "RISKS.md",
    ]
    if backlog_dir.is_dir():
        sources.extend(sorted(backlog_dir.glob("*.md")))
    return sources


def _drift_counts(drift: dict[str, Any]) -> dict[str, Any]:
    """Reduce the drift summary to the scalar counts the record tracks for
    'what changed since last run'. Framework-drift kinds only — Argus does
    not measure code-vs-plan drift (that is the personas' job at gate
    reviews, §5)."""
    fv = drift.get("format_violations_by_file_and_domain", []) or []
    bm = drift.get("banner_misses_by_source", {}) or {}
    return {
        "format_non_grandfathered": sum(e.get("violations_non_grandfathered", 0) for e in fv),
        "intake_unmatched": len(drift.get("intake_reconciliation_unmatched", []) or []),
        "banner_timeouts": sum(c.get("timeout", 0) for c in bm.values()),
        "low_volume_aggregate": dict(drift.get("low_volume_aggregate", {}) or {}),
    }


def _read_prior_record_state(record_path: Path) -> dict[str, Any] | None:
    """Parse the machine-state block of an existing run record, if any.
    Returns None when there's no prior record or it can't be parsed — the
    record write then notes 'first recorded run'."""
    if not record_path.is_file():
        return None
    try:
        text = record_path.read_text(encoding="utf-8")
    except OSError:
        return None
    start = text.find(_RECORD_STATE_OPEN)
    if start == -1:
        return None
    start += len(_RECORD_STATE_OPEN)
    end = text.find(_RECORD_STATE_CLOSE, start)
    if end == -1:
        return None
    try:
        parsed = json.loads(text[start:end].strip())
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        return None


def _compute_changes(prior: dict[str, Any] | None,
                     verdict: str, failures: int, advisories: int,
                     dc: dict[str, Any]) -> list[str]:
    """Human-readable 'what changed since last run' lines."""
    if prior is None:
        return ["First recorded run — no prior baseline to compare against."]
    lines: list[str] = []
    if prior.get("verdict") != verdict:
        lines.append(f"Verdict: {prior.get('verdict', '?')} → {verdict}")
    if prior.get("failures") != failures:
        lines.append(f"Failures: {prior.get('failures', '?')} → {failures}")
    if prior.get("advisories") != advisories:
        lines.append(f"Advisories: {prior.get('advisories', '?')} → {advisories}")
    pdc = prior.get("drift_counts", {}) if isinstance(prior.get("drift_counts"), dict) else {}
    for key, label in (("format_non_grandfathered", "Format violations (non-grandfathered)"),
                       ("intake_unmatched", "Intake-unmatched backlog events"),
                       ("banner_timeouts", "SessionStart hook timeouts")):
        before, after = pdc.get(key), dc.get(key)
        if before != after:
            lines.append(f"{label}: {before if before is not None else '?'} → {after}")
    pl = pdc.get("low_volume_aggregate", {}) if isinstance(pdc.get("low_volume_aggregate"), dict) else {}
    cl = dc.get("low_volume_aggregate", {})
    for key in sorted(set(pl) | set(cl)):
        before, after = pl.get(key, 0), cl.get(key, 0)
        if before != after:
            lines.append(f"Drift '{key}': {before} → {after}")
    if not lines:
        lines.append("No change since last run — same verdict, same drift counts.")
    return lines


def write_run_record(project_root: Path, verdict: str, exit_code: int,
                     failures: int, advisories: int, trigger: str,
                     drift: dict[str, Any], plugin_root: Path | None,
                     root_source: str) -> Path | None:
    """Write Argus's durable run record to status/argus-last-run.md (§4.4).

    The ONLY project file Argus mutates besides its freshness cache. Never
    touches backlog state or state.json. Failures are swallowed — a record
    write that fails must never change Argus's verdict or exit code.
    """
    record_path = project_root / RUN_RECORD_REL
    ran_at = dt.datetime.now(dt.timezone.utc).isoformat()
    dc = _drift_counts(drift)
    prior = _read_prior_record_state(record_path)
    changes = _compute_changes(prior, verdict, failures, advisories, dc)

    machine_state = {
        "ran_at": ran_at,
        "verdict": verdict,
        "exit_code": exit_code,
        "failures": failures,
        "advisories": advisories,
        "trigger": trigger,
        "plugin_root": str(plugin_root) if plugin_root else None,
        "plugin_root_source": root_source,
        "drift_counts": dc,
        "schema_version": SCHEMA_VERSION,
    }

    lines = [
        "# Argus — last run",
        "",
        "_Machine-managed by `hermes-argus.py` (Argus's memory). Do not hand-edit._",
        "",
        f"- Ran at: {ran_at}",
        f"- Trigger: {trigger}",
        f"- Verdict: {verdict} (exit {exit_code})",
        f"- Failures: {failures} · Advisories: {advisories}",
        f"- Plugin root: {plugin_root if plugin_root else 'CANNOT_LOCATE'} (via {root_source})",
        "",
        "## What changed since last run",
        "",
    ]
    lines += [f"- {c}" for c in changes]
    lines += [
        "",
        "## Drift snapshot (framework-drift only)",
        "",
        f"- Format violations (non-grandfathered): {dc['format_non_grandfathered']}",
        f"- Intake-unmatched backlog events: {dc['intake_unmatched']}",
        f"- SessionStart hook timeouts: {dc['banner_timeouts']}",
        f"- Low-volume drift: {dc['low_volume_aggregate']}",
        "",
        _RECORD_STATE_OPEN,
        json.dumps(machine_state, indent=2),
        _RECORD_STATE_CLOSE,
        "",
    ]

    try:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        record_path.write_text("\n".join(lines), encoding="utf-8")
        return record_path
    except OSError:
        return None


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="cc-forge framework self-check")
    p.add_argument("--project-root", default=".", help="Project root (default: cwd)")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of banner")
    p.add_argument("--no-cache", action="store_true",
                   help="Skip the freshness-checked Layer-2 cache; always recompute")
    p.add_argument("--no-record", action="store_true",
                   help="Skip writing the durable run record at "
                        "status/argus-last-run.md (Argus's memory)")
    p.add_argument("--trigger", default="manual",
                   help="What invoked this run (recorded in the run record): "
                        "e.g. 'manual', 'session-close'")
    args = p.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    plugin_root, root_source, root_note = resolve_plugin_root()

    l1_checks, l1_fails = check_layer1(plugin_root, root_source)

    # ─── Cache-mediated Layer-2 read (§2.7) ─────────────────────────
    # The cache stores the COMPUTED Layer-2 check output, keyed by source-
    # file mtimes. A warm cache means: no source has changed, so the
    # cached check results are still valid. Stale → recompute and refresh.
    cache_state: dict[str, Any] | None = None
    l2_checks: list[dict[str, Any]] = []
    l2_fails = 0
    l2_advisories = 0
    format_per_file_violations: list[dict[str, Any]] = []
    unmatched_intake: list[dict[str, Any]] = []
    banner_rendering_raw: dict[str, Any] = {}

    use_cache = (HermesCache is not None) and (not args.no_cache)
    cache_path = project_root / ".cc-forge" / "cache.json"
    sources = _layer2_source_files(project_root)
    cached_payload: dict[str, Any] | None = None
    cache_obj: Any = None

    if use_cache:
        cache_obj = HermesCache(cache_path)
        cached_payload = cache_obj.read_if_warm(sources)

    if cached_payload is not None:
        # Warm: rehydrate Layer-2 check outputs from the cache.
        l2_checks = cached_payload.get("l2_checks", [])
        l2_fails = cached_payload.get("l2_fails", 0)
        l2_advisories = cached_payload.get("l2_advisories", 0)
        format_per_file_violations = cached_payload.get("format_per_file_violations", [])
        unmatched_intake = cached_payload.get("unmatched_intake", [])
        banner_rendering_raw = cached_payload.get("banner_rendering_raw", {})
        cache_state = {"used": True, "warm": True, "path": str(cache_path)}
    else:
        # Cold or stale: recompute Layer 2 + new checks, then refresh cache.
        l2_checks, l2_fails, l2_advisories = check_layer2(project_root)
        fmt_checks, fmt_fails, fmt_advisories, format_per_file_violations = \
            check_catalogue_format(project_root)
        l2_checks.extend(fmt_checks); l2_fails += fmt_fails; l2_advisories += fmt_advisories

        intake_checks, intake_fails, intake_advisories, unmatched_intake = \
            check_intake_reconciliation(project_root)
        l2_checks.extend(intake_checks); l2_fails += intake_fails; l2_advisories += intake_advisories

        banner_checks, banner_fails, banner_advisories, banner_rendering_raw = \
            check_banner_rendering(project_root)
        l2_checks.extend(banner_checks); l2_fails += banner_fails; l2_advisories += banner_advisories

        if use_cache and cache_obj is not None:
            try:
                report = cache_obj.staleness_report(sources)
                cache_obj.write({
                    "l2_checks": l2_checks,
                    "l2_fails": l2_fails,
                    "l2_advisories": l2_advisories,
                    "format_per_file_violations": format_per_file_violations,
                    "unmatched_intake": unmatched_intake,
                    "banner_rendering_raw": banner_rendering_raw,
                }, source_files=sources)
                cache_state = {
                    "used": True, "warm": False, "path": str(cache_path),
                    "stale_sources": report.get("stale_sources", []),
                }
            except OSError as e:
                cache_state = {"used": True, "warm": False, "error": str(e)}
        else:
            cache_state = {"used": False, "warm": False,
                           "reason": "module unavailable" if HermesCache is None else "--no-cache"}

    # Drift summary (E-1) and low-volume aggregate (always recomputed —
    # usage.log changes frequently and the count is cheap).
    drift = compute_drift_summary(format_per_file_violations,
                                  unmatched_intake, banner_rendering_raw)
    drift["low_volume_aggregate"] = count_low_volume_drift(project_root)

    if args.json:
        print(render_json(plugin_root, root_source, root_note, project_root,
                          l1_checks, l1_fails, l2_checks, l2_fails, l2_advisories,
                          drift, cache_state))
    else:
        print(render_human(plugin_root, root_source, root_note, project_root,
                           l1_checks, l1_fails, l2_checks, l2_fails, l2_advisories,
                           drift, cache_state))

    verdict = compute_verdict(plugin_root, l1_fails, l2_fails, l2_advisories)
    # Exit codes:
    #   0  HEALTHY
    #   1  DEGRADED
    #   2  BROKEN
    #   3  CANNOT_LOCATE (distinct from BROKEN — we couldn't find the
    #                    plugin to check it; not a Layer-1 failure verdict)
    exit_code = {"HEALTHY": 0, "DEGRADED": 1, "BROKEN": 2, "CANNOT_LOCATE": 3}[verdict]

    # Durable run record (§5.4) — Argus's memory. Written on every run unless
    # --no-record. Wrapped so a write failure never changes the verdict/exit.
    if not args.no_record:
        write_run_record(project_root, verdict, exit_code,
                         l1_fails + l2_fails, l2_advisories, args.trigger,
                         drift, plugin_root, root_source)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
