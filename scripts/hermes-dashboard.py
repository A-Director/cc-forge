#!/usr/bin/env python3
"""
hermes-dashboard.py — generate dashboard.html from project markdown sources.

Reads .cc-forge/state.json, backlog/*.md, PHASES.md, RISKS.md, DECISIONS.md,
.cc-forge/usage.log, and (optionally) Claude Code conversation jsonl files.
Writes a single self-contained dashboard.html in the project root.

Design reference: docs-templates/dashboard-prototype.html. The HTML template
embedded in this script is derived from that prototype.

Stdlib only — no external dependencies. Degrades gracefully when sources
are missing.

Usage:
    python3 scripts/hermes-dashboard.py [--project-root PATH] [--output PATH]
"""

from __future__ import annotations

import argparse
import datetime as dt
import glob
import json
import os
import re
import sys
from pathlib import Path
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

DOMAIN_NUMBERS = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10"]
DOMAIN_NAMES = {
    "01": "Product",
    "02": "Development",
    "03": "Security",
    "04": "Reliability",
    "05": "Design",
    "06": "Integrations",
    "07": "Compliance",
    "08": "Launch",
    "09": "Growth",
    "10": "Operations",
}
DOMAIN_DEFAULT_OWNERS = {
    "01": "Product Owner",
    "02": "CTO + QA",
    "03": "Security Auditor",
    "04": "SRE Engineer",
    "05": "UX Expert",
    "06": "CTO",
    "07": "Legal/Compliance",
    "08": "Product Owner",
    "09": "Growth Agent",
    "10": "CFO + SRE",
}

STATUSES = ["done", "in-progress", "not-started", "not-applicable", "operator-action"]

# Phase target defaults (used if PHASES.md not parseable). Mirrors PHASES.md
# bar table — values are percent targets per phase, per domain.
PHASE_DEFAULTS: dict[int, dict[str, int]] = {
    1: {"01": 80,  "02": 60, "03": 20, "04": 10, "05": 20, "06": 40, "07": 0,  "08": 0,  "09": 0,  "10": 10},
    2: {"01": 100, "02": 80, "03": 60, "04": 40, "05": 60, "06": 70, "07": 10, "08": 20, "09": 10, "10": 30},
    3: {"01": 100, "02": 90, "03": 80, "04": 70, "05": 70, "06": 90, "07": 40, "08": 50, "09": 20, "10": 60},
    4: {"01": 95,  "02": 95, "03": 95, "04": 95, "05": 95, "06": 95, "07": 90, "08": 95, "09": 50, "10": 80},
    5: {"01": 95,  "02": 95, "03": 95, "04": 95, "05": 95, "06": 95, "07": 95, "08": 95, "09": 80, "10": 90},
}
PHASE_NAMES = {1: "MVP", 2: "Beta", 3: "Pilot", 4: "Launch", 5: "Growth"}

# Anthropic API price per million tokens (Sonnet 4.6 as a sane default).
# Used only for the estimated-cost number on the Usage tab.
PRICE_PER_M_INPUT = 3.0
PRICE_PER_M_OUTPUT = 15.0
PRICE_PER_M_CACHE_READ = 0.30


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def read_text_safe(path: Path) -> str | None:
    """Read a text file, return None if missing or unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except (FileNotFoundError, IsADirectoryError, PermissionError, UnicodeDecodeError):
        return None


def to_js(value: Any) -> str:
    """JSON encode a Python value for embedding in a <script> block."""
    # ensure_ascii=False keeps em-dashes etc. legible; </script> is the only
    # sequence we must defuse to be safe inside <script>.
    return json.dumps(value, ensure_ascii=False).replace("</script>", "<\\/script>")


def humanize_number(n: float) -> str:
    """Format a number as 1.2k, 3.4M, 567 for use in UI cards."""
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.0f}k"
    return f"{int(n)}"


# ─────────────────────────────────────────────────────────────────────────────
# Parsers
# ─────────────────────────────────────────────────────────────────────────────

def parse_state_json(project_root: Path) -> dict[str, Any]:
    raw = read_text_safe(project_root / ".cc-forge" / "state.json")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def parse_phases_md(project_root: Path, current_phase: int | None) -> dict[str, Any]:
    """
    Parse PHASES.md to extract the current phase's name + exit-gate bullets +
    active personas + per-domain targets. Degrades to PHASE_DEFAULTS if the
    file is missing or shapes can't be located.
    """
    if current_phase is None:
        current_phase = 1

    raw = read_text_safe(project_root / "PHASES.md")
    targets = PHASE_DEFAULTS.get(current_phase, PHASE_DEFAULTS[1]).copy()
    name = PHASE_NAMES.get(current_phase, "MVP")
    exit_criteria: list[str] = []
    personas: list[str] = []

    if not raw:
        return {
            "number": current_phase,
            "name": name,
            "exit_criteria": exit_criteria,
            "personas": personas,
            "targets": targets,
            "source": "defaults",
        }

    # Find the section heading like "### Phase 2 — Beta"
    section_pat = re.compile(
        rf"###\s+Phase\s+{current_phase}\b[^\n]*",
        re.IGNORECASE,
    )
    m = section_pat.search(raw)
    if m:
        start = m.start()
        # next ### Phase or top-level ## section ends the block
        rest = raw[m.end():]
        end_m = re.search(r"\n###\s+Phase\s+\d|\n##\s+", rest)
        section_body = rest[: end_m.start()] if end_m else rest
        section = raw[start: start + (m.end() - start) + len(section_body)]
        # Pull the name from the heading
        name_m = re.match(r"###\s+Phase\s+\d+\s*[—-]\s*([A-Za-z][A-Za-z0-9 ]*)", raw[start:])
        if name_m:
            name = name_m.group(1).strip()

        # Exit gate bullets: lines after "Exit gate" until next "**"
        eg_m = re.search(r"\*\*Exit gate:\*\*\s*([^\n]+(?:\n[^*\n][^\n]*)*)", section)
        if eg_m:
            raw_block = eg_m.group(1)
            # split on " · " or sentence-ish dots, take fragments
            parts = re.split(r"\s+·\s+", raw_block)
            for p in parts:
                p = p.strip().rstrip(".").rstrip(",")
                if p:
                    exit_criteria.append(p)

        # Active personas: "**Personas active:**" line
        pa_m = re.search(r"\*\*Personas active:\*\*\s*([^\n]+)", section)
        if pa_m:
            line = pa_m.group(1)
            # Strip leading "+ " or "+ ", split on commas
            line = re.sub(r"^\+\s*", "", line)
            for p in re.split(r",\s*", line):
                p = re.sub(r"\([^)]*\)", "", p).strip().rstrip(".").rstrip(",")
                if p:
                    personas.append(p)

    return {
        "number": current_phase,
        "name": name,
        "exit_criteria": exit_criteria,
        "personas": personas,
        "targets": targets,
        "source": "PHASES.md" if raw else "defaults",
    }


def parse_backlog_item(block: str) -> dict[str, Any]:
    """Parse one backlog item block (between '### [ID]' headers) into a dict."""
    item: dict[str, Any] = {
        "id": "",
        "title": "",
        "outcome": "",
        "standard": "",
        "owner": "",
        "phase": None,
        "applicability": "",
        "status": "not-started",
        "evidence": "",
    }
    lines = block.strip().split("\n")
    if lines and lines[0].startswith("### "):
        header = lines[0][4:].strip()
        idm = re.match(r"\[([^\]]+)\]\s*(.*)", header)
        if idm:
            item["id"] = idm.group(1).strip()
            item["title"] = idm.group(2).strip()
    # Canonical list-item form per spec §3.2 (post-Session-0). Lines look
    # like "- Field: value". Note: this is line-anchored on the stripped
    # form; whitespace before "- " is acceptable.
    field_pat = re.compile(r"^-\s+([A-Za-z][A-Za-z-]*):\s*(.+)$")
    for ln in lines[1:]:
        fm = field_pat.match(ln.strip())
        if not fm:
            continue
        key = fm.group(1).lower()
        val = fm.group(2).strip()
        if key == "outcome":
            item["outcome"] = val
        elif key == "standard":
            item["standard"] = val
        elif key == "owner":
            item["owner"] = val
        elif key == "phase":
            pm = re.match(r"(\d+)", val)
            if pm:
                item["phase"] = int(pm.group(1))
        elif key == "applicability":
            item["applicability"] = val
        elif key == "status":
            v = val.strip().lower()
            if v in STATUSES:
                item["status"] = v
        elif key == "evidence":
            item["evidence"] = val
    return item


def parse_backlog_domain(project_root: Path, dn: str) -> dict[str, Any]:
    """Parse one domain file. Tries .cc-forge/backlog/ first, falls back to backlog/."""
    candidates = [
        project_root / ".cc-forge" / "backlog" / f"{dn}-{DOMAIN_NAMES[dn].lower()}.md",
        project_root / ".cc-forge" / "backlog",
        project_root / "backlog" / f"{dn}-{DOMAIN_NAMES[dn].lower()}.md",
        project_root / "backlog",
    ]
    raw: str | None = None
    used: Path | None = None
    # Direct name try first
    for c in candidates:
        if c.is_file():
            raw = read_text_safe(c)
            used = c
            break
        if c.is_dir():
            for f in sorted(c.glob(f"{dn}-*.md")):
                raw = read_text_safe(f)
                used = f
                break
            if raw is not None:
                break

    items: list[dict[str, Any]] = []
    if raw:
        # Split on '### [' but keep '###' attached
        chunks = re.split(r"(?m)^(?=###\s+\[)", raw)
        for ch in chunks:
            if ch.lstrip().startswith("### ["):
                it = parse_backlog_item(ch)
                if it["id"]:
                    items.append(it)

    # Compute counts (excluding not-applicable from completion %)
    applicable = [i for i in items if i["status"] != "not-applicable"]
    done = sum(1 for i in items if i["status"] == "done")
    prog = sum(1 for i in items if i["status"] == "in-progress")
    op = sum(1 for i in items if i["status"] == "operator-action")
    todo = sum(1 for i in items if i["status"] == "not-started")
    na = sum(1 for i in items if i["status"] == "not-applicable")

    pct = int(round((done / len(applicable)) * 100)) if applicable else 0

    return {
        "num": dn,
        "name": DOMAIN_NAMES[dn],
        "owner": DOMAIN_DEFAULT_OWNERS[dn],
        "items": items,
        "pct": pct,
        "done": done,
        "prog": prog,
        "op": op,
        "todo": todo,
        "na": na,
        "total": len(items),
        "applicable": len(applicable),
        "source": str(used.relative_to(project_root)) if used else None,
    }


def parse_backlog_master(project_root: Path) -> dict[str, Any]:
    """Best-effort: extract phase from header line if present."""
    raw = read_text_safe(project_root / ".cc-forge" / "backlog" / "master.md")
    if not raw:
        raw = read_text_safe(project_root / "backlog" / "master.md")
    out: dict[str, Any] = {"phase": None}
    if raw:
        m = re.search(r"Current PDLC phase[^\n]*?:\s*(\d+)", raw)
        if m:
            out["phase"] = int(m.group(1))
    return out


def parse_risks_md(project_root: Path) -> list[dict[str, Any]]:
    """
    Parse RISKS.md. Recognises ### [RISK-NNN] Title headings + fielded blocks:
    Severity, Description / desc, Mitigation, Owner, Review.
    Tolerant to variant shapes; returns empty list if nothing recognisable.
    """
    raw = read_text_safe(project_root / "RISKS.md")
    if not raw:
        return []
    risks: list[dict[str, Any]] = []
    chunks = re.split(r"(?m)^(?=###\s+\[?RISK[- ])", raw)
    for ch in chunks:
        if not re.match(r"^###\s+", ch.lstrip()):
            continue
        head_m = re.match(r"###\s+\[?(RISK[- ]?\d+)\]?\s*(.*)$", ch.lstrip().split("\n", 1)[0])
        if not head_m:
            continue
        rid = head_m.group(1).replace(" ", "-")
        title = head_m.group(2).strip()
        sev = "med"
        desc = ""
        mit = ""
        owner = ""
        review = ""
        for ln in ch.split("\n")[1:]:
            ln_stripped = ln.strip()
            sm = re.match(r"\*\*Severity:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if sm:
                v = sm.group(1).strip().lower()
                if "crit" in v: sev = "crit"
                elif "high" in v: sev = "high"
                elif "med" in v: sev = "med"
                elif "low" in v: sev = "low"
                continue
            dm = re.match(r"\*\*Description:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if dm:
                desc = dm.group(1).strip()
                continue
            mm = re.match(r"\*\*Mitigation:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if mm:
                mit = mm.group(1).strip()
                continue
            om = re.match(r"\*\*Owner:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if om:
                owner = om.group(1).strip()
                continue
            rm = re.match(r"\*\*Review:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if rm:
                review = rm.group(1).strip()
                continue
        risks.append({
            "id": rid,
            "sev": sev,
            "title": title,
            "desc": desc,
            "mit": mit,
            "owner": owner,
            "review": review,
        })
    sev_order = {"crit": 0, "high": 1, "med": 2, "low": 3}
    risks.sort(key=lambda r: sev_order.get(r["sev"], 9))
    return risks


def parse_decisions_md(project_root: Path) -> list[dict[str, Any]]:
    """
    Parse DECISIONS.md. Recognises ### [ADR-NNN] Title headings with
    Date, Status, Context, Rationale fields. Tolerant to variant shapes.
    """
    raw = read_text_safe(project_root / "DECISIONS.md")
    if not raw:
        return []
    adrs: list[dict[str, Any]] = []
    chunks = re.split(r"(?m)^(?=###\s+\[?ADR[- ])", raw)
    for ch in chunks:
        if not re.match(r"^###\s+", ch.lstrip()):
            continue
        first = ch.lstrip().split("\n", 1)[0]
        head_m = re.match(r"###\s+\[?(ADR[- ]?[\w-]+)\]?\s*(.*)$", first)
        if not head_m:
            continue
        aid = head_m.group(1).replace(" ", "-")
        title = head_m.group(2).strip()
        status = "accepted"
        date = ""
        ctx = ""
        why = ""
        for ln in ch.split("\n")[1:]:
            ln_stripped = ln.strip()
            sm = re.match(r"\*\*Status:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if sm:
                v = sm.group(1).strip().lower()
                if "deprec" in v: status = "deprecated"
                elif "propos" in v: status = "proposed"
                elif "accept" in v: status = "accepted"
                continue
            dm = re.match(r"\*\*Date:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if dm:
                date = dm.group(1).strip()
                continue
            cm = re.match(r"\*\*Context:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if cm:
                ctx = cm.group(1).strip()
                continue
            rm = re.match(r"\*\*Rationale:\*\*\s*(.*)", ln_stripped, re.IGNORECASE)
            if rm:
                why = rm.group(1).strip()
                continue
        adrs.append({
            "id": aid,
            "date": date,
            "status": status,
            "title": title,
            "ctx": ctx,
            "why": why,
        })
    # newest first if date parseable
    def date_key(a: dict[str, Any]) -> str:
        return a["date"] or "0000"
    adrs.sort(key=date_key, reverse=True)
    return adrs


def parse_usage_log(project_root: Path) -> dict[str, Any]:
    """
    Parse JSONL .cc-forge/usage.log. Returns aggregates:
        sessions, commands, persona_counts, persona_outcomes,
        drift counts (orphan_task, missing_coverage, standards_strip,
        phase_transitions), trajectory (session_start backlog %s),
        last argus run date, model distribution.
    """
    out: dict[str, Any] = {
        "sessions": 0,
        "commands": {},
        "persona_counts": {},
        "persona_outcomes": {},     # persona -> {"PASS": n, "CONDITIONAL": n, "BLOCK": n}
        "claude_md_tokens_seen": None,
        "drift": {
            "orphan_task": 0,
            "missing_coverage": 0,
            "standards_strip_detected": 0,
            "argus_drift": 0,
        },
        "phase_transitions": [],
        "trajectory": [],
        "last_argus": None,
        "model_distribution": {},
        "gates": 0,
        "compact_runs": 0,
        "has_data": False,
    }
    raw = read_text_safe(project_root / ".cc-forge" / "usage.log")
    if not raw:
        return out
    out["has_data"] = True
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = entry.get("type")
        data = entry.get("data") or {}
        ts = entry.get("ts", "")

        if etype == "session_start":
            out["sessions"] += 1
            pct = data.get("backlog_overall_pct")
            if isinstance(pct, (int, float)):
                out["trajectory"].append({"ts": ts, "pct": int(pct)})
            cmt = data.get("claude_md_tokens")
            if isinstance(cmt, (int, float)):
                out["claude_md_tokens_seen"] = int(cmt)
        elif etype == "session_end":
            if data.get("compact_run"):
                out["compact_runs"] += 1
            model = data.get("model_used")
            if model:
                out["model_distribution"][model] = out["model_distribution"].get(model, 0) + 1
        elif etype == "command":
            cmd = data.get("command")
            if cmd:
                out["commands"][cmd] = out["commands"].get(cmd, 0) + 1
        elif etype == "gate":
            out["gates"] += 1
            personas = data.get("personas") or []
            outcomes = data.get("outcomes") or {}
            for p in personas:
                out["persona_counts"][p] = out["persona_counts"].get(p, 0) + 1
            for p, o in outcomes.items():
                bucket = out["persona_outcomes"].setdefault(p, {"PASS": 0, "CONDITIONAL": 0, "BLOCK": 0})
                if o in bucket:
                    bucket[o] += 1
        elif etype == "persona":
            p = data.get("persona")
            if p:
                out["persona_counts"][p] = out["persona_counts"].get(p, 0) + 1
                bucket = out["persona_outcomes"].setdefault(p, {"PASS": 0, "CONDITIONAL": 0, "BLOCK": 0})
                outcome = data.get("outcome")
                if outcome in bucket:
                    bucket[outcome] += 1
        elif etype == "orphan_task":
            out["drift"]["orphan_task"] += 1
        elif etype == "missing_coverage":
            out["drift"]["missing_coverage"] += 1
        elif etype == "standards_strip_detected":
            out["drift"]["standards_strip_detected"] += 1
        elif etype == "drift":
            out["drift"]["argus_drift"] += 1
            detected_by = data.get("detected_by", "")
            if detected_by == "argus":
                out["last_argus"] = ts
        elif etype == "phase_transition":
            out["phase_transitions"].append({
                "ts": ts,
                "from": data.get("from"),
                "to": data.get("to"),
                "outcome": data.get("outcome"),
            })
    return out


def parse_cc_conversations(project_root: Path) -> dict[str, Any]:
    """
    Best-effort read of Claude Code conversation jsonl. Returns total tokens
    (input/output/cache_read), session count, and estimated cost. Degrades
    gracefully — every error path returns the unavailable shape.
    """
    unavailable = {
        "available": False,
        "input": 0,
        "output": 0,
        "cache_read": 0,
        "cost": 0.0,
        "sessions": 0,
        "note": "raw token data unavailable — check ~/.claude/projects/",
    }
    cc_home = Path(os.path.expanduser("~/.claude/projects"))
    if not cc_home.is_dir():
        return unavailable

    # Project hash convention: leading slash dropped, slashes → dashes.
    abs_root = str(project_root.resolve())
    candidate = "-" + abs_root.lstrip("/").replace("/", "-")
    proj_dir = cc_home / candidate
    if not proj_dir.is_dir():
        # Fall back to scanning all project dirs for one whose conversations
        # mention this path — too expensive; skip.
        return unavailable

    files = sorted(proj_dir.glob("*.jsonl"))
    if not files:
        return unavailable

    total_in = 0
    total_out = 0
    total_cache_r = 0
    sessions = 0
    for f in files:
        sessions += 1
        try:
            with f.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        msg = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    usage = (msg.get("message") or {}).get("usage") or msg.get("usage") or {}
                    if not isinstance(usage, dict):
                        continue
                    total_in += int(usage.get("input_tokens", 0) or 0)
                    total_out += int(usage.get("output_tokens", 0) or 0)
                    total_cache_r += int(usage.get("cache_read_input_tokens", 0) or 0)
        except OSError:
            continue

    cost = (
        total_in * PRICE_PER_M_INPUT / 1_000_000
        + total_out * PRICE_PER_M_OUTPUT / 1_000_000
        + total_cache_r * PRICE_PER_M_CACHE_READ / 1_000_000
    )

    return {
        "available": True,
        "input": total_in,
        "output": total_out,
        "cache_read": total_cache_r,
        "cost": cost,
        "sessions": sessions,
        "note": "parsed from ~/.claude/projects/<hash>/conversation-*.jsonl · message-level metadata",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Computation
# ─────────────────────────────────────────────────────────────────────────────

def compute_hermes_overhead(
    usage: dict[str, Any],
    weights: dict[str, Any],
    cc_raw: dict[str, Any],
) -> dict[str, Any]:
    """
    Estimate Hermes overhead tokens from usage.log + token-weights.json.
    Returns a breakdown so the dashboard can show each contributor.
    """
    cmd_weights = weights.get("commands", {})
    persona_w = int(weights.get("persona_invocation", 2000))
    claude_md_per_turn = int(weights.get("claude_md_per_turn", 600))

    # Commands
    cmd_tokens = 0
    for cmd, count in usage.get("commands", {}).items():
        w = cmd_weights.get(cmd, 1500)  # fallback weight
        cmd_tokens += int(count) * int(w)

    # Persona invocations (gates + persona events)
    persona_invocations = sum(usage.get("persona_counts", {}).values())
    persona_tokens = persona_invocations * persona_w

    # CLAUDE.md context — approximate by sessions × turns/session × tokens
    # We don't know turns per session, so use sessions × 8 as a default
    # "turns per session" heuristic. Honesty note: this is the weakest part
    # of the estimate; v2 will replace it.
    sessions = usage.get("sessions", 0)
    estimated_turns = sessions * 8
    claude_md_tokens = estimated_turns * claude_md_per_turn

    hermes_total = cmd_tokens + persona_tokens + claude_md_tokens

    cc_total = (cc_raw or {}).get("input", 0) + (cc_raw or {}).get("output", 0)
    share_pct: float | None = None
    if cc_total > 0:
        share_pct = round(hermes_total / cc_total * 100, 1)

    return {
        "claude_md_tokens": claude_md_tokens,
        "command_tokens": cmd_tokens,
        "persona_tokens": persona_tokens,
        "persona_invocations": persona_invocations,
        "command_invocations": sum(usage.get("commands", {}).values()),
        "hermes_total": hermes_total,
        "cc_total": cc_total,
        "share_pct": share_pct,
        "estimated_turns": estimated_turns,
    }


def compute_phase_exit_progress(phase: dict[str, Any], domains: list[dict[str, Any]]) -> dict[str, Any]:
    """
    For each per-domain target, mark whether the current domain % meets it.
    Returns met/total counts and per-domain bar status.
    """
    targets = phase.get("targets", {})
    met = 0
    total = 0
    per_domain: dict[str, dict[str, Any]] = {}
    for d in domains:
        t = int(targets.get(d["num"], 0))
        if t > 0:
            total += 1
            ok = d["pct"] >= t
            if ok:
                met += 1
        per_domain[d["num"]] = {"target": t, "met": d["pct"] >= t}
    # Plus per-criterion exit-gate count from PHASES.md bullets (we treat
    # the parsed bullets as informational, not auto-checkable).
    return {
        "domains_met": met,
        "domains_total": total,
        "per_domain": per_domain,
        "criteria": phase.get("exit_criteria", []),
    }


def compute_overall_pct(domains: list[dict[str, Any]]) -> dict[str, Any]:
    total_applicable = sum(d["applicable"] for d in domains)
    total_done = sum(d["done"] for d in domains)
    pct = int(round(total_done / total_applicable * 100)) if total_applicable else 0
    return {
        "pct": pct,
        "applicable": total_applicable,
        "done": total_done,
        "total": sum(d["total"] for d in domains),
        "na": sum(d["na"] for d in domains),
    }


def compute_observed_orphans(domains: list[dict[str, Any]]) -> int:
    """
    Observed orphans (vs logged orphans): backlog items marked in-progress
    whose Evidence line lacks a Taskmaster reference. This is the "current
    state" drift counter distinct from the logged orphan_task events.
    """
    count = 0
    for d in domains:
        for it in d["items"]:
            if it["status"] == "in-progress":
                ev = it.get("evidence", "") or ""
                if "Taskmaster" not in ev and "#" not in ev:
                    count += 1
    return count


# ─────────────────────────────────────────────────────────────────────────────
# Rendering — HTML template embedded below
# ─────────────────────────────────────────────────────────────────────────────

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>cc-forge dashboard — __PROJECT_NAME__</title>
<style>
  :root {
    --bg: #faf8f3;
    --bg-card: #ffffff;
    --bg-subtle: #f3f0e8;
    --bg-strong: #1c1b18;
    --ink: #1c1b18;
    --ink-soft: #5b5950;
    --ink-faint: #8c8a7e;
    --rule: #e5e1d4;
    --accent: #b8472e;
    --accent-soft: #f5e6e0;
    --green: #2d6a4f;
    --green-soft: #dceee2;
    --amber: #b67800;
    --amber-soft: #fbeed2;
    --red: #a01818;
    --red-soft: #f9dada;
    --blue: #1d4e89;
    --blue-soft: #dfe9f5;
    --purple: #5a3e85;
    --purple-soft: #ebe2f3;
    --font-display: 'Fraunces', 'Iowan Old Style', 'Palatino', Georgia, serif;
    --font-body: 'Inter Tight', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body {
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-body);
    font-size: 14px;
    line-height: 1.55;
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
  }
  .container { max-width: 1280px; margin: 0 auto; padding: 32px 40px 80px; }
  .header { display: grid; grid-template-columns: 1fr auto; align-items: end; gap: 24px; padding-bottom: 24px; border-bottom: 1px solid var(--rule); margin-bottom: 32px; }
  .header-left h1 { font-family: var(--font-display); font-size: 44px; font-weight: 400; letter-spacing: -0.02em; line-height: 1; margin-bottom: 6px; }
  .header-left h1 .small { font-size: 22px; color: var(--ink-soft); margin-left: 8px; font-style: italic; }
  .header-left .meta { color: var(--ink-faint); font-size: 13px; font-family: var(--font-mono); letter-spacing: 0.02em; }
  .header-right { text-align: right; }
  .pill-row { display: inline-flex; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
  .stage-pill { display: inline-flex; align-items: center; gap: 8px; background: var(--bg-strong); color: var(--bg); padding: 6px 14px; font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }
  .stage-pill .dot { width: 6px; height: 6px; background: var(--green); border-radius: 50%; }
  .phase-pill { display: inline-flex; align-items: center; gap: 8px; background: var(--accent); color: white; padding: 6px 14px; font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; }
  .phase-pill .dot { width: 6px; height: 6px; background: white; border-radius: 50%; }
  .gen-time { color: var(--ink-faint); font-size: 12px; margin-top: 8px; font-family: var(--font-mono); }

  .kpi-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--rule); border: 1px solid var(--rule); margin-bottom: 32px; }
  .kpi { background: var(--bg-card); padding: 20px 24px; }
  .kpi-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-faint); margin-bottom: 10px; font-weight: 500; }
  .kpi-value { font-family: var(--font-display); font-size: 36px; font-weight: 400; letter-spacing: -0.02em; line-height: 1; }
  .kpi-value .unit { font-size: 18px; color: var(--ink-soft); margin-left: 2px; }
  .kpi-trend { margin-top: 8px; font-size: 12px; color: var(--ink-soft); font-family: var(--font-mono); }
  .kpi-trend.up { color: var(--green); }
  .kpi-trend.warn { color: var(--amber); }
  .kpi-trend.bad { color: var(--red); }

  .tabs { display: flex; gap: 0; border-bottom: 1px solid var(--rule); margin-bottom: 32px; }
  .tab { padding: 12px 20px 14px; background: transparent; border: none; cursor: pointer; font-family: var(--font-body); font-size: 13px; font-weight: 500; color: var(--ink-faint); border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color 0.15s ease; letter-spacing: 0.01em; }
  .tab:hover { color: var(--ink-soft); }
  .tab.active { color: var(--ink); border-bottom-color: var(--accent); }
  .tab .badge { display: inline-block; background: var(--bg-subtle); color: var(--ink-soft); font-size: 11px; padding: 1px 7px; border-radius: 10px; margin-left: 6px; font-weight: 500; }
  .tab.active .badge { background: var(--accent-soft); color: var(--accent); }

  .panel { display: none; }
  .panel.active { display: block; }

  .section-h { font-family: var(--font-display); font-size: 22px; font-weight: 400; letter-spacing: -0.01em; margin-bottom: 4px; }
  .section-sub { color: var(--ink-faint); font-size: 13px; margin-bottom: 24px; }

  .backlog-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin-bottom: 32px; }
  .domain-card { background: var(--bg-card); border: 1px solid var(--rule); padding: 18px 20px; }
  .domain-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; }
  .domain-num { font-family: var(--font-mono); font-size: 11px; color: var(--ink-faint); letter-spacing: 0.05em; }
  .domain-name { font-size: 14px; font-weight: 500; margin-top: 2px; }
  .domain-pct { font-family: var(--font-display); font-size: 26px; line-height: 1; font-weight: 400; }
  .domain-target { font-family: var(--font-mono); font-size: 11px; color: var(--ink-faint); margin-top: 4px; text-align: right; }
  .domain-target.met { color: var(--green); }
  .domain-target.miss { color: var(--accent); }
  .progress-bar { height: 4px; background: var(--bg-subtle); position: relative; margin-bottom: 10px; }
  .progress-fill { height: 100%; background: var(--ink); transition: width 0.6s ease; }
  .progress-fill.complete { background: var(--green); }
  .progress-fill.warn { background: var(--amber); }
  .progress-fill.behind { background: var(--accent); }
  .progress-target { position: absolute; top: -3px; bottom: -3px; width: 2px; background: var(--ink-faint); }
  .domain-meta { display: flex; gap: 14px; font-size: 12px; color: var(--ink-soft); font-family: var(--font-mono); flex-wrap: wrap; }
  .domain-meta .pill { display: inline-flex; align-items: center; gap: 4px; }
  .domain-meta .pill .dot { width: 6px; height: 6px; border-radius: 50%; }
  .dot-done { background: var(--green); }
  .dot-prog { background: var(--amber); }
  .dot-todo { background: var(--ink-faint); }
  .dot-op   { background: var(--blue); }
  .dot-na   { background: var(--rule); border: 1px solid var(--ink-faint); }
  .domain-owner { margin-top: 12px; padding-top: 10px; border-top: 1px dashed var(--rule); font-size: 11px; color: var(--ink-faint); font-family: var(--font-mono); text-transform: uppercase; letter-spacing: 0.05em; }

  .filter-row { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; flex-wrap: wrap; }
  .filter-label { font-size: 12px; color: var(--ink-faint); margin-right: 8px; text-transform: uppercase; letter-spacing: 0.08em; }
  .chip { padding: 5px 12px; background: var(--bg-card); border: 1px solid var(--rule); font-size: 12px; cursor: pointer; font-family: var(--font-mono); transition: all 0.12s ease; }
  .chip:hover { border-color: var(--ink-soft); }
  .chip.active { background: var(--ink); color: var(--bg); border-color: var(--ink); }

  .item-table { width: 100%; border-collapse: collapse; background: var(--bg-card); border: 1px solid var(--rule); }
  .item-table th { text-align: left; padding: 10px 16px; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; color: var(--ink-faint); border-bottom: 1px solid var(--rule); background: var(--bg-subtle); }
  .item-table td { padding: 12px 16px; border-bottom: 1px solid var(--rule); vertical-align: top; font-size: 13px; }
  .item-table tr:last-child td { border-bottom: none; }
  .item-table tr:hover { background: var(--bg-subtle); }
  .item-id { font-family: var(--font-mono); font-size: 11px; color: var(--ink-soft); white-space: nowrap; }
  .status-tag { display: inline-block; padding: 2px 8px; font-size: 11px; font-family: var(--font-mono); text-transform: lowercase; letter-spacing: 0.02em; }
  .status-done { background: var(--green-soft); color: var(--green); }
  .status-prog { background: var(--amber-soft); color: var(--amber); }
  .status-todo { background: var(--bg-subtle); color: var(--ink-soft); }
  .status-op   { background: var(--blue-soft); color: var(--blue); }
  .status-na   { background: transparent; color: var(--ink-faint); border: 1px dashed var(--ink-faint); }

  .risk-card { display: grid; grid-template-columns: 80px 1fr auto; gap: 24px; padding: 20px 24px; background: var(--bg-card); border: 1px solid var(--rule); border-left-width: 4px; margin-bottom: 12px; align-items: start; }
  .risk-card.crit { border-left-color: var(--red); }
  .risk-card.high { border-left-color: var(--accent); }
  .risk-card.med  { border-left-color: var(--amber); }
  .risk-card.low  { border-left-color: var(--ink-faint); }
  .risk-sev { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; font-weight: 500; }
  .risk-card.crit .risk-sev { color: var(--red); }
  .risk-card.high .risk-sev { color: var(--accent); }
  .risk-card.med  .risk-sev { color: var(--amber); }
  .risk-card.low  .risk-sev { color: var(--ink-faint); }
  .risk-id { font-family: var(--font-mono); font-size: 11px; color: var(--ink-faint); margin-top: 4px; }
  .risk-title { font-size: 15px; font-weight: 500; margin-bottom: 4px; }
  .risk-desc { font-size: 13px; color: var(--ink-soft); margin-bottom: 10px; }
  .risk-mitigation { font-size: 12px; color: var(--ink-faint); font-style: italic; padding-top: 8px; border-top: 1px dashed var(--rule); }
  .risk-mitigation strong { font-style: normal; color: var(--ink-soft); text-transform: uppercase; font-size: 10px; letter-spacing: 0.08em; font-weight: 500; margin-right: 6px; }
  .risk-meta { text-align: right; font-family: var(--font-mono); font-size: 11px; color: var(--ink-faint); }
  .risk-meta div + div { margin-top: 4px; }

  .adr-search { width: 100%; padding: 10px 14px; border: 1px solid var(--rule); background: var(--bg-card); font-family: var(--font-body); font-size: 13px; margin-bottom: 16px; }
  .adr-search:focus { outline: none; border-color: var(--ink); }
  .adr { background: var(--bg-card); border: 1px solid var(--rule); padding: 18px 22px; margin-bottom: 10px; }
  .adr-head { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; gap: 16px; }
  .adr-num { font-family: var(--font-mono); font-size: 11px; color: var(--ink-faint); letter-spacing: 0.04em; }
  .adr-status { font-family: var(--font-mono); font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; padding: 2px 8px; }
  .adr-status.accepted { background: var(--green-soft); color: var(--green); }
  .adr-status.proposed { background: var(--amber-soft); color: var(--amber); }
  .adr-status.deprecated { background: var(--bg-subtle); color: var(--ink-faint); text-decoration: line-through; }
  .adr-title { font-size: 15px; font-weight: 500; margin-bottom: 8px; line-height: 1.3; }
  .adr-context { font-size: 13px; color: var(--ink-soft); margin-bottom: 8px; }
  .adr-rationale { font-size: 12px; color: var(--ink-faint); border-top: 1px dashed var(--rule); padding-top: 8px; }
  .adr-rationale strong { color: var(--ink-soft); text-transform: uppercase; font-size: 10px; letter-spacing: 0.08em; font-weight: 500; margin-right: 6px; }
  .adr-date { font-family: var(--font-mono); font-size: 11px; color: var(--ink-faint); }

  .usage-row { display: grid; grid-template-columns: 2fr 1fr; gap: 16px; margin-bottom: 16px; }
  .panel-card { background: var(--bg-card); border: 1px solid var(--rule); padding: 24px; }
  .panel-card-h { font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-faint); margin-bottom: 16px; font-weight: 500; }
  .sparkline-wrap { height: 180px; width: 100%; margin-bottom: 8px; }
  .sparkline-x { display: flex; justify-content: space-between; font-family: var(--font-mono); font-size: 10px; color: var(--ink-faint); }
  .stat-list { display: flex; flex-direction: column; gap: 12px; }
  .stat-row { display: flex; justify-content: space-between; align-items: baseline; padding-bottom: 10px; border-bottom: 1px dashed var(--rule); }
  .stat-row:last-child { border-bottom: none; padding-bottom: 0; }
  .stat-row-label { font-size: 13px; color: var(--ink-soft); }
  .stat-row-val { font-family: var(--font-mono); font-size: 13px; font-weight: 500; }
  .stat-row-val.warn { color: var(--amber); }
  .stat-row-val.bad { color: var(--red); }

  .token-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
  .token-big { font-family: var(--font-display); font-size: 32px; line-height: 1; margin: 8px 0 4px; }
  .token-sub { font-size: 12px; color: var(--ink-faint); font-family: var(--font-mono); }
  .token-note { font-size: 11px; color: var(--ink-faint); font-style: italic; border-top: 1px dashed var(--rule); padding-top: 10px; margin-top: 6px; }

  .gate-table { width: 100%; border-collapse: collapse; margin-top: 4px; }
  .gate-table td { padding: 8px 0; font-size: 12px; border-bottom: 1px dashed var(--rule); }
  .gate-table tr:last-child td { border-bottom: none; }
  .gate-table .persona { font-weight: 500; }
  .gate-table .pco { font-family: var(--font-mono); color: var(--ink-faint); }
  .verdict { display: inline-block; padding: 1px 6px; font-size: 10px; font-family: var(--font-mono); letter-spacing: 0.05em; }
  .verdict.p { background: var(--green-soft); color: var(--green); }
  .verdict.c { background: var(--amber-soft); color: var(--amber); }
  .verdict.b { background: var(--red-soft); color: var(--red); }

  .footer { margin-top: 60px; padding-top: 24px; border-top: 1px solid var(--rule); font-size: 11px; color: var(--ink-faint); font-family: var(--font-mono); text-align: center; }
  .empty-state { text-align: center; padding: 40px 20px; color: var(--ink-faint); font-size: 13px; }

  .readiness { background: var(--bg-card); border: 1px solid var(--rule); padding: 24px 28px; margin-bottom: 28px; display: grid; grid-template-columns: 1fr auto; gap: 24px; align-items: center; }
  .readiness-left .h { font-family: var(--font-display); font-size: 24px; margin-bottom: 4px; }
  .readiness-left .s { font-size: 13px; color: var(--ink-soft); margin-bottom: 14px; }
  .readiness-track { height: 8px; background: var(--bg-subtle); position: relative; overflow: hidden; }
  .readiness-fill { height: 100%; background: var(--ink); transition: width 0.8s ease; }
  .readiness-marker { position: absolute; top: -4px; bottom: -4px; width: 2px; background: var(--accent); }
  .readiness-right { text-align: right; }
  .readiness-pct { font-family: var(--font-display); font-size: 48px; line-height: 1; letter-spacing: -0.02em; }
  .readiness-pct .sm { font-size: 20px; color: var(--ink-soft); }
  .readiness-verdict { margin-top: 6px; font-family: var(--font-mono); font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; }
  .readiness-verdict.green { color: var(--green); }
  .readiness-verdict.amber { color: var(--amber); }
  .readiness-verdict.red   { color: var(--red); }

  .exit-criteria { background: var(--bg-card); border: 1px solid var(--rule); padding: 20px 24px; margin-bottom: 28px; }
  .exit-criteria h3 { font-family: var(--font-display); font-size: 18px; font-weight: 400; margin-bottom: 4px; }
  .exit-criteria .ec-sub { font-size: 12px; color: var(--ink-faint); margin-bottom: 14px; }
  .exit-criteria ul { list-style: none; }
  .exit-criteria li { padding: 6px 0; font-size: 13px; color: var(--ink-soft); border-bottom: 1px dashed var(--rule); }
  .exit-criteria li:last-child { border-bottom: none; }

  .drift-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 20px; }
  .drift-card { background: var(--bg-card); border: 1px solid var(--rule); padding: 16px 20px; }
  .drift-card.bad { border-left: 4px solid var(--red); }
  .drift-card.warn { border-left: 4px solid var(--amber); }
  .drift-card.ok { border-left: 4px solid var(--green); }
  .drift-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--ink-faint); margin-bottom: 8px; font-weight: 500; }
  .drift-value { font-family: var(--font-display); font-size: 26px; line-height: 1; }
  .drift-note { font-size: 11px; color: var(--ink-faint); margin-top: 6px; font-family: var(--font-mono); }

  @media (max-width: 900px) {
    .container { padding: 20px 16px 40px; }
    .header { grid-template-columns: 1fr; }
    .header-right { text-align: left; }
    .kpi-row { grid-template-columns: repeat(2, 1fr); }
    .backlog-grid { grid-template-columns: 1fr; }
    .usage-row { grid-template-columns: 1fr; }
    .token-grid { grid-template-columns: 1fr; }
    .readiness { grid-template-columns: 1fr; }
    .drift-row { grid-template-columns: 1fr; }
  }
</style>
</head>
<body>
<div class="container">

  <header class="header">
    <div class="header-left">
      <h1>__PROJECT_NAME__ <span class="small">— cc-forge dashboard</span></h1>
      <div class="meta">__PROJECT_META__</div>
    </div>
    <div class="header-right">
      <div class="pill-row">
        <span class="phase-pill"><span class="dot"></span>__PHASE_PILL__</span>
        <span class="stage-pill"><span class="dot"></span>__STAGE_PILL__</span>
      </div>
      <div class="gen-time">Generated __GEN_TIME__</div>
    </div>
  </header>

  <div class="kpi-row">
    <div class="kpi">
      <div class="kpi-label">Backlog overall</div>
      <div class="kpi-value">__KPI_BACKLOG__<span class="unit">%</span></div>
      <div class="kpi-trend">__KPI_BACKLOG_SUB__</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Phase exit</div>
      <div class="kpi-value">__KPI_PHASE_EXIT__</div>
      <div class="kpi-trend">__KPI_PHASE_EXIT_SUB__</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Active risks</div>
      <div class="kpi-value">__KPI_RISKS__</div>
      <div class="kpi-trend __KPI_RISKS_CLASS__">__KPI_RISKS_SUB__</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Hermes overhead</div>
      <div class="kpi-value">__KPI_HERMES__</div>
      <div class="kpi-trend">__KPI_HERMES_SUB__</div>
    </div>
  </div>

  <div class="tabs" role="tablist">
    <button class="tab active" data-tab="backlog" role="tab">Backlog <span class="badge">__BADGE_BACKLOG__</span></button>
    <button class="tab" data-tab="risks" role="tab">Risks <span class="badge">__BADGE_RISKS__</span></button>
    <button class="tab" data-tab="decisions" role="tab">Decisions <span class="badge">__BADGE_DECISIONS__</span></button>
    <button class="tab" data-tab="usage" role="tab">Usage</button>
  </div>

  <section class="panel active" id="panel-backlog">

    <div class="readiness">
      <div class="readiness-left">
        <div class="h">__READINESS_HEADING__</div>
        <div class="s">__READINESS_SUB__</div>
        <div class="readiness-track">
          <div class="readiness-fill" style="width: __OVERALL_PCT__%;"></div>
          <div class="readiness-marker" style="left: 100%;"></div>
        </div>
      </div>
      <div class="readiness-right">
        <div class="readiness-pct">__OVERALL_PCT__<span class="sm">%</span></div>
        <div class="readiness-verdict __READINESS_CLASS__">__READINESS_VERDICT__</div>
      </div>
    </div>

    <div class="exit-criteria" id="exit-criteria-section">
      <h3>Phase __PHASE_NUM__ exit criteria</h3>
      <div class="ec-sub">From PHASES.md · domain targets: __PHASE_EXIT_DOMAINS_MET__ / __PHASE_EXIT_DOMAINS_TOTAL__ met · exit-gate bullets are advisory</div>
      <ul id="exit-criteria-list"></ul>
    </div>

    <div class="drift-row">
      <div class="drift-card __OBS_ORPHAN_CLASS__">
        <div class="drift-label">Observed orphan items</div>
        <div class="drift-value">__OBS_ORPHANS__</div>
        <div class="drift-note">in-progress items with no Taskmaster ref</div>
      </div>
      <div class="drift-card __ORPHAN_CLASS__">
        <div class="drift-label">Logged orphan_task events</div>
        <div class="drift-value">__LOG_ORPHANS__</div>
        <div class="drift-note">from usage.log · Session B schema</div>
      </div>
      <div class="drift-card __MISSING_CLASS__">
        <div class="drift-label">Missing-coverage events</div>
        <div class="drift-value">__LOG_MISSING__</div>
        <div class="drift-note">findings without a template item</div>
      </div>
    </div>

    <h2 class="section-h">Completion by domain</h2>
    <p class="section-sub">10 domains · __APPLICABLE__ active items · __NA_COUNT__ not-applicable with decision records</p>

    <div class="backlog-grid" id="domain-grid"></div>

    <h2 class="section-h">Items</h2>
    <p class="section-sub">Filter by status to find what's in-flight or blocked</p>

    <div class="filter-row">
      <span class="filter-label">Status</span>
      <button class="chip active" data-filter="all">All</button>
      <button class="chip" data-filter="in-progress">In progress</button>
      <button class="chip" data-filter="not-started">Not started</button>
      <button class="chip" data-filter="done">Done</button>
      <button class="chip" data-filter="operator-action">Operator action</button>
      <button class="chip" data-filter="not-applicable">Not applicable</button>
    </div>

    <table class="item-table" id="item-table">
      <thead>
        <tr>
          <th style="width: 110px;">ID</th>
          <th>Outcome</th>
          <th style="width: 90px;">Owner</th>
          <th style="width: 60px;">Phase</th>
          <th style="width: 130px;">Status</th>
        </tr>
      </thead>
      <tbody id="item-tbody"></tbody>
    </table>
  </section>

  <section class="panel" id="panel-risks">
    <h2 class="section-h">Risk register</h2>
    <p class="section-sub">__BADGE_RISKS__ active risks · ordered by severity · auto-aggregated from RISKS.md</p>
    <div class="filter-row">
      <span class="filter-label">Severity</span>
      <button class="chip active" data-rfilter="all">All</button>
      <button class="chip" data-rfilter="crit">Critical</button>
      <button class="chip" data-rfilter="high">High</button>
      <button class="chip" data-rfilter="med">Medium</button>
      <button class="chip" data-rfilter="low">Low</button>
    </div>
    <div id="risk-list"></div>
  </section>

  <section class="panel" id="panel-decisions">
    <h2 class="section-h">Architecture decisions</h2>
    <p class="section-sub">__BADGE_DECISIONS__ decision records · from DECISIONS.md · search by title, context, or ID</p>
    <input type="text" class="adr-search" id="adr-search" placeholder="Search decisions — try &quot;auth&quot;, &quot;railway&quot;, or &quot;ADR-005&quot;" />
    <div id="adr-list"></div>
  </section>

  <section class="panel" id="panel-usage">
    <h2 class="section-h">Token &amp; framework usage</h2>
    <p class="section-sub">Claude Code raw tokens · Hermes framework overhead · session discipline · gate history</p>

    <div class="usage-row">
      <div class="panel-card">
        <div class="panel-card-h">Claude Code raw tokens</div>
        <div class="token-grid">
          <div>
            <div class="kpi-label">Input</div>
            <div class="token-big">__CC_INPUT__</div>
            <div class="token-sub">__CC_INPUT_SUB__</div>
          </div>
          <div>
            <div class="kpi-label">Output</div>
            <div class="token-big">__CC_OUTPUT__</div>
            <div class="token-sub">__CC_OUTPUT_SUB__</div>
          </div>
          <div>
            <div class="kpi-label">Cache read</div>
            <div class="token-big" style="color: var(--green);">__CC_CACHE__</div>
            <div class="token-sub">__CC_CACHE_SUB__</div>
          </div>
          <div>
            <div class="kpi-label">Est. cost</div>
            <div class="token-big">__CC_COST__</div>
            <div class="token-sub">at sonnet rates</div>
          </div>
        </div>
        <div class="token-note">__CC_NOTE__</div>
      </div>

      <div class="panel-card" style="border-left: 4px solid var(--accent);">
        <div class="panel-card-h">Hermes overhead (estimated)</div>
        <div class="token-grid">
          <div>
            <div class="kpi-label">CLAUDE.md context</div>
            <div class="token-big">__HERMES_CMD_CTX__</div>
            <div class="token-sub">__HERMES_CMD_CTX_SUB__</div>
          </div>
          <div>
            <div class="kpi-label">/hermes-* commands</div>
            <div class="token-big">__HERMES_CMDS__</div>
            <div class="token-sub">__HERMES_CMDS_SUB__</div>
          </div>
          <div>
            <div class="kpi-label">Persona gates</div>
            <div class="token-big">__HERMES_PERSONAS__</div>
            <div class="token-sub">__HERMES_PERSONAS_SUB__</div>
          </div>
          <div>
            <div class="kpi-label">Hermes share</div>
            <div class="token-big" style="color: var(--accent);">__HERMES_SHARE__</div>
            <div class="token-sub">__HERMES_SHARE_SUB__</div>
          </div>
        </div>
        <div class="token-note">Estimated from .cc-forge/usage.log · per-command weights × invocation counts · v2 will measure directly via hook</div>
      </div>
    </div>

    <div class="usage-row">
      <div class="panel-card">
        <div class="panel-card-h">Backlog trajectory</div>
        <div class="sparkline-wrap">
          <svg id="sparkline" viewBox="0 0 800 180" preserveAspectRatio="none" style="width:100%;height:100%;"></svg>
        </div>
        <div class="sparkline-x" id="sparkline-x"></div>
      </div>

      <div class="panel-card">
        <div class="panel-card-h">Hermes session discipline</div>
        <div class="stat-list">
          <div class="stat-row"><span class="stat-row-label">Sessions</span><span class="stat-row-val">__DISC_SESSIONS__</span></div>
          <div class="stat-row"><span class="stat-row-label">CLAUDE.md tokens</span><span class="stat-row-val">__DISC_CMD_TOKENS__</span></div>
          <div class="stat-row"><span class="stat-row-label">/compact runs</span><span class="stat-row-val">__DISC_COMPACT__</span></div>
          <div class="stat-row"><span class="stat-row-label">Argus last run</span><span class="stat-row-val">__DISC_ARGUS__</span></div>
          <div class="stat-row"><span class="stat-row-label">Drift events</span><span class="stat-row-val __DRIFT_CLASS__">__DISC_DRIFT__</span></div>
          <div class="stat-row"><span class="stat-row-label">Standards-strip events</span><span class="stat-row-val __STRIP_CLASS__">__DISC_STRIP__</span></div>
          <div class="stat-row"><span class="stat-row-label">Model distribution</span><span class="stat-row-val">__DISC_MODELS__</span></div>
        </div>
      </div>
    </div>

    <div class="usage-row">
      <div class="panel-card">
        <div class="panel-card-h">Command usage</div>
        <div class="stat-list" id="command-usage"></div>
      </div>

      <div class="panel-card">
        <div class="panel-card-h">Persona gate history</div>
        <table class="gate-table" id="gate-history"></table>
      </div>
    </div>
  </section>

  <footer class="footer">
    cc-forge dashboard v0.1 · generated by /hermes-dashboard · markdown is the source of truth · regenerate with one command
  </footer>
</div>

<script>
// ───── DATA ─────
const DATA = __DATA_JSON__;

const domains             = DATA.domains;
const items               = DATA.items;
const risks               = DATA.risks;
const adrs                = DATA.adrs;
const backlogTrajectory   = DATA.trajectory;
const exitCriteria        = DATA.exit_criteria;
const commandUsage        = DATA.command_usage;
const gateHistory         = DATA.gate_history;

// ───── RENDER ─────

function renderDomains() {
  const grid = document.getElementById('domain-grid');
  grid.innerHTML = domains.map(d => {
    const total = d.done + d.prog + d.todo + d.op + d.na;
    const fillClass = d.pct >= d.target ? 'complete' : d.pct >= Math.max(d.target * 0.5, 20) ? 'warn' : d.pct === 0 ? 'behind' : '';
    const targetClass = d.pct >= d.target ? 'met' : 'miss';
    const opPill = d.op > 0 ? `<span class="pill"><span class="dot dot-op"></span>${d.op} op-action</span>` : '';
    const naPill = d.na > 0 ? `<span class="pill"><span class="dot dot-na"></span>${d.na} n/a</span>` : '';
    const targetLine = d.target > 0
      ? `<div class="domain-target ${targetClass}">${d.pct}% / ${d.target}% target</div>`
      : `<div class="domain-target">${d.pct}% (no phase target)</div>`;
    const targetMark = d.target > 0
      ? `<div class="progress-target" style="left: ${d.target}%;"></div>`
      : '';
    return `
      <div class="domain-card">
        <div class="domain-head">
          <div>
            <div class="domain-num">${d.num}</div>
            <div class="domain-name">${d.name}</div>
          </div>
          <div>
            <div class="domain-pct">${d.pct}<span style="font-size:14px;color:var(--ink-soft);">%</span></div>
          </div>
        </div>
        ${targetLine}
        <div class="progress-bar">
          <div class="progress-fill ${fillClass}" style="width: ${d.pct}%;"></div>
          ${targetMark}
        </div>
        <div class="domain-meta">
          <span class="pill"><span class="dot dot-done"></span>${d.done} done</span>
          <span class="pill"><span class="dot dot-prog"></span>${d.prog} in-prog</span>
          <span class="pill"><span class="dot dot-todo"></span>${d.todo} todo</span>
          ${opPill}
          ${naPill}
        </div>
        <div class="domain-owner">Owner — ${d.owner}</div>
      </div>
    `;
  }).join('');
}

function statusClass(s) {
  return {
    'done': 'status-done',
    'in-progress': 'status-prog',
    'not-started': 'status-todo',
    'operator-action': 'status-op',
    'not-applicable': 'status-na',
  }[s] || 'status-todo';
}

function escapeHtml(s) {
  return String(s == null ? '' : s)
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function renderItems(filter = 'all') {
  const tbody = document.getElementById('item-tbody');
  const filtered = filter === 'all' ? items : items.filter(i => i.status === filter);
  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="5" class="empty-state">No items match this filter.</td></tr>`;
    return;
  }
  tbody.innerHTML = filtered.map(i => `
    <tr>
      <td class="item-id">${escapeHtml(i.id)}</td>
      <td>${escapeHtml(i.outcome || i.title)}</td>
      <td style="font-family: var(--font-mono); font-size: 12px; color: var(--ink-soft);">${escapeHtml(i.owner_short)}</td>
      <td style="font-family: var(--font-mono); font-size: 12px; color: var(--ink-faint);">${i.phase ? 'P' + i.phase : '—'}</td>
      <td><span class="status-tag ${statusClass(i.status)}">${i.status}</span></td>
    </tr>
  `).join('');
}

function renderRisks(filter = 'all') {
  const list = document.getElementById('risk-list');
  const sevName = { crit: 'Critical', high: 'High', med: 'Medium', low: 'Low' };
  const filtered = filter === 'all' ? risks : risks.filter(r => r.sev === filter);
  if (filtered.length === 0) {
    list.innerHTML = `<div class="empty-state">No risks at this severity.</div>`;
    return;
  }
  list.innerHTML = filtered.map(r => `
    <div class="risk-card ${r.sev}">
      <div>
        <div class="risk-sev">${sevName[r.sev] || r.sev}</div>
        <div class="risk-id">${escapeHtml(r.id)}</div>
      </div>
      <div>
        <div class="risk-title">${escapeHtml(r.title)}</div>
        <div class="risk-desc">${escapeHtml(r.desc)}</div>
        ${r.mit ? `<div class="risk-mitigation"><strong>Mitigation</strong>${escapeHtml(r.mit)}</div>` : ''}
      </div>
      <div class="risk-meta">
        <div>${escapeHtml(r.owner)}</div>
        ${r.review ? `<div>review ${escapeHtml(r.review)}</div>` : ''}
      </div>
    </div>
  `).join('');
}

function renderADRs(q = '') {
  const list = document.getElementById('adr-list');
  const query = q.toLowerCase().trim();
  const filtered = !query ? adrs : adrs.filter(a =>
    (a.title || '').toLowerCase().includes(query) ||
    (a.ctx   || '').toLowerCase().includes(query) ||
    (a.why   || '').toLowerCase().includes(query) ||
    (a.id    || '').toLowerCase().includes(query)
  );
  if (filtered.length === 0) {
    list.innerHTML = `<div class="empty-state">No decisions match "${escapeHtml(q)}".</div>`;
    return;
  }
  list.innerHTML = filtered.map(a => `
    <div class="adr">
      <div class="adr-head">
        <div>
          <span class="adr-num">${escapeHtml(a.id)}</span>
          ${a.date ? `<span class="adr-date" style="margin-left: 10px;">${escapeHtml(a.date)}</span>` : ''}
        </div>
        <span class="adr-status ${a.status}">${a.status}</span>
      </div>
      <div class="adr-title">${escapeHtml(a.title)}</div>
      ${a.ctx ? `<div class="adr-context">${escapeHtml(a.ctx)}</div>` : ''}
      ${a.why ? `<div class="adr-rationale"><strong>Rationale</strong>${escapeHtml(a.why)}</div>` : ''}
    </div>
  `).join('');
}

function renderExitCriteria() {
  const ul = document.getElementById('exit-criteria-list');
  if (!exitCriteria || exitCriteria.length === 0) {
    ul.innerHTML = '<li style="color: var(--ink-faint); font-style: italic;">No exit-gate bullets parsed from PHASES.md — domain targets still apply.</li>';
    return;
  }
  ul.innerHTML = exitCriteria.map(c => `<li>· ${escapeHtml(c)}</li>`).join('');
}

function renderCommandUsage() {
  const wrap = document.getElementById('command-usage');
  if (!commandUsage || commandUsage.length === 0) {
    wrap.innerHTML = '<div class="empty-state">No command history yet.</div>';
    return;
  }
  wrap.innerHTML = commandUsage.map(c => {
    const cls = c.count === 0 ? 'style="color: var(--ink-faint);"' : '';
    const txt = c.count === 0 ? '0 — never used' : c.count;
    return `<div class="stat-row"><span class="stat-row-label">${escapeHtml(c.cmd)}</span><span class="stat-row-val" ${cls}>${txt}</span></div>`;
  }).join('');
}

function renderGateHistory() {
  const t = document.getElementById('gate-history');
  if (!gateHistory || gateHistory.length === 0) {
    t.innerHTML = '<tr><td colspan="3" class="empty-state">No gate reviews recorded yet.</td></tr>';
    return;
  }
  t.innerHTML = gateHistory.map(g => {
    const verdicts = [];
    if (g.pass)        verdicts.push(`<span class="verdict p">${g.pass}P</span>`);
    if (g.conditional) verdicts.push(`<span class="verdict c">${g.conditional}C</span>`);
    if (g.block)       verdicts.push(`<span class="verdict b">${g.block}B</span>`);
    const verdictCell = g.count === 0
      ? `<td colspan="2" class="pco">never invoked</td>`
      : `<td class="pco">${g.count} reviews</td><td>${verdicts.join(' ')}</td>`;
    const personaStyle = g.count === 0 ? 'style="color: var(--ink-faint);"' : '';
    return `<tr><td class="persona" ${personaStyle}>${escapeHtml(g.persona)}</td>${verdictCell}</tr>`;
  }).join('');
}

function renderSparkline() {
  const svg = document.getElementById('sparkline');
  const xAxis = document.getElementById('sparkline-x');
  const data = backlogTrajectory;
  if (!data || data.length < 2) {
    svg.innerHTML = `<text x="400" y="90" text-anchor="middle" font-family="JetBrains Mono, monospace" font-size="11" fill="#8c8a7e">Not enough session data yet</text>`;
    xAxis.innerHTML = '';
    return;
  }
  const W = 800, H = 180, padL = 30, padR = 8, padT = 12, padB = 24;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  const maxV = 100;
  const points = data.map((d, i) => {
    const x = padL + (i / (data.length - 1)) * innerW;
    const y = padT + (1 - d.pct / maxV) * innerH;
    return { x, y, pct: d.pct, day: d.day };
  });
  let grid = '';
  for (let g = 0; g <= 100; g += 25) {
    const y = padT + (1 - g / 100) * innerH;
    grid += `<line x1="${padL}" x2="${W - padR}" y1="${y}" y2="${y}" stroke="#e5e1d4" stroke-width="0.5" stroke-dasharray="${g === 100 || g === 0 ? '0' : '2,3'}"/>`;
    grid += `<text x="${padL - 6}" y="${y + 3}" font-family="JetBrains Mono, monospace" font-size="9" fill="#8c8a7e" text-anchor="end">${g}%</text>`;
  }
  const linePath = points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(' ');
  const areaPath = linePath + ` L ${points[points.length-1].x} ${padT + innerH} L ${points[0].x} ${padT + innerH} Z`;
  const dots = points.map(p => `<circle cx="${p.x}" cy="${p.y}" r="3" fill="#1c1b18" stroke="#faf8f3" stroke-width="1.5"/>`).join('');
  const last = points[points.length - 1];
  const lastLabel = `<text x="${last.x}" y="${last.y - 10}" font-family="Fraunces, serif" font-size="14" fill="#1c1b18" text-anchor="end" font-weight="500">${last.pct}%</text>`;
  svg.innerHTML = `${grid}<path d="${areaPath}" fill="#1c1b18" fill-opacity="0.05"/><path d="${linePath}" stroke="#1c1b18" stroke-width="1.5" fill="none"/>${dots}${lastLabel}`;
  xAxis.innerHTML = data.filter((_, i) => i % Math.max(1, Math.floor(data.length / 6)) === 0).map(d => `<span>${escapeHtml(d.day)}</span>`).join('');
}

// ───── INTERACTIVITY ─────

document.querySelectorAll('.tab').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('panel-' + btn.dataset.tab).classList.add('active');
    if (btn.dataset.tab === 'usage') renderSparkline();
  });
});

document.querySelectorAll('[data-filter]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-filter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderItems(btn.dataset.filter);
  });
});

document.querySelectorAll('[data-rfilter]').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('[data-rfilter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderRisks(btn.dataset.rfilter);
  });
});

document.getElementById('adr-search').addEventListener('input', e => {
  renderADRs(e.target.value);
});

// ───── INIT ─────
renderDomains();
renderItems();
renderRisks();
renderADRs();
renderExitCriteria();
renderCommandUsage();
renderGateHistory();
</script>
</body>
</html>
"""


# Short owner mapping for the items table
OWNER_SHORT = {
    "product owner": "PO",
    "cto": "CTO",
    "cto + qa engineer": "CTO/QA",
    "qa engineer": "QA",
    "security auditor": "Sec",
    "sre engineer": "SRE",
    "ux expert": "UX",
    "legal / compliance": "Legal",
    "legal/compliance": "Legal",
    "growth agent": "Growth",
    "cfo": "CFO",
}


def short_owner(name: str) -> str:
    if not name:
        return "—"
    return OWNER_SHORT.get(name.strip().lower(), name.split()[0] if name else "—")


def render_html(
    project_root: Path,
    state: dict[str, Any],
    phase: dict[str, Any],
    domains: list[dict[str, Any]],
    overall: dict[str, Any],
    exit_progress: dict[str, Any],
    risks: list[dict[str, Any]],
    adrs: list[dict[str, Any]],
    usage: dict[str, Any],
    cc_raw: dict[str, Any],
    overhead: dict[str, Any],
    observed_orphans: int,
) -> str:
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    project_name = state.get("project_name") or project_root.name
    stack = state.get("stack")
    if isinstance(stack, dict):
        stack_str = " + ".join(f"{v}" for v in stack.values() if v)
    elif isinstance(stack, list):
        stack_str = " + ".join(stack)
    else:
        stack_str = "stack unknown"
    project_meta = stack_str.lower()

    cur_stage = state.get("current_stage")
    cur_stage_name = state.get("current_stage_name") or ""
    if cur_stage is not None:
        stage_pill = f"Stage {cur_stage:02d}" + (f" · {cur_stage_name}" if cur_stage_name else "")
    else:
        stage_pill = "stage unknown"

    phase_num = phase.get("number") or 0
    phase_name = phase.get("name") or "MVP"
    phase_pill = f"Phase {phase_num} · {phase_name}" if phase_num else "phase unknown"

    # Build domains array for the JS data block — adding targets + owners
    js_domains = []
    targets = phase.get("targets", {})
    for d in domains:
        js_domains.append({
            "num": d["num"],
            "name": d["name"],
            "pct": d["pct"],
            "done": d["done"],
            "prog": d["prog"],
            "todo": d["todo"],
            "op":   d["op"],
            "na":   d["na"],
            "owner": d["owner"],
            "target": int(targets.get(d["num"], 0)),
        })

    # Flatten items for items table
    js_items = []
    for d in domains:
        for it in d["items"]:
            js_items.append({
                "id":       it["id"],
                "title":    it["title"],
                "outcome":  it["outcome"],
                "owner":    it["owner"],
                "owner_short": short_owner(it["owner"]),
                "phase":    it["phase"],
                "status":   it["status"],
                "domain":   d["num"],
            })

    # Trajectory: derive a day label from ts
    trajectory_js = []
    for pt in usage.get("trajectory", []):
        ts = pt.get("ts", "")
        day = ts[:10] if ts else ""
        trajectory_js.append({"day": day, "pct": int(pt["pct"])})

    # Command usage list
    all_known_cmds = list({
        "/hermes-status", "/hermes-next", "/hermes-gate-review", "/hermes-phase-gate",
        "/hermes-argus", "/hermes-backlog", "/hermes-backlog-init", "/hermes-dashboard",
        "/hermes-deploy", "/hermes-research", "/hermes-clean", "/hermes-quality",
        "/hermes-report",
    } | set(usage.get("commands", {}).keys()))
    cmd_usage_list = sorted(
        [{"cmd": c, "count": int(usage.get("commands", {}).get(c, 0))} for c in all_known_cmds],
        key=lambda x: (-x["count"], x["cmd"]),
    )

    # Gate history (per persona)
    persona_order = [
        "cto", "security-auditor", "qa-engineer", "sre-engineer",
        "ux-expert", "product-owner", "legal-compliance",
        "argus", "cfo", "growth-agent", "market-analyst", "research-agent",
    ]
    persona_display = {
        "cto": "CTO",
        "security-auditor": "Security Auditor",
        "qa-engineer": "QA Engineer",
        "sre-engineer": "SRE Engineer",
        "ux-expert": "UX Expert",
        "product-owner": "Product Owner",
        "legal-compliance": "Legal / Compliance",
        "argus": "Argus",
        "cfo": "CFO",
        "growth-agent": "Growth Agent",
        "market-analyst": "Market Analyst",
        "research-agent": "Research Agent",
    }
    gate_history_js = []
    for p in persona_order:
        c = usage.get("persona_counts", {}).get(p, 0)
        outcomes = usage.get("persona_outcomes", {}).get(p, {})
        gate_history_js.append({
            "persona": persona_display.get(p, p),
            "count": c,
            "pass": outcomes.get("PASS", 0),
            "conditional": outcomes.get("CONDITIONAL", 0),
            "block": outcomes.get("BLOCK", 0),
        })

    data_json = to_js({
        "domains": js_domains,
        "items": js_items,
        "risks": risks,
        "adrs": adrs,
        "trajectory": trajectory_js,
        "exit_criteria": phase.get("exit_criteria", []),
        "command_usage": cmd_usage_list,
        "gate_history": gate_history_js,
    })

    # KPIs
    backlog_sub = f"{overall['done']}/{overall['applicable']} done · phase target weighted"
    phase_exit_kpi = f"{exit_progress['domains_met']}/{exit_progress['domains_total']}"
    phase_exit_sub = f"domains meeting phase {phase_num} target"

    high_risks = sum(1 for r in risks if r["sev"] == "high")
    crit_risks = sum(1 for r in risks if r["sev"] == "crit")
    med_risks = sum(1 for r in risks if r["sev"] == "med")
    risks_kpi_sub = f"{crit_risks} crit · {high_risks} high · {med_risks} med"
    if crit_risks > 0:
        risks_class = "bad"
    elif high_risks > 0:
        risks_class = "warn"
    else:
        risks_class = ""

    if overhead["share_pct"] is not None:
        hermes_kpi = f"{overhead['share_pct']:.0f}<span class='unit'>%</span>"
        hermes_sub = f"{humanize_number(overhead['hermes_total'])} of {humanize_number(overhead['cc_total'])} tokens"
    else:
        hermes_kpi = f"{humanize_number(overhead['hermes_total'])}"
        hermes_sub = "tokens — CC raw unavailable, share not computed"

    # Readiness banner
    if phase_num >= 4:
        readiness_heading = f"Phase {phase_num} ({phase_name}) readiness"
        readiness_sub = "Approaching public availability — all domain bars in scope"
    elif phase_num > 0:
        readiness_heading = f"Phase {phase_num} ({phase_name}) readiness"
        readiness_sub = f"Domain bars rebased to phase {phase_num} targets · see PHASES.md"
    else:
        readiness_heading = "Backlog readiness"
        readiness_sub = "Run /hermes-phase-gate to set the current phase"

    if exit_progress["domains_total"] == 0:
        readiness_verdict = "phase targets unavailable"
        readiness_class = ""
    elif exit_progress["domains_met"] >= exit_progress["domains_total"]:
        readiness_verdict = "ready to advance"
        readiness_class = "green"
    elif exit_progress["domains_met"] >= exit_progress["domains_total"] - 2:
        missing = exit_progress["domains_total"] - exit_progress["domains_met"]
        readiness_verdict = f"{missing} domain{'s' if missing != 1 else ''} blocking"
        readiness_class = "amber"
    else:
        missing = exit_progress["domains_total"] - exit_progress["domains_met"]
        readiness_verdict = f"{missing} domains blocking"
        readiness_class = "red"

    # Drift cards
    def drift_class(n: int) -> str:
        if n == 0:
            return "ok"
        if n <= 2:
            return "warn"
        return "bad"

    log_orphans = usage["drift"]["orphan_task"]
    log_missing = usage["drift"]["missing_coverage"]
    log_strip = usage["drift"]["standards_strip_detected"]

    # CC raw token panel
    if cc_raw["available"]:
        cc_input  = humanize_number(cc_raw["input"])
        cc_output = humanize_number(cc_raw["output"])
        cc_cache  = humanize_number(cc_raw["cache_read"])
        cc_cost   = f"${cc_raw['cost']:.2f}"
        avg_in    = cc_raw["input"]  // max(cc_raw["sessions"], 1)
        avg_out   = cc_raw["output"] // max(cc_raw["sessions"], 1)
        if cc_raw["input"] + cc_raw["cache_read"] > 0:
            hit_rate = round(cc_raw["cache_read"] / (cc_raw["input"] + cc_raw["cache_read"]) * 100)
        else:
            hit_rate = 0
        cc_input_sub  = f"avg {humanize_number(avg_in)} / session"
        cc_output_sub = f"avg {humanize_number(avg_out)} / session"
        cc_cache_sub  = f"{hit_rate}% hit rate"
        cc_note       = cc_raw["note"]
    else:
        cc_input = cc_output = cc_cache = "—"
        cc_cost = "—"
        cc_input_sub = cc_output_sub = cc_cache_sub = "—"
        cc_note = "raw token data unavailable on this machine · ~/.claude/projects/<hash>/ not found"

    # Hermes overhead breakdown
    hermes_cmd_ctx     = humanize_number(overhead["claude_md_tokens"])
    hermes_cmd_ctx_sub = f"{overhead['estimated_turns']} turns × 600 tok"
    hermes_cmds        = humanize_number(overhead["command_tokens"])
    hermes_cmds_sub    = f"{overhead['command_invocations']} invocations"
    hermes_personas    = humanize_number(overhead["persona_tokens"])
    hermes_personas_sub = f"{overhead['persona_invocations']} reviews"
    if overhead["share_pct"] is not None:
        hermes_share = f"{overhead['share_pct']:.0f}%"
        hermes_share_sub = f"${overhead['hermes_total'] * 3.0 / 1_000_000 + overhead['hermes_total'] * 15.0 / 1_000_000:.2f} approx"
    else:
        hermes_share = "—"
        hermes_share_sub = "raw CC tokens unavailable"

    # Session discipline values
    disc_sessions = str(usage["sessions"])
    cmt = usage.get("claude_md_tokens_seen")
    disc_cmd_tokens = f"{cmt} / 600" if cmt else "—"
    disc_compact = f"{usage['compact_runs']} / {usage['sessions']} sessions" if usage["sessions"] else "—"
    if usage["last_argus"]:
        try:
            last_t = dt.datetime.fromisoformat(usage["last_argus"].rstrip("Z"))
            delta = dt.datetime.utcnow() - last_t
            if delta.days == 0:
                disc_argus = "today"
            elif delta.days == 1:
                disc_argus = "1 day ago"
            else:
                disc_argus = f"{delta.days} days ago"
        except (ValueError, TypeError):
            disc_argus = usage["last_argus"][:10]
    else:
        disc_argus = "never"

    total_drift = usage["drift"]["argus_drift"]
    disc_drift = str(total_drift)
    drift_class_val = "warn" if total_drift > 0 else ""

    disc_strip = str(log_strip)
    strip_class = "bad" if log_strip > 0 else ""

    if usage["model_distribution"]:
        total_models = sum(usage["model_distribution"].values())
        parts = []
        for m, c in sorted(usage["model_distribution"].items(), key=lambda x: -x[1]):
            pct = round(c / total_models * 100)
            short = m.split("-")[1].capitalize() if "-" in m else m
            parts.append(f"{short} {pct}%")
        disc_models = " · ".join(parts[:3])
    else:
        disc_models = "—"

    # Replacement table
    replacements = {
        "__PROJECT_NAME__": project_name,
        "__PROJECT_META__": project_meta,
        "__PHASE_PILL__": phase_pill,
        "__STAGE_PILL__": stage_pill,
        "__GEN_TIME__": now,
        "__KPI_BACKLOG__": str(overall["pct"]),
        "__KPI_BACKLOG_SUB__": backlog_sub,
        "__KPI_PHASE_EXIT__": phase_exit_kpi,
        "__KPI_PHASE_EXIT_SUB__": phase_exit_sub,
        "__KPI_RISKS__": str(len(risks)),
        "__KPI_RISKS_CLASS__": risks_class,
        "__KPI_RISKS_SUB__": risks_kpi_sub if risks else "no risks recorded",
        "__KPI_HERMES__": hermes_kpi,
        "__KPI_HERMES_SUB__": hermes_sub,
        "__BADGE_BACKLOG__": str(overall["applicable"]),
        "__BADGE_RISKS__": str(len(risks)),
        "__BADGE_DECISIONS__": str(len(adrs)),
        "__READINESS_HEADING__": readiness_heading,
        "__READINESS_SUB__": readiness_sub,
        "__OVERALL_PCT__": str(overall["pct"]),
        "__READINESS_CLASS__": readiness_class,
        "__READINESS_VERDICT__": readiness_verdict,
        "__PHASE_NUM__": str(phase_num),
        "__PHASE_EXIT_DOMAINS_MET__": str(exit_progress["domains_met"]),
        "__PHASE_EXIT_DOMAINS_TOTAL__": str(exit_progress["domains_total"]),
        "__APPLICABLE__": str(overall["applicable"]),
        "__NA_COUNT__": str(overall["na"]),
        "__OBS_ORPHAN_CLASS__": drift_class(observed_orphans),
        "__OBS_ORPHANS__": str(observed_orphans),
        "__ORPHAN_CLASS__": drift_class(log_orphans),
        "__LOG_ORPHANS__": str(log_orphans),
        "__MISSING_CLASS__": drift_class(log_missing),
        "__LOG_MISSING__": str(log_missing),
        "__CC_INPUT__": cc_input,
        "__CC_INPUT_SUB__": cc_input_sub,
        "__CC_OUTPUT__": cc_output,
        "__CC_OUTPUT_SUB__": cc_output_sub,
        "__CC_CACHE__": cc_cache,
        "__CC_CACHE_SUB__": cc_cache_sub,
        "__CC_COST__": cc_cost,
        "__CC_NOTE__": cc_note,
        "__HERMES_CMD_CTX__": hermes_cmd_ctx,
        "__HERMES_CMD_CTX_SUB__": hermes_cmd_ctx_sub,
        "__HERMES_CMDS__": hermes_cmds,
        "__HERMES_CMDS_SUB__": hermes_cmds_sub,
        "__HERMES_PERSONAS__": hermes_personas,
        "__HERMES_PERSONAS_SUB__": hermes_personas_sub,
        "__HERMES_SHARE__": hermes_share,
        "__HERMES_SHARE_SUB__": hermes_share_sub,
        "__DISC_SESSIONS__": disc_sessions,
        "__DISC_CMD_TOKENS__": disc_cmd_tokens,
        "__DISC_COMPACT__": disc_compact,
        "__DISC_ARGUS__": disc_argus,
        "__DISC_DRIFT__": disc_drift,
        "__DRIFT_CLASS__": drift_class_val,
        "__DISC_STRIP__": disc_strip,
        "__STRIP_CLASS__": strip_class,
        "__DISC_MODELS__": disc_models,
        "__DATA_JSON__": data_json,
    }

    out = HTML_TEMPLATE
    for k, v in replacements.items():
        out = out.replace(k, str(v))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate cc-forge dashboard.html")
    p.add_argument("--project-root", default=".", help="Project root (default: cwd)")
    p.add_argument("--output", default=None, help="Output path (default: <root>/dashboard.html)")
    p.add_argument("--quiet", action="store_true", help="Suppress stdout summary")
    args = p.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    output = Path(args.output) if args.output else project_root / "dashboard.html"

    state = parse_state_json(project_root)
    master = parse_backlog_master(project_root)
    current_phase = state.get("current_phase") or master.get("phase") or 1
    phase = parse_phases_md(project_root, current_phase)

    domains = [parse_backlog_domain(project_root, dn) for dn in DOMAIN_NUMBERS]
    overall = compute_overall_pct(domains)
    exit_progress = compute_phase_exit_progress(phase, domains)

    risks = parse_risks_md(project_root)
    adrs = parse_decisions_md(project_root)
    usage = parse_usage_log(project_root)
    cc_raw = parse_cc_conversations(project_root)

    # Token weights for overhead estimate. Spec §4.3: canonical at
    # ${CLAUDE_PLUGIN_ROOT}/token-weights.json (Layer 1); per-project
    # overrides at .cc-forge/overrides/token-weights.json. Override
    # consulted first, fall back to canonical, fall back to in-code defaults.
    weights_raw = None
    override_path = project_root / ".cc-forge" / "overrides" / "token-weights.json"
    if override_path.is_file():
        weights_raw = read_text_safe(override_path)
    if not weights_raw:
        plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT")
        if plugin_root:
            canonical_path = Path(plugin_root) / "token-weights.json"
            if canonical_path.is_file():
                weights_raw = read_text_safe(canonical_path)
    if not weights_raw:
        # Last-resort fallback for dev-tree runs where neither override nor
        # plugin root is reachable. Look in the script's own ancestor tree.
        legacy_path = Path(__file__).resolve().parent.parent / "token-weights.json"
        weights_raw = read_text_safe(legacy_path)
    try:
        weights = json.loads(weights_raw) if weights_raw else {}
    except json.JSONDecodeError:
        weights = {}
    overhead = compute_hermes_overhead(usage, weights, cc_raw)

    observed_orphans = compute_observed_orphans(domains)

    html = render_html(
        project_root=project_root,
        state=state,
        phase=phase,
        domains=domains,
        overall=overall,
        exit_progress=exit_progress,
        risks=risks,
        adrs=adrs,
        usage=usage,
        cc_raw=cc_raw,
        overhead=overhead,
        observed_orphans=observed_orphans,
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")

    if not args.quiet:
        share = f"~{overhead['share_pct']:.0f}%" if overhead["share_pct"] is not None else "n/a"
        print("━" * 60)
        print(f"  HERMES  ·  Dashboard generated")
        print("━" * 60)
        print(f"  ✓ Wrote: {output}")
        print()
        print(f"  Phase:    {phase['number']} {phase['name']}   "
              f"(exit progress: {exit_progress['domains_met']}/{exit_progress['domains_total']} domains)")
        print(f"  Backlog:  {overall['pct']}%               ({overall['applicable']} applicable items)")
        print(f"  Risks:    {len(risks)} active            "
              f"({sum(1 for r in risks if r['sev']=='crit')} crit, "
              f"{sum(1 for r in risks if r['sev']=='high')} high, "
              f"{sum(1 for r in risks if r['sev']=='med')} med)")
        print(f"  Drift:    orphan_task={usage['drift']['orphan_task']}  "
              f"missing_coverage={usage['drift']['missing_coverage']}  "
              f"standards_strip={usage['drift']['standards_strip_detected']}")
        print(f"  Hermes:   {share} overhead     (estimated — v2 will measure directly)")
        print()
        print(f"  Open {output.relative_to(project_root)} in your browser.")
        print("━" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
