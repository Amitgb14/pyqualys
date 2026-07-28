# Qualys VM plugin for Claude Code

Wraps the [`pyqualys`](https://github.com/Amitgb14/pyqualys) MCP server so you can launch and
triage Qualys VM scans from Claude Code without hand-wiring environment variables.

## Requirements

- **[`uv`](https://docs.astral.sh/uv/)** must be installed and on your `PATH`. The plugin runs the
  server with `uvx --python 3.12`, which provisions its own interpreter. This matters because the
  MCP Python SDK requires Python 3.10+ and many systems still ship 3.9 — `uvx` sidesteps that
  entirely. If `uvx` is missing, the server will not start.
- A Qualys account with API access.

## Install

```
/plugin marketplace add Amitgb14/pyqualys
/plugin install pyqualys@pyqualys
```

On enable you'll be prompted for three values:

| Field | Notes |
| :--- | :--- |
| **Qualys API URL** | Per-POD. Find yours under **Help → About** in the Qualys UI. The default (`qualysapi.qualys.com`) is US Platform 1 — if you're on QG2, QG3, EU, etc. the default will fail to authenticate. |
| **Qualys username** | Prefer a dedicated account with the narrowest role that permits scan launch and read. |
| **Qualys password** | Marked `sensitive`, so it goes to your OS keychain — never to `settings.json`. |

Credentials reach the server as environment variables. They are never passed as tool arguments and
never appear in tool output.

## Tools

| Tool | What it does |
| :--- | :--- |
| `qualys_launch_vm_scan` | Launch a VM scan against IPs or asset groups |
| `qualys_list_vm_scans` | List scans; filter by reference to check status |
| `qualys_fetch_vm_scan_results` | Fetch results for a finished scan |
| `qualys_manage_vm_scan` | Cancel, pause, resume or delete a scan — **guarded, see below** |
| `qualys_list_hosts` | List host assets, with pagination |
| `qualys_list_host_detections` | Pull VMDR detections (the vulnerability findings) |

### Scan launch is asynchronous

`qualys_launch_vm_scan` returns a scan *reference* immediately — not results. The scan itself can
take hours. Poll with `qualys_list_vm_scans` filtered by that reference, then fetch once it's
finished.

Poll with backoff, not in a tight loop. Qualys signals rate and concurrency limits with **HTTP
409**, not 429, and those limits are **per subscription** — aggressive polling can exhaust the API
budget for your whole security team, not just your session.

### Destructive actions are gated

`qualys_manage_vm_scan` with `action=cancel` or `action=delete` triggers a `PreToolUse` hook that
escalates to an explicit permission prompt. `delete` permanently removes a scan and its results;
`cancel` stops a running scan and cannot be undone. `pause` and `resume` are reversible and pass
through without a prompt.

The guard fails safe: if it cannot parse the payload or does not recognise the action, it escalates
rather than allowing.

## Local development

The plugin pins `pyqualys[mcp]==0.1.0` from PyPI. To develop against a local checkout instead, edit
`.mcp.json` to point at your working tree:

```json
{
  "mcpServers": {
    "qualys": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "/path/to/pyqualys[mcp]", "pyqualys-mcp"],
      "env": {
        "QUALYS_API_URL": "${user_config.qualys_api_url}",
        "QUALYS_USERNAME": "${user_config.qualys_username}",
        "QUALYS_PASSWORD": "${user_config.qualys_password}"
      }
    }
  }
}
```

Then load it without installing:

```
claude --plugin-dir ./plugin
/reload-plugins          # after each edit
claude plugin validate ./plugin
```

## Caveats

The Qualys endpoint versions this build targets (`api/3.0` for scan list, `api/5.0` for the host
endpoints) were derived from vendor documentation and verified against mocks, not against a live
subscription. Confirm behaviour on a non-production subscription before relying on it.
