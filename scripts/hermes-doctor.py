#!/usr/bin/env python3
"""hermes-doctor.py — framework self-check (skeleton).

v1.0.0 (Session 0): Layer-1 + Layer-2 file-existence checks only. Grows in
the Doctor session into the full §5.3 check catalogue (format-violation
stratification, cache freshness, banner-rendering caveat, intake
reconciliation, etc.).

Stdlib only. Two output modes: human (default), JSON (`--json`). Exit
codes per §5.6: 0 HEALTHY, 1 DEGRADED (advisories), 2 BROKEN (failures).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0.0"  # versioned per spec §5.6 / cross-check E-2

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
       contains .claude-plugin/plugin.json. The doctor lives at
       <plugin_root>/scripts/hermes-doctor.py so the parent of parent is
       the usual hit; we walk further as a safety margin.
    3. None — distinct "cannot locate" condition, NOT BROKEN. The caller
       reports this as its own verdict.

    Returns (root_path, source, note) where:
      source ∈ {"env", "self-discovered", "env-then-self", "not-found"}
      note   is a short human-readable explanation when relevant.

    Critical: the brief's #4 finding (forked doctor reports false BROKEN
    because CLAUDE_PLUGIN_ROOT doesn't survive the forked subshell) is
    closed by step 2 — the doctor finds its own plugin root from __file__
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

    # Walk up from __file__. The script lives at <root>/scripts/hermes-doctor.py;
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
                 l2_checks: list[dict[str, Any]], l2_fails: int, l2_advisories: int) -> str:
    """Render the §5.2 banner."""
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    name = project_root.name
    out: list[str] = []
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"  HERMES-DOCTOR · {name} · {ts}")
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

    verdict = compute_verdict(plugin_root, l1_fails, l2_fails, l2_advisories)
    suffix = ""
    if verdict == "DEGRADED":
        suffix = f" with {l2_advisories} advisor{'y' if l2_advisories == 1 else 'ies'}"
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"  Overall: {verdict}{suffix}")
    out.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    out.append("")
    out.append("  Note: v1.0.0 skeleton — Layer 1 + Layer 2 file-existence checks only.")
    out.append("        Format-violation stratification, cache freshness, banner-rendering")
    out.append("        caveat, and intake reconciliation land in the Doctor session.")
    return "\n".join(out)


def render_json(plugin_root: Path | None, root_source: str, root_note: str | None,
                project_root: Path,
                l1_checks: list[dict[str, Any]], l1_fails: int,
                l2_checks: list[dict[str, Any]], l2_fails: int, l2_advisories: int) -> str:
    """Render §5.6 versioned JSON output."""
    verdict = compute_verdict(plugin_root, l1_fails, l2_fails, l2_advisories)
    payload = {
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
        "summary": {
            "verdict": verdict,
            "failures": l1_fails + l2_fails,
            "advisories": l2_advisories,
        },
    }
    return json.dumps(payload, indent=2)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="cc-forge framework self-check (skeleton)")
    p.add_argument("--project-root", default=".", help="Project root (default: cwd)")
    p.add_argument("--json", action="store_true", help="Emit JSON instead of banner")
    args = p.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    plugin_root, root_source, root_note = resolve_plugin_root()

    l1_checks, l1_fails = check_layer1(plugin_root, root_source)
    l2_checks, l2_fails, l2_advisories = check_layer2(project_root)

    if args.json:
        print(render_json(plugin_root, root_source, root_note, project_root,
                          l1_checks, l1_fails, l2_checks, l2_fails, l2_advisories))
    else:
        print(render_human(plugin_root, root_source, root_note, project_root,
                           l1_checks, l1_fails, l2_checks, l2_fails, l2_advisories))

    verdict = compute_verdict(plugin_root, l1_fails, l2_fails, l2_advisories)
    # Exit codes:
    #   0  HEALTHY
    #   1  DEGRADED
    #   2  BROKEN
    #   3  CANNOT_LOCATE (distinct from BROKEN — we couldn't find the
    #                    plugin to check it; not a Layer-1 failure verdict)
    return {"HEALTHY": 0, "DEGRADED": 1, "BROKEN": 2, "CANNOT_LOCATE": 3}[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
