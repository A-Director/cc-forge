#!/bin/bash
# hermes-prompt-submit.sh — fires on every UserPromptSubmit (§2.8).
#
# v1.0.0 (Session 0): stub. The full per-prompt framing + intake-bypass
# detection lands in Session D. Shipping the registration now so the plugin
# manifest is complete and the hook surface is wired; this stub does no work
# and is safe to be invoked on every prompt.
#
# When Session D extends this script, the hook's job becomes:
#   1. Examine the prompt for intake markers (new requirement, feature ask).
#   2. Compute an intake_bypass risk score.
#   3. Emit a structured per-prompt frame if useful.
#   4. Log bypass_detected events if the score crosses threshold.

set -u
# Stub — exit cleanly without modifying context or producing output.
exit 0
