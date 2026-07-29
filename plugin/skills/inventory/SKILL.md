---
name: inventory
description: Lists the scanned host assets in a Qualys subscription with pagination, filtering by IP range, asset group or host ID. Use when the user asks what assets or hosts they have, wants an inventory or asset count, needs host IDs to feed into vulnerability triage, or asks when a host was last scanned.
---

# Qualys asset inventory

Answers "what do we have" using `qualys_list_hosts`. Also the way to get
host IDs for `/pyqualys:triage`.

## Pick the cheapest detail level that answers the question

`details` controls response size, and the difference is large:

| Value | Returns |
|---|---|
| `None` | host IDs only — cheapest, right for feeding triage |
| `Basic` | ID, IP, tracking method, DNS, NetBIOS, OS, last scan |
| `Basic/AGs` | Basic plus asset group membership |
| `All` | everything, including cloud metadata — large |
| `All/AGs` | All plus asset groups |

Default to `Basic`. Only reach for `All` when the user asks for something it
uniquely contains.

## Pagination

Responses are paginated. When `truncated` is true, more records exist —
pass the returned `next_id_min` as `id_min` to get the next page.

Decide deliberately how far to go, and **report what you actually
retrieved**. "1,000 hosts (first 10 pages, more remain)" is a usable answer;
"1,000 hosts" when there are 8,000 is a wrong one. If the user wants a total
count and the set is large, say how many pages you walked.

## Tracking method affects counting

`TRACKING_METHOD` is `IP`, `DNS`, `NETBIOS`, `EC2` or `Cloud Agent`. The
same physical machine can appear more than once under different tracking
methods — a cloud agent install alongside a network-scanned IP, for
instance. Before reporting a host count as an asset count, note the
tracking methods present. Do not silently de-duplicate; surface it and let
the user decide.

Cloud-tracked hosts also put their real identity in `EC2_INSTANCE_ID` or
the DNS field rather than in a meaningful IP, so an IP-keyed summary of an
EC2-heavy subscription reads as noise.

## Staleness

`LAST_VULN_SCAN_DATETIME` is when the host was last scanned for
vulnerabilities. A host that has not been scanned in months has detection
data that is equally old — that matters when its results feed triage. When
asked for an inventory, flag hosts whose last scan is conspicuously old
rather than presenting all rows as equally current.

## Filters

- `ids` — host IDs or ranges, e.g. `"1-100,205"`
- `ips` — addresses or ranges
- `ag_ids` — asset group IDs

## Rate limits

Qualys signals limits with **HTTP 409**, not 429. A rate-limit block carries
a wait period; a concurrency block carries none and means too many calls are
in flight. Paging aggressively through a large inventory is the common way
to hit the second one — page steadily rather than in parallel.
