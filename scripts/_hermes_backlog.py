#!/usr/bin/env python3
"""_hermes_backlog.py — the ONE canonical parser for the §3.2 backlog-item format.

Spec §3 warned that six subsystems read/write the backlog and demanded "one
canonical parser per format." Before Session F, Argus, the dashboard, and the
intake classifier each rolled their own regex — and they diverged (the
dashboard accepted a lowercase `- status:` line that Argus rejected: same
file, two truths). This module is the single source of truth they now import.

Two jobs:

1. **Parse** the strict §3.2 form: `### [ID]` item headers with `- Field: value`
   list lines. One regex pair, shared by every consumer.

2. **Fail loud on the silent-empty class.** During CLARK's migration a parser
   hit table-form input, returned zero items from a NON-EMPTY file, and the
   migration reported a vacuous "FIDELITY PASSED on 0/0 pairs" — a no-op that
   nearly passed for success. The rule encoded here: parsing an item-bearing
   file and extracting zero items is an ERROR, surfaced loudly (raise /
   non-zero exit), never a silent empty return. A genuinely empty or
   scaffolding-only file legitimately yields zero items and stays quiet.

Stdlib only. Importable by the Python consumers; also runnable as a CLI so
the bash migration can inherit the same fail-loud guard
(`python3 _hermes_backlog.py --assert-nonempty <file>...`, exit 2 on a
silent-empty file).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

# ── The §3.2 contract — strict. This is the canonical form; consumers that
#    want a different shape map FROM these, they do not re-define the regex. ──
# Item header: ### [SEC-UNI-001] optional title
# group(1) = ID (the only group the strict parser reads); group(2) = optional
# trailing title (the classifier uses it as an Outcome fallback). Capturing
# the title keeps this the single header regex for every consumer.
ITEM_HEADER_PATTERN = re.compile(r"^### \[([A-Z][A-Z0-9-]+)\]\s*(.*)$")
# Field line: - Field: value  (Field is Capitalized per §3.2 — strict)
FIELD_PATTERN = re.compile(r"^- ([A-Z][A-Za-z-]*):\s*(.+)$")

# Required fields per §3.2. `Standard` is grandfathered for one transition
# cycle (§3.2 line 644) — consumers list missing-Standard separately.
REQUIRED_FIELDS = {"Outcome", "Standard", "Phase", "Status", "Owner", "Evidence"}
GRANDFATHERED_FIELD = "Standard"

VALID_STATUS_VALUES = {
    "not-started", "in-progress", "done",
    "not-applicable", "operator-action", "intake-pending",
}
VALID_PHASE_VALUES = {"1", "2", "3", "4", "5", "—"}

# Canonical Owner vocabulary (§3.2) — one identifier per backlog-owning
# persona, matching the persona definitions in personas/ exactly (filename ==
# name: == Owner). An Owner outside this set can't route to a persona, so it's
# a format violation (kind="owner_not_recognised"). market-analyst /
# research-agent / argus are personas but NOT backlog owners — ceo owns the
# market/research domains; argus is the deterministic watcher.
VALID_OWNERS = {
    "security-sme", "cto", "qa-sme", "sre-sme", "ux-sme",
    "product-owner", "legal-sme", "cfo", "growth-sme", "ceo",
}

# Markers that say "this file carries items in SOME form" — used by the
# fail-loud guard to tell an item-bearing file (drift) from a legitimately
# empty/scaffolding-only one (fine). Catches the forms a non-canonical file
# takes: canonical headers, the legacy bold form, and table rows that carry an
# item ID (CLARK's table-form case).
_BOLD_FIELD = re.compile(r"^\*\*[A-Z][A-Za-z -]*:\*\*")
_TABLE_ID_ROW = re.compile(r"^\|.*[A-Z]{2,}-[A-Z0-9-]+")


class BacklogParseError(Exception):
    """Raised when an item-bearing file parses to zero items — the
    silent-empty class. Loud by construction; never swallowed."""


def is_item_bearing(text: str) -> bool:
    """True if the text contains backlog-item content in *any* form
    (canonical, bold, or table-with-IDs). Distinguishes real content the
    strict parser may have failed to read from a legitimately empty file."""
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### ["):
            return True
        if _BOLD_FIELD.match(line):
            return True
        if _TABLE_ID_ROW.match(line):
            return True
    return False


def parse_backlog_items(text: str,
                        *, source: str | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Strict §3.2 parser. Returns (items, violations).

    Each item: {"id", "fields": {Field: value}, "line_start", "line_end"}.
    Each violation is one of:
      {"kind": "field_not_recognised", "line": int, "text": str}
      {"kind": "required_field_missing", "id": str, "field": str, "grandfathered": bool}
      {"kind": "no_items", "detail": str}

    This is the single canonical implementation — Argus, the dashboard, and
    the classifier all route through it. `source` is carried into messages
    only; it does not change parsing.
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
        for required in REQUIRED_FIELDS:
            if required not in cur_fields:
                violations.append({
                    "kind": "required_field_missing",
                    "id": cur_id,
                    "field": required,
                    "grandfathered": required == GRANDFATHERED_FIELD,
                })
        # Owner-vocabulary enforcement (§3.2): a present Owner must be one of
        # the canonical identifiers, or it can't route to a persona. Only
        # checked when Owner is present — absence is already flagged above.
        owner = cur_fields.get("Owner")
        if owner is not None and owner not in VALID_OWNERS:
            violations.append({
                "kind": "owner_not_recognised",
                "id": cur_id,
                "owner": owner,
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
            continue
        if not line.strip():
            continue
        # A "- Capital…" line inside an item block must be a valid field.
        # Sub-bullets and prose are allowed without flag.
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


def parse_or_raise(text: str, *, source: str | None = None) -> list[dict[str, Any]]:
    """Parse and enforce the fail-loud rule: an item-bearing file that yields
    zero items raises BacklogParseError. Use this anywhere a vacuous empty
    result would be mistaken for "nothing to do" — migration fidelity checks,
    dashboard counts, Argus's format check."""
    items, _ = parse_backlog_items(text, source=source)
    if not items and is_item_bearing(text):
        where = source or "backlog file"
        raise BacklogParseError(
            f"{where}: non-empty / item-bearing content but parsed 0 items. "
            f"Expected '### [ID]' headers with '- Field: value' lines per §3.2 — "
            f"this looks like table-form or bold-form the canonical parser does "
            f"not accept. Refusing to report a vacuous empty result (this is the "
            f"silent-empty class that nearly passed a no-op migration)."
        )
    return items


def _cli(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Canonical §3.2 backlog parser / fail-loud guard.")
    p.add_argument("--assert-nonempty", nargs="+", metavar="FILE",
                   help="Exit 2 if any item-bearing file parses to zero items.")
    args = p.parse_args(argv)

    if args.assert_nonempty:
        failed = False
        for fp in args.assert_nonempty:
            path = Path(fp)
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as e:
                print(f"error: cannot read {fp}: {e}", file=sys.stderr)
                failed = True
                continue
            try:
                items = parse_or_raise(text, source=fp)
                print(f"ok: {fp} — {len(items)} item(s)")
            except BacklogParseError as e:
                print(f"FAIL (silent-empty): {e}", file=sys.stderr)
                failed = True
        return 2 if failed else 0

    p.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
