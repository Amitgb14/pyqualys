#!/usr/bin/env bash
# PreToolUse guard for qualys_manage_vm_scan.
#
# `delete` permanently removes a scan and its results, and `cancel` cannot
# be undone - both act on a live Qualys subscription. This escalates those
# two actions to an explicit user prompt. `pause` and `resume` are
# reversible and pass straight through.
#
# Fails SAFE: anything this script cannot confidently classify is escalated
# rather than allowed. A guard that silently allows on error is worse than
# no guard, because it reads as protection in review.
#
# Takes no credentials and interpolates no ${user_config.*} - those are
# rejected in shell-form hook commands precisely because the value would
# reach a shell.

set -uo pipefail

exec python3 -c '
import json
import sys

DESTRUCTIVE = ("cancel", "delete")
REVERSIBLE = ("pause", "resume")


def escalate(reason):
    json.dump({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }, sys.stdout)
    sys.exit(0)


try:
    payload = json.load(sys.stdin)
except Exception:
    escalate("Qualys scan guard could not parse the hook payload, so it "
             "cannot confirm this action is reversible. Escalating.")

action = (payload.get("tool_input") or {}).get("action")

if action in REVERSIBLE:
    # Reversible - defer to the normal permission flow.
    sys.exit(0)

if action in DESTRUCTIVE:
    scan_ref = (payload.get("tool_input") or {}).get("scan_ref", "unknown")
    if action == "delete":
        detail = ("permanently removes the scan and its results from the "
                  "Qualys subscription. This cannot be undone.")
    else:
        detail = ("stops a running scan on the Qualys subscription. This "
                  "cannot be undone, and partial results may be lost.")
    escalate("Qualys scan guard: action=%s on %s %s Confirm before "
             "proceeding." % (action, scan_ref, detail))

escalate("Qualys scan guard does not recognise action=%r on "
         "qualys_manage_vm_scan, so it cannot confirm the action is "
         "reversible. Escalating." % (action,))
'
