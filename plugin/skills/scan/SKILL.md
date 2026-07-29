---
name: scan
description: Launches a Qualys VM scan and follows it to completion - launch, poll for state, then fetch results. Use when the user asks to scan hosts or IPs for vulnerabilities, to check whether a running scan has finished, or to retrieve the results of a scan that has already been launched.
---

# Launch and follow a Qualys VM scan

A Qualys scan is **asynchronous**. `qualys_launch_vm_scan` returns a scan
reference immediately and the scan then runs for minutes to hours. Fetching
before it finishes returns nothing useful. Treat launch, poll and fetch as
three separate steps, possibly across separate sessions.

## Workflow

```
- [ ] 1. Confirm the target and option profile with the user
- [ ] 2. Launch, and report the scan reference immediately
- [ ] 3. Poll until the state is terminal
- [ ] 4. Fetch results
```

### 1. Confirm before launching

A scan consumes subscription capacity and touches live hosts. Before calling
`qualys_launch_vm_scan`, confirm with the user:

- the target — `ip` (addresses or ranges), `asset_groups`, `asset_group_ids`
  or `fqdn`. At least one is required.
- the option profile — exactly one of `option_id` or `option_title`. These
  are mutually exclusive and one is required; the tool rejects both mistakes.

If the user has not named an option profile, ask. Do not guess an ID.

### 2. Launch and report the reference

Report the returned `scan_ref` in your reply **as soon as you have it**,
before doing anything else. If the session ends or polling is interrupted,
that reference is the only way back to the scan.

### 3. Poll

Qualys has no scan-status endpoint. Poll by listing with the reference:

```
qualys_list_vm_scans(scan_ref="scan/1358285558.36992")
```

States: `Queued`, `Loading`, `Running`, `Paused`, `Finished`, `Canceled`,
`Error`. Terminal states are `Finished`, `Canceled` and `Error`.

**Poll at most once a minute.** Scans routinely run for hours; a tight loop
buys nothing and trips the platform's limits. If the user is present, prefer
reporting the current state and letting them ask again over polling in a
loop — an agent that sits blocked for an hour is not useful to anyone.

**Check `sub_state` before reporting a finished scan as clean.** `Finished`
with `sub_state="No_Host"` means the scan ran to completion without reaching
any host — empty results mean the target was wrong, not that the hosts are
healthy. Report that as a targeting failure and say what the scan was
pointed at, rather than as an all-clear.

### 4. Fetch

```
qualys_fetch_vm_scan_results(scan_ref="scan/1358285558.36992")
```

Valid only for `Finished`, `Canceled`, `Paused` and `Error`. Results from a
canceled or errored scan are partial — label them as partial when reporting.

## Rate limits

Qualys signals limits with **HTTP 409**, not 429. Two distinct cases:

- **Rate limit** — carries a wait period. Honour it before retrying.
- **Concurrency limit** — carries no wait period at all, and takes
  precedence when both apply. It means too many calls are in flight, so
  waiting a fixed interval is not the fix; reduce parallelism instead.

Either way, back off rather than retrying immediately.

## Managing a running scan

`qualys_manage_vm_scan` takes `cancel`, `pause`, `resume` and `delete`.

`cancel` and `delete` are irreversible against a live subscription and will
prompt the user for confirmation — that prompt is deliberate. Never invoke
either to "clean up" or "retry" without the user explicitly asking. A
canceled scan cannot be resumed; only a paused one can.

## Reporting

State the scan reference, the state you observed, and when you observed it.
If you polled once and the scan was still running, say that plainly rather
than implying the scan failed or that results are unavailable.
