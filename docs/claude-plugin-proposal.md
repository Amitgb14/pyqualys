# Proposal: `pyqualys` Claude Code plugin

**Status:** Draft for review
**Date:** 2026-07-28
**Depends on:** PR #2 (`feat/vm-scan-api-mcp`) — the MCP server and the six tools it exposes

---

## 1. Why a plugin, when we already ship an MCP server

PR #2 already gives a user a working Qualys MCP server. They can wire it up today by hand: install
`pyqualys[mcp]`, export three environment variables, and paste an `mcpServers` block into their
config. So the plugin is not what makes the tools *exist*. It is what makes them *usable and
shareable*.

Concretely, a plugin buys four things the bare MCP server cannot:

| Problem with the bare MCP server | What the plugin does |
| :--- | :--- |
| Credentials live in shell env vars, typically in `.zshrc` or a committed `.env` | `userConfig` prompts at enable time and stores the password in the **OS keychain** |
| Every user hand-writes the same `mcpServers` JSON | Ships `.mcp.json`; install is `/plugin install` |
| Six low-level tools, no workflow — the model has to be told *how* to triage | Skills encode the launch → poll → fetch → triage loop |
| `qualys_manage_vm_scan` can **delete** and **cancel** scans with no confirmation | A `PreToolUse` hook gates destructive actions |

That last row is the one I would lead with. We are shipping a tool that can cancel a running
vulnerability scan in someone's production subscription. The plugin is the only layer where we can
put a guardrail in front of it.

---

## 2. Hard prerequisite (blocking)

**`pyqualys` 0.1.0 is not on PyPI.** The latest published release is **0.0.4**, which predates all of
PR #2. The `.mcp.json` committed in PR #2 says:

```json
"args": ["--python", "3.12", "--from", "pyqualys[mcp]", "pyqualys-mcp"]
```

Run today, `uvx` resolves `pyqualys[mcp]` to 0.0.4, which has no `mcp` extra and no `pyqualys-mcp`
entry point. **It fails.** So:

> **P0: merge PR #2, then publish 0.1.0 to PyPI.** Nothing in this proposal works until that
> happens. The `python -m build` fix in PR #2 (setup.py no longer imports the package it builds)
> is what unblocks the release.

Until 0.1.0 is live, the plugin can be developed and tested against a local checkout by pointing
`.mcp.json` at a path instead of PyPI, but it cannot be distributed.

---

## 3. Repository layout

Recommendation: **keep the plugin in this repo**, under `plugin/`, and make this repo its own
marketplace. One repo, one release cadence, and the plugin version can track the library version
that it pins.

```
pyqualys/                                  # this repo = the marketplace
├── .claude-plugin/
│   └── marketplace.json                   # catalog: lists the one plugin
├── plugin/                                # the plugin root
│   ├── .claude-plugin/
│   │   └── plugin.json                    # manifest (ONLY this file goes in .claude-plugin/)
│   ├── .mcp.json                          # bundled Qualys MCP server
│   ├── skills/
│   │   ├── scan/SKILL.md                  # /pyqualys:scan
│   │   ├── triage/SKILL.md                # /pyqualys:triage
│   │   └── inventory/SKILL.md             # /pyqualys:inventory
│   ├── agents/
│   │   └── qualys-analyst.md
│   ├── hooks/
│   │   └── hooks.json                     # destructive-action guard
│   └── README.md
└── pyqualys/                              # the library, unchanged
```

Two structural rules from the docs that are easy to get wrong:

- **Only `plugin.json` goes inside `.claude-plugin/`.** `skills/`, `agents/`, `hooks/` and
  `.mcp.json` all sit at the plugin root. This is the single most common plugin bug.
- The marketplace's `.claude-plugin/marketplace.json` sits at the **repo** root; the plugin's
  `.claude-plugin/plugin.json` sits at the **plugin** root. Different directories, similar names.

---

## 4. The manifest, and why `userConfig` is the centerpiece

```json
{
  "name": "pyqualys",
  "displayName": "Qualys VM",
  "version": "0.1.0",
  "description": "Launch and triage Qualys VM scans, list hosts, and pull VMDR detections",
  "author": { "name": "Amit Ghadge", "email": "amitg.b14@gmail.com" },
  "repository": "https://github.com/Amitgb14/pyqualys",
  "license": "MIT",
  "keywords": ["qualys", "vulnerability", "vmdr", "security"],

  "userConfig": {
    "qualys_api_url": {
      "type": "string",
      "title": "Qualys API URL",
      "description": "Your platform's API base URL, e.g. https://qualysapi.qg2.apps.qualys.com/",
      "default": "https://qualysapi.qualys.com/",
      "required": true
    },
    "qualys_username": {
      "type": "string",
      "title": "Qualys username",
      "description": "A user with API access. Use a dedicated read-mostly API account.",
      "required": true
    },
    "qualys_password": {
      "type": "string",
      "title": "Qualys password",
      "description": "Stored in your OS keychain, never in settings.json",
      "sensitive": true,
      "required": true
    }
  }
}
```

`sensitive: true` is the important flag. It masks the input and routes the value to the macOS
Keychain (or `~/.claude/.credentials.json` where no keychain exists) rather than to
`settings.json`. Non-sensitive values land in `pluginConfigs` in user settings.

One constraint worth designing around now rather than discovering later: Claude Code reads
`pluginConfigs` **only** from user settings, `--settings`, and managed settings. It deliberately
ignores a project's `.claude/settings.json`, precisely so a cloned repo cannot inject credentials
into a plugin's MCP config. So we cannot ship a pre-filled config in the repo for convenience —
and we should not want to.

There is a real Qualys-specific wrinkle here: **the API URL is per-platform.** A user on QG2 US
who accepts the `qualysapi.qualys.com` default will authenticate against the wrong platform and get
confusing failures. The `description` should spell out how to find the right POD URL, and the
`scan` skill should surface the platform on first use.

### `.mcp.json`

```json
{
  "mcpServers": {
    "qualys": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "pyqualys[mcp]==0.1.0", "pyqualys-mcp"],
      "env": {
        "QUALYS_API_URL": "${user_config.qualys_api_url}",
        "QUALYS_USERNAME": "${user_config.qualys_username}",
        "QUALYS_PASSWORD": "${user_config.qualys_password}"
      }
    }
  }
}
```

`${user_config.*}` substitution **is** permitted in MCP server configs — it is rejected only in
shell-form hook commands, monitor commands, and MCP `headersHelper`, where the value would reach a
shell. That is exactly why the guard hook in §6 reads its input from stdin and never interpolates a
credential.

Pinning `==0.1.0` means a library release cannot silently change plugin behaviour; we bump both
together.

**`uvx` is a hard dependency and we should say so.** The MCP Python SDK requires 3.10+, and the
user's system Python may well be 3.9 (it is on the machine this was developed on). `uvx --python
3.12` sidesteps that entirely by provisioning its own interpreter — but only if `uv` is installed.
The plugin README must state this, and the `scan` skill should fail with a clear message rather
than a stack trace when `uvx` is missing.

---

## 5. Skills — the actual value-add

The six MCP tools are primitives. The skills encode the workflow a Qualys operator actually runs,
so the model does not have to rediscover it each session.

### `/pyqualys:scan` — launch and follow a scan

Wraps `qualys_launch_vm_scan` → `qualys_list_vm_scans` (polling) → `qualys_fetch_vm_scan_results`.
The thing this skill exists to teach the model is that **Qualys scan launch is asynchronous**: it
returns a scan reference immediately, and results are not available until the scan finishes, which
can take hours. Without this, the model launches a scan, immediately tries to fetch, gets nothing,
and reports failure.

The skill should also encode:
- Poll with backoff, not in a tight loop — the platform answers rate limits with **HTTP 409**, not
  429, and PR #2 raises a typed `RateLimitError` carrying `X-RateLimit-ToWait-Sec`.
- `action=fetch` defaults to **CSV**, not XML. (This is the documented non-blocking finding from
  PR #2's review — worth fixing in the library, but the skill must not assume a dict either way.)
- Never poll more than once a minute for a long scan.

### `/pyqualys:triage` — turn detections into a ranked list

Wraps `qualys_list_host_detections`. Takes an optional host/IP/tag argument. Groups by QID, ranks by
severity and whether the detection is confirmed vs potential, and produces a short remediation
list. This is the "what should I fix first" question, and it is the single most common thing people
want from VMDR data.

Honest limitation to document in the skill: without the KnowledgeBase endpoint (explicitly out of
scope in PR #2) we have QIDs and severities but no CVE titles or patch guidance. The skill should
say so rather than inventing descriptions. If triage proves popular, KnowledgeBase becomes the
obvious next library addition.

### `/pyqualys:inventory` — asset inventory

Wraps `qualys_list_hosts` with the pagination generator. Answers "what do we have", filtered by
tag/IP range/OS.

---

## 6. Hooks — the destructive-action guard

`qualys_manage_vm_scan` accepts `cancel`, `pause`, `resume`, `delete`. `cancel` and `delete` are
destructive and irreversible against a live subscription. Proposal: a `PreToolUse` hook that
requires explicit confirmation for those two actions and lets `pause`/`resume` through.

The scoped-name detail matters and is easy to get wrong. A hook matching a plugin's **own** bundled
MCP server must use the fully scoped tool name, `mcp__plugin_<plugin-name>_<server-name>__<tool>`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "mcp__plugin_pyqualys_qualys__qualys_manage_vm_scan",
        "hooks": [
          { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/guard-destructive.sh" }
        ]
      }
    ]
  }
}
```

A matcher written against the bare `qualys` server key **never fires** — it would look correct in
review and silently protect nothing. The guard script reads the hook payload as JSON on stdin,
inspects `.tool_input.action`, and exits non-zero to block. It takes no credentials and
interpolates no user config, which keeps it clear of the shell-substitution restriction.

---

## 7. Distribution

`.claude-plugin/marketplace.json` at the repo root:

```json
{
  "name": "pyqualys",
  "owner": { "name": "Amit Ghadge", "email": "amitg.b14@gmail.com" },
  "plugins": [
    {
      "name": "pyqualys",
      "source": "./plugin",
      "description": "Launch and triage Qualys VM scans from Claude Code",
      "version": "0.1.0"
    }
  ]
}
```

Install path for users:

```
/plugin marketplace add Amitgb14/pyqualys
/plugin install pyqualys@pyqualys
```

Local development, no marketplace needed:

```
claude --plugin-dir ./plugin
/reload-plugins        # after each edit
claude plugin validate ./plugin
```

Submission to the public `claude-community` marketplace is a possible later step via the Console
form at platform.claude.com/plugins/submit. I would hold off until the plugin has been used against
a real subscription — see the open question in §9 about whether any of this has been validated
against live Qualys.

---

## 8. Phasing

| Phase | Scope | Exit criteria |
| :--- | :--- | :--- |
| **P0** | Merge PR #2, publish 0.1.0 to PyPI | `uvx --from pyqualys[mcp]==0.1.0 pyqualys-mcp` starts |
| **P1** | Manifest + `.mcp.json` + `userConfig`, no skills | `/plugin install`, then a raw tool call returns real data |
| **P2** | The three skills | Each runs end-to-end against a real subscription |
| **P3** | Destructive-action hook + `qualys-analyst` agent | Hook demonstrably blocks a `delete`; `claude plugin validate` clean |
| **P4** | Marketplace + README, tag `plugin-v0.1.0` | A second person installs from GitHub without help |

P1 is small — a manifest and a JSON file — and it is worth shipping on its own, because it
independently validates the credential path, which is the riskiest single piece.

---

## 9. Risks and open questions

1. **Has any of this touched a live Qualys subscription?** Everything in PR #2 was verified against
   mocks. The endpoint versions in particular (`api/3.0` for scan list, `api/5.0` for the host
   endpoints) were a contested call between two review rounds, resolved from vendor docs, never
   confirmed against a real platform. **A plugin makes those calls easier to run and therefore
   easier to get wrong at scale.** I would want one real end-to-end scan before P4.
2. **Rate limits are per-subscription, not per-user.** A model that polls too eagerly can exhaust
   the API concurrency limit for an entire security team. The `scan` skill's backoff guidance is
   load-bearing, not a nicety.
3. **Credential blast radius.** Qualys API accounts are often over-privileged. The plugin README
   should recommend a dedicated account with the narrowest role that permits scan launch and read.
4. **`uvx` dependency** — see §4. Needs a clear failure message.
5. **Should destructive tools ship at all?** An alternative is to drop `qualys_manage_vm_scan` from
   the plugin's exposed surface entirely and keep the plugin read-plus-launch. That is a smaller,
   safer v1. I lean toward shipping it *with* the hook, but it is a legitimate call to make the
   other way, and it is cheaper to decide now than to remove a tool later.

---

## 10. Recommendation

Ship P0 and P1 first and stop there for a beat. The credential flow through `userConfig` → keychain
→ MCP env is the part most likely to have a surprise in it, and it is testable in an afternoon once
0.1.0 is on PyPI. Skills are additive and can land incrementally afterwards.

The one thing I would not defer is the §6 hook. If `qualys_manage_vm_scan` is in the plugin at P1,
the guard should be in it too.
