"""
Hermes intake module (Session D, Phase C).

Programmatic intake management — used by /hermes-intake and the
verification battery. Owns:

  - intake_id allocation: monotonic, never reused, scans existing log
    for max and returns max+1 (even rejected/withdrawn IDs stay
    allocated per spec §3.7).
  - intake-log.md append: writes the section with YAML frontmatter +
    markdown body.
  - format validation: classification.other requires classification_detail;
    disposition values are closed; classification values are closed
    except for the explicit `other` escape.
  - intake_step event emission to usage.log per §3.6.

Spec §3.7:
  - intake_id ^INTAKE-\\d{3,4}$
  - disposition ∈ {accepted, deferred-to-phase-N, rejected, withdrawn}
  - classification ∈ {feature, bug, improvement, spike, other}
       other requires classification_detail
  - personas_consulted array
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

INTAKE_ID_PATTERN = re.compile(r"^INTAKE-(\d{3,4})$")
INTAKE_HEADER_PATTERN = re.compile(r"^##\s+(INTAKE-\d{3,4})\b")

VALID_CLASSIFICATIONS = {"feature", "bug", "improvement", "spike", "other"}
VALID_DISPOSITIONS_PREFIX = ("accepted", "rejected", "withdrawn")
DEFERRED_PATTERN = re.compile(r"^deferred-to-phase-([1-5])$")


class IntakeValidationError(ValueError):
    """Raised when an intake entry fails format validation. Carries the
    specific violation so the writer (persona or operator) gets a
    pointed error message it can act on per the §3.8 write-path
    validate-and-retry contract — Phase D mechanics."""

    def __init__(self, violations: list[str]):
        self.violations = violations
        super().__init__("; ".join(violations))


def find_all_intake_ids(log_path: Path) -> list[int]:
    """Return every numeric portion of every INTAKE-NNN heading found
    in the log, in file order. Used to verify monotonicity and
    allocate the next id."""
    if not log_path.is_file():
        return []
    nums: list[int] = []
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return nums
    for line in text.split("\n"):
        m = INTAKE_HEADER_PATTERN.match(line)
        if m:
            id_str = m.group(1)
            # Re-match against the id pattern for the digit group
            n = INTAKE_ID_PATTERN.match(id_str)
            if n:
                nums.append(int(n.group(1)))
    return nums


def next_intake_id(log_path: Path) -> str:
    """Return the next intake_id as INTAKE-NNN (zero-padded to 3
    digits). Never reuses an id, even from rejected/withdrawn intakes
    — they keep their id, the next is always max+1."""
    existing = find_all_intake_ids(log_path)
    next_num = (max(existing) + 1) if existing else 1
    # Spec allows 3 or 4 digits. Use 3 until we hit 1000.
    return f"INTAKE-{next_num:03d}" if next_num < 1000 else f"INTAKE-{next_num:04d}"


def validate_entry(entry: dict[str, Any]) -> None:
    """Raise IntakeValidationError with the precise field-level
    violation(s) if the entry doesn't satisfy §3.7. This is the
    structured error the Phase D validate-and-retry loop feeds back
    to the persona."""
    violations: list[str] = []

    intake_id = entry.get("intake_id", "")
    if not isinstance(intake_id, str) or not INTAKE_ID_PATTERN.match(intake_id):
        violations.append(
            f"intake_id must match ^INTAKE-\\d{{3,4}}$; got {intake_id!r}")

    classification = entry.get("classification", "")
    if classification not in VALID_CLASSIFICATIONS:
        violations.append(
            f"classification must be one of {sorted(VALID_CLASSIFICATIONS)}; "
            f"got {classification!r}")
    elif classification == "other":
        detail = entry.get("classification_detail", "")
        if not isinstance(detail, str) or not detail.strip():
            violations.append(
                "classification 'other' requires non-empty "
                "classification_detail (free text describing what it is)")

    disposition = entry.get("disposition", "")
    valid_disp = (
        disposition in VALID_DISPOSITIONS_PREFIX
        or (isinstance(disposition, str) and DEFERRED_PATTERN.match(disposition))
    )
    if not valid_disp:
        violations.append(
            "disposition must be one of accepted | rejected | withdrawn | "
            f"deferred-to-phase-{{1-5}}; got {disposition!r}")

    pc = entry.get("personas_consulted")
    if not isinstance(pc, list):
        violations.append(
            f"personas_consulted must be an array; got {type(pc).__name__}")
    elif not all(isinstance(p, str) for p in pc):
        violations.append(
            "personas_consulted must contain only strings")

    requirement = entry.get("requirement", "")
    if not isinstance(requirement, str) or not requirement.strip():
        violations.append("requirement (body text) must be non-empty")

    if violations:
        raise IntakeValidationError(violations)


def _yaml_block(d: dict[str, Any]) -> str:
    """Emit a small YAML block. Keep dependency-free — values we write
    are scalars, arrays of strings, and ISO timestamps."""
    lines = ["---"]
    for k, v in d.items():
        if isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}: [{', '.join(str(x) for x in v)}]")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def append_intake(project_root: Path, *, intake_id: str, title: str,
                  classification: str, classification_detail: str | None,
                  disposition: str, target_phase: int | None,
                  personas_consulted: list[str], requirement: str,
                  triage_decision: str = "", outcome: str = "",
                  validate: bool = True) -> Path:
    """Append a new intake event to .cc-forge/intake-log.md. Validates
    by default. Returns the log path."""
    entry = {
        "intake_id": intake_id,
        "classification": classification,
        "disposition": disposition,
        "personas_consulted": personas_consulted,
        "requirement": requirement,
    }
    if classification == "other":
        entry["classification_detail"] = classification_detail
    if target_phase is not None:
        entry["target_phase"] = target_phase

    if validate:
        validate_entry(entry)

    intake_log = project_root / ".cc-forge" / "intake-log.md"
    intake_log.parent.mkdir(parents=True, exist_ok=True)

    iso_ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    fm: dict[str, Any] = {
        "date": iso_ts,
        "intake_id": intake_id,
        "disposition": disposition,
        "classification": classification,
    }
    if classification == "other":
        fm["classification_detail"] = classification_detail
    if target_phase is not None:
        fm["target_phase"] = target_phase
    fm["personas_consulted"] = personas_consulted

    body_parts = [f"## {intake_id} — {title}", "", _yaml_block(fm), "",
                  "### Requirement", "", requirement.strip(), ""]
    if triage_decision.strip():
        body_parts.extend(["### Triage decision", "", triage_decision.strip(), ""])
    if outcome.strip():
        body_parts.extend(["### Outcome", "", outcome.strip(), ""])
    body_parts.append("---")
    body_parts.append("")

    with intake_log.open("a", encoding="utf-8") as fh:
        if intake_log.stat().st_size > 0:
            fh.write("\n")
        fh.write("\n".join(body_parts))

    log_intake_step(project_root, intake_id, "appended", "ok")
    return intake_log


def log_intake_step(project_root: Path, intake_id: str, step: str,
                    result: str) -> None:
    """Emit an intake_step event to usage.log per §3.6."""
    usage_log = project_root / ".cc-forge" / "usage.log"
    iso_ts = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entry = {
        "ts": iso_ts,
        "type": "intake_step",
        "data": {"intake_id": intake_id, "step": step, "result": result},
    }
    try:
        with usage_log.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def verify_monotonicity(log_path: Path) -> dict[str, Any]:
    """Doctor-facing check: every INTAKE-NNN heading is monotonically
    increasing AND no id is reused. Returns a structured report."""
    ids = find_all_intake_ids(log_path)
    out: dict[str, Any] = {"ids": ids, "violations": []}
    seen: set[int] = set()
    for prev, curr in zip(ids, ids[1:]):
        if curr <= prev:
            out["violations"].append(
                f"not monotonic: INTAKE-{prev:03d} → INTAKE-{curr:03d}")
    for n in ids:
        if n in seen:
            out["violations"].append(f"INTAKE-{n:03d} reused")
        seen.add(n)
    out["ok"] = not out["violations"]
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Hermes intake helper (Phase C)")
    sub = p.add_subparsers(dest="cmd", required=True)

    nid = sub.add_parser("next-id", help="Print next intake_id")
    nid.add_argument("--project-root", default=".")

    add = sub.add_parser("append", help="Append intake to log (JSON on stdin)")
    add.add_argument("--project-root", default=".")
    add.add_argument("--allow-invalid", action="store_true",
                     help="Skip validation (for testing the validator only)")

    val = sub.add_parser("validate", help="Validate intake JSON on stdin")

    mon = sub.add_parser("verify", help="Verify monotonicity of an intake log")
    mon.add_argument("--project-root", default=".")

    args = p.parse_args(argv)

    if args.cmd == "next-id":
        log_path = Path(args.project_root).resolve() / ".cc-forge" / "intake-log.md"
        print(next_intake_id(log_path))
        return 0

    if args.cmd == "append":
        try:
            data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            print(f"error: invalid JSON on stdin: {e}", file=sys.stderr)
            return 2
        project_root = Path(args.project_root).resolve()
        try:
            path = append_intake(
                project_root,
                intake_id=data.get("intake_id") or next_intake_id(
                    project_root / ".cc-forge" / "intake-log.md"),
                title=data.get("title", "(untitled)"),
                classification=data.get("classification", ""),
                classification_detail=data.get("classification_detail"),
                disposition=data.get("disposition", ""),
                target_phase=data.get("target_phase"),
                personas_consulted=data.get("personas_consulted") or [],
                requirement=data.get("requirement", ""),
                triage_decision=data.get("triage_decision", ""),
                outcome=data.get("outcome", ""),
                validate=(not args.allow_invalid),
            )
            print(json.dumps({"appended": True, "path": str(path),
                              "intake_id": data.get("intake_id") or
                              find_all_intake_ids(path)[-1]}))
            return 0
        except IntakeValidationError as e:
            print(json.dumps({"appended": False, "violations": e.violations}),
                  file=sys.stderr)
            return 3

    if args.cmd == "validate":
        try:
            data = json.loads(sys.stdin.read())
        except json.JSONDecodeError as e:
            print(json.dumps({"valid": False,
                              "violations": [f"invalid JSON: {e}"]}))
            return 2
        try:
            validate_entry(data)
            print(json.dumps({"valid": True, "violations": []}))
            return 0
        except IntakeValidationError as e:
            print(json.dumps({"valid": False, "violations": e.violations}))
            return 3

    if args.cmd == "verify":
        log_path = Path(args.project_root).resolve() / ".cc-forge" / "intake-log.md"
        rep = verify_monotonicity(log_path)
        print(json.dumps(rep, indent=2))
        return 0 if rep["ok"] else 4

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
