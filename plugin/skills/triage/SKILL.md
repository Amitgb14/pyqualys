---
name: triage
description: Ranks Qualys vulnerability detections into a prioritised remediation list by severity, confirmation type and spread across hosts. Use when the user asks what to fix first, wants their vulnerabilities triaged or prioritised, asks about detections on a host or IP range, or asks how exposed they are to a specific QID.
---

# Triage Qualys detections

Turns `qualys_list_host_detections` output into "what should I fix first".

## Two defaults that silently narrow the answer

Qualys applies these server-side. Neither is overridden by the tool, so
unless you pass them explicitly the data you triage is already filtered:

- **Only `New`, `Active` and `Re-Opened` detections are returned.** Pass
  `status="New,Active,Re-Opened,Fixed"` to include remediated ones.
- **Information-gathered QIDs are hidden.** Pass `show_igs=1` to include
  them.

For a triage question the defaults are usually right — the user wants open
problems, not fixed ones or informational noise. **Say which filter you
used.** "23 open detections" and "23 detections including fixed" are
different claims about the same subscription.

## Ranking

Order by, in this priority:

1. **Severity**, 5 (highest) down to 1.
2. **Type** — rank `Confirmed` above `Potential` at equal severity. A
   potential detection means Qualys inferred the vulnerability rather than
   proving it, so it may not be real.
3. **Spread** — a QID on 40 hosts is one fix with 40× the payoff of a QID
   on one host. Group by QID and count affected hosts before ranking.

`STATUS` also matters when reporting: `New` is newly discovered,
`Re-Opened` means it was fixed and came back — which usually points at a
configuration that reverts, and is worth calling out separately.

## What this data does not contain

Detections carry the **QID, severity, type, status and dates — no title, no
CVE, no patch guidance.** Those live in the Qualys KnowledgeBase, which this
plugin does not expose.

Do not invent a description for a QID. Report the QID number and let the
user look it up, or say plainly that the title is not available through this
plugin. A plausible-sounding but wrong CVE mapping is worse than no mapping:
it sends someone to patch the wrong thing.

## Scope the query

Unfiltered triage across a whole subscription returns an unusable volume.
Narrow first:

- `ids` — host IDs, from `/pyqualys:inventory`
- `ips` — addresses or ranges
- `qids` — when the user asks about one specific vulnerability
- `severities` — e.g. `"4-5"` for the urgent tier
- `detection_updated_since` — for "what changed this week"

`truncation_limit` defaults to 25 because these responses are large. When
`truncated` comes back true there is more data; pass `next_id_min` to
continue. Page deliberately, and **state how much you actually looked at** —
"the 25 most recent" is honest, "your vulnerabilities" is not.

## Report format

```markdown
## Priority

| QID | Severity | Type | Hosts | Status |
|-----|----------|------|-------|--------|
| 90194 | 5 | Confirmed | 12 | New |

Scope: severities 4-5, open detections only (New/Active/Re-Opened),
first 25 records.
```

Lead with the count and the scope, then the table. If a QID number has no
title available, leave it as a number rather than filling the gap.
