#!/bin/bash
# hermes-migrate-backlog-format.sh — Catalogue/backlog content migration.
#
# Transforms backlog-item field lines from bold form (`**Field:** value`)
# to canonical list-item form (`- Field: value`) per spec §3.2.
#
# Standalone, re-runnable, supports --dry-run. Invoked by the main
# pre-plugin → plugin migration in step 8, and can also be invoked
# directly to migrate just the catalogue.
#
# Per the Session 0 v3 design: step 8 enforces TRANSFORM FIDELITY (the
# transform preserved every field, every value, with no stray markers)
# rather than END-STATE CONFORMANCE (which §3.2 explicitly grandfathers
# for one transition cycle for missing `Standard` fields).
#
# Two failure classes:
#   - FIDELITY: a field that existed before is missing/malformed after.
#     Halt + recommend rollback.
#   - CARRY-FORWARD: a required field was already missing before the
#     transform (pre-existing data gap). Log, surface in report, do not halt.
#
# Required-field bucketing in the report:
#   - "Grandfathered per §3.2": missing Standard only (spec blesses this).
#   - "Pre-existing violation, needs cleanup": missing Outcome / Phase /
#     Status / Owner / Evidence. Spec does not bless these; report names
#     them for the next sprint.

set -u

MODE="apply"
TARGET_DIR=""
REPORT_FILE=""

usage() {
  cat <<EOF
Usage: $0 [--dry-run] [--report FILE] <target-directory>

Transforms backlog-item field lines from **Field:** value (bold) to
- Field: value (list-item) per spec §3.2 across every *.md file in
<target-directory>.

  --dry-run        Print the diff that would be applied; make no changes.
  --report FILE    Write the migration report to FILE (default: stdout).
  --help           This message.
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) MODE="dry-run"; shift;;
    --report)  REPORT_FILE="$2"; shift 2;;
    --help|-h) usage; exit 0;;
    --*)       echo "unknown flag: $1" >&2; usage; exit 1;;
    *)         TARGET_DIR="$1"; shift;;
  esac
done

if [ -z "$TARGET_DIR" ]; then
  echo "error: target directory required" >&2
  usage
  exit 1
fi
if [ ! -d "$TARGET_DIR" ]; then
  echo "error: $TARGET_DIR is not a directory" >&2
  exit 1
fi

# Required fields per §3.2.
REQUIRED_FIELDS="Outcome Standard Phase Status Owner Evidence"
GRANDFATHERED_FIELD="Standard"

# Tempdir for before/after snapshots used in fidelity checks.
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

# Per-item field-set extraction: emits one line "<basename>::<ID>::<field>::<value>"
# for each <field>: <value> line under each `### [ID]` block.
# Uses basename only so pre-transform (in target dir) and post-transform (in
# tempdir) tuples are key-comparable.
extract_fields() {
  local file="$1"
  local form="$2"    # "bold" or "list"
  python3 - "$file" "$form" <<'PYEOF'
import os, re, sys
path, form = sys.argv[1], sys.argv[2]
key = os.path.basename(path)
if form == "bold":
    pat = re.compile(r"^\*\*([A-Z][A-Za-z-]*):\*\*\s*(.+?)\s*$")
elif form == "list":
    pat = re.compile(r"^- ([A-Z][A-Za-z-]*):\s*(.+?)\s*$")
else:
    sys.exit(2)
header = re.compile(r"^###\s+\[([A-Z][A-Z0-9-]+)\]")
with open(path, encoding="utf-8") as fh:
    cur_id = None
    for ln in fh:
        m = header.match(ln)
        if m:
            cur_id = m.group(1)
            continue
        if cur_id is None:
            continue
        fm = pat.match(ln)
        if fm:
            print(f"{key}::{cur_id}::{fm.group(1)}::{fm.group(2)}")
PYEOF
}

# Apply the transform to a single file. Writes output to stdout (dry-run)
# or back to the file (apply).
transform_file() {
  local file="$1"
  python3 - "$file" <<'PYEOF'
import re, sys
path = sys.argv[1]
# Match `**Field:** value` only when it's a backlog field line — anchored at
# start of line, field name matches [A-Z][A-Za-z-]*, value is the rest.
pat = re.compile(r"^\*\*([A-Z][A-Za-z-]*):\*\*\s*(.*?)\s*$", re.MULTILINE)
with open(path, encoding="utf-8") as fh:
    src = fh.read()
out = pat.sub(lambda m: f"- {m.group(1)}: {m.group(2)}", src)
sys.stdout.write(out)
PYEOF
}

# ─────────────────────────────────────────────────────────────────────────
# Pass 1 — capture pre-transform field-sets for every catalogue file.
# ─────────────────────────────────────────────────────────────────────────
echo "▸ Migrating backlog format in: $TARGET_DIR"
echo "  Mode: $MODE"
echo ""
echo "▸ Pass 1: capturing pre-transform field-sets..."

pre_fields_file="$TMPDIR/pre_fields.tsv"
> "$pre_fields_file"
catalogue_files=()
for f in "$TARGET_DIR"/*.md; do
  [ -f "$f" ] || continue
  catalogue_files+=("$f")
  extract_fields "$f" "bold" >> "$pre_fields_file"
done
pre_count=$(wc -l < "$pre_fields_file" | tr -d ' ')
echo "  ✓ captured $pre_count field/value pairs across ${#catalogue_files[@]} files"

# ─────────────────────────────────────────────────────────────────────────
# Pass 2 — apply (or dry-run) the transform and capture post-state.
# ─────────────────────────────────────────────────────────────────────────
echo ""
echo "▸ Pass 2: applying transform..."

# For each file, produce the transformed content. Dry-run holds it in a
# parallel tree; apply writes it back to the file.
post_dir="$TMPDIR/post"
mkdir -p "$post_dir"

for f in "${catalogue_files[@]}"; do
  base=$(basename "$f")
  transform_file "$f" > "$post_dir/$base"
done

# Note: write-to-disk is deferred until AFTER the fidelity gate passes.
# Whether dry-run or apply, we hold the post content in $post_dir and only
# commit it once fidelity has been verified.

if [ "$MODE" = "dry-run" ]; then
  echo "  (dry-run — diff below; transform held in tempdir, not yet applied)"
  echo ""
  for f in "${catalogue_files[@]}"; do
    base=$(basename "$f")
    if ! diff -u "$f" "$post_dir/$base" > /dev/null; then
      echo "─── $f ───"
      diff -u "$f" "$post_dir/$base" | head -30
      echo ""
    fi
  done
else
  echo "  ✓ transform generated for ${#catalogue_files[@]} files (held in tempdir; commits after fidelity gate)"
fi

# ─────────────────────────────────────────────────────────────────────────
# Pass 3 — capture post-transform field-sets from the post tree.
# ─────────────────────────────────────────────────────────────────────────
echo ""
echo "▸ Pass 3: capturing post-transform field-sets..."

post_fields_file="$TMPDIR/post_fields.tsv"
> "$post_fields_file"
for f in "${catalogue_files[@]}"; do
  base=$(basename "$f")
  extract_fields "$post_dir/$base" "list" >> "$post_fields_file"
done
post_count=$(wc -l < "$post_fields_file" | tr -d ' ')
echo "  ✓ captured $post_count field/value pairs post-transform"

# ─────────────────────────────────────────────────────────────────────────
# Pass 4 — fidelity gate + carry-forward audit (the core of step 8).
# ─────────────────────────────────────────────────────────────────────────
echo ""
echo "▸ Pass 4: fidelity gate + carry-forward audit..."

# Sort both for set-comparison.
sort "$pre_fields_file"  > "$TMPDIR/pre.sorted"
sort "$post_fields_file" > "$TMPDIR/post.sorted"

# Items present pre-transform that should exist post-transform with identical
# (field, value) pairs. Any (file, id, field, value) tuple in pre but not in
# post is a FIDELITY failure.
lost=$(comm -23 "$TMPDIR/pre.sorted" "$TMPDIR/post.sorted")

# New tuples that didn't exist pre-transform = the transform invented fields.
# Should never happen; would mean the regex matched something unexpected.
extra=$(comm -13 "$TMPDIR/pre.sorted" "$TMPDIR/post.sorted")

# Value cleanliness — value must not contain `**` anywhere. The regex
# substitution can leave stray markers if, e.g., a field value originally
# was `**Standard:** **NIST 800-57` (unlikely but bound to be checked).
dirty=$(awk -F'::' '$4 ~ /\*\*/ {print $0}' "$post_fields_file")

# ─── Build report ───
report=$(cat <<EOF
═══════════════════════════════════════════════════════════════
  Catalogue format migration report
═══════════════════════════════════════════════════════════════

  Files processed:       ${#catalogue_files[@]}
  Field/value pairs:     $pre_count (pre) / $post_count (post)
  Mode:                  $MODE

EOF
)

# ─── FIDELITY checks ───
fidelity_failed=0

if [ -n "$lost" ]; then
  fidelity_failed=1
  report="$report
  ✗ FIDELITY FAILURE — fields lost or value-drifted by transform:
$(echo "$lost" | sed 's/^/      /')
"
fi
if [ -n "$extra" ]; then
  fidelity_failed=1
  report="$report
  ✗ FIDELITY FAILURE — fields invented by transform (regex too greedy?):
$(echo "$extra" | sed 's/^/      /')
"
fi
if [ -n "$dirty" ]; then
  fidelity_failed=1
  report="$report
  ✗ FIDELITY FAILURE — post-transform values contain stray markers:
$(echo "$dirty" | sed 's/^/      /')
"
fi

if [ "$fidelity_failed" -eq 0 ]; then
  report="$report
  ✓ FIDELITY PASSED — every field and value carried through unchanged.
"
fi

# ─── CARRY-FORWARD audit (does not halt) ───
# For each item in the post-state, check which required fields are missing.
# Bucket "grandfathered per §3.2" (Standard) vs "pre-existing violation".

grandfathered=""
preexisting_gaps=""

# Build a map of (file, id) → set of fields present (post-transform).
items_seen=$(awk -F'::' '{print $1"::"$2}' "$post_fields_file" | sort -u)
while IFS= read -r item; do
  [ -z "$item" ] && continue
  file_part="${item%%::*}"
  id_part="${item##*::}"
  fields_present=$(awk -F'::' -v f="$file_part" -v i="$id_part" \
    '$1==f && $2==i {print $3}' "$post_fields_file" | sort -u)
  for required in $REQUIRED_FIELDS; do
    if ! echo "$fields_present" | grep -qx "$required"; then
      if [ "$required" = "$GRANDFATHERED_FIELD" ]; then
        grandfathered="${grandfathered}      ${file_part}::${id_part} missing $required
"
      else
        preexisting_gaps="${preexisting_gaps}      ${file_part}::${id_part} missing $required
"
      fi
    fi
  done
done <<< "$items_seen"

if [ -n "$grandfathered" ]; then
  report="$report
  ⚠ Grandfathered per §3.2 — missing Standard (spec blesses for one transition cycle):
${grandfathered}"
fi
if [ -n "$preexisting_gaps" ]; then
  report="$report
  ⚠ Pre-existing violations — NOT grandfathered, needs cleanup next sprint:
${preexisting_gaps}"
fi

if [ -z "$grandfathered" ] && [ -z "$preexisting_gaps" ]; then
  report="$report
  ✓ No pre-existing data gaps — every item carries all six required fields.
"
fi

report="$report
═══════════════════════════════════════════════════════════════
"

# ─── Emit report ───
if [ -n "$REPORT_FILE" ]; then
  echo "$report" > "$REPORT_FILE"
  echo "▸ Report written to: $REPORT_FILE"
else
  echo "$report"
fi

# ─── Halt-on-fidelity-failure BEFORE committing the write ───
if [ "$fidelity_failed" -ne 0 ]; then
  echo "▸ EXIT 2: fidelity failure. No files modified (transform held in tempdir was discarded)." >&2
  echo "  Run with --dry-run to inspect the proposed transform." >&2
  exit 2
fi

# ─── Fidelity passed — commit the write (only when applying) ───
if [ "$MODE" = "apply" ]; then
  for f in "${catalogue_files[@]}"; do
    base=$(basename "$f")
    cp "$post_dir/$base" "$f"
  done
  echo "▸ Fidelity passed. Transform committed to ${#catalogue_files[@]} files."
else
  echo "▸ Dry-run complete (fidelity would pass). Re-run without --dry-run to apply."
fi
exit 0
