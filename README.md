# pyqualys


pyqualys is simple, easy to use, Qualys public API based services.

Currently this project is in working progress, but there are few features are available(Check TODO).

Install
-----------
```
$ pip install pyqualys
```

Optional MCP server (needs Python 3.10+):
```
$ pip install 'pyqualys[mcp]'
```


Example
-----------
* Add Asset Group
```
# -*- coding: utf-8 -*-
import pyqualys

qualys = pyqualys.QualysAPI(username="admin",
                         password="admin",
                         host="https://abc123.com/")

service = qualys.service("vulnerability")
# Get response in json format, default is xml
service.FORMAT = "json"
asset = service.add_asset(title="myLinux", ips="10.10.10.1")
print("Response", asset)
```

* VM scan: launch -> poll -> fetch

A VM scan is asynchronous. `start_scan` returns a scan reference, you poll
`scan_status` with it until the state is `Finished`, then you fetch the
results. Qualys has no dedicated status endpoint - `scan_status` is a
filtered scan list.

```
# -*- coding: utf-8 -*-
import time
import pyqualys

qualys = pyqualys.QualysAPI(username="admin",
                            password="admin",
                            host="https://qualysapi.qualys.com/")
service = qualys.service("vulnerability")
service.FORMAT = "json"

# 1. Launch. Exactly one option profile, at least one target.
launched = service.scanner.start_scan(scan_title="pyqualys nightly",
                                      option_id=1234,
                                      ip="10.10.10.1")
items = launched["data"]["SIMPLE_RETURN"]["RESPONSE"]["ITEM_LIST"]["ITEM"]
scan_ref = [i["VALUE"] for i in items if i["KEY"] == "REFERENCE"][0]

# 2. Poll until it is done.
while True:
    status = service.scanner.scan_status(scan_ref)
    scan = status["data"]["SCAN_LIST_OUTPUT"]["RESPONSE"]["SCAN_LIST"]["SCAN"]
    state = scan["STATUS"]["STATE"]
    if state in ("Finished", "Canceled", "Error"):
        break
    time.sleep(60)

# 3. Fetch the results. output_format drives the return shape:
#    json/json_extended -> {"type": "json", ...}
#    csv/csv_extended   -> {"type": "csv", "data": <raw csv>}
#    omitted            -> the decoded XML dict
results = service.scanner.get_scan_report(scan_ref=scan_ref,
                                          output_format="json")
print(results["data"])
```

Manage a running scan with `manage_scan` - `action` and `scan_ref` are both
required:

```
service.scanner.manage_scan(action="cancel", scan_ref=scan_ref)
```

* Get hosts (Host List)

```
service = qualys.service("vulnerability")
service.FORMAT = "json"

# One page. No truncation_limit is injected, so Qualys applies its own
# default of 1000 records.
hosts = service.list_hosts(details="Basic", truncation_limit=100)

# Every page: iter_hosts follows the truncation WARNING/URL for you.
for page in service.iter_hosts(details="Basic", truncation_limit=100):
    response = page["data"]["HOST_LIST_OUTPUT"]["RESPONSE"]
    for host in response["HOST_LIST"]["HOST"]:
        print(host["ID"], host["IP"])

# max_pages is a runaway guard, 0 (the default) means unlimited.
first_two = list(service.iter_hosts(max_pages=2, truncation_limit=100))
```

* Get vulnerabilities (Host List Detection)

```
detections = service.list_host_detections(severities="4-5",
                                          truncation_limit=25)

# Two Qualys defaults worth knowing, neither of which pyqualys overrides:
#  * the response contains only New, Active and Re-Opened detections -
#    pass status="New,Active,Re-Opened,Fixed" to also see Fixed ones;
#  * information gathered QIDs are hidden unless you pass show_igs=1.
everything = service.list_host_detections(
    status="New,Active,Re-Opened,Fixed", show_igs=1)

for page in service.iter_host_detections(detection_updated_since="2026-01-01"):
    ...
```


API versions
-----------

Qualys versions each endpoint - and sometimes each *action* of an endpoint -
independently, so the prefix is now declared per endpoint instead of as one
global `api/2.0/` string. The versions below follow the "API Version / EOS /
EOL" tables in the Qualys VM/PA API user guide:

| Endpoint | URI | Version | Why |
| --- | --- | --- | --- |
| VM scan list | `fo/scan/` `action=list` | `api/3.0/` | V3.0 Active; V2.0 EOS Dec 2025, EOL Dec 2026 |
| VM scan launch / fetch / manage | `fo/scan/` | `api/2.0/` | only version Qualys documents |
| Host List | `fo/asset/host/` | `api/5.0/` | V5.0 Active; V2.0-V4.0 EOS Dec 2025 |
| Host List Detection | `fo/asset/host/vm/detection/` | `api/5.0/` | V5.0 Active; V2.0-V4.0 EOS Dec 2025 |
| Asset groups | `fo/asset/group/` | `api/2.0/` | unchanged |
| Reports | `fo/report/` | `api/2.0/` | unchanged, out of scope |
| Users / asset IPs | `msp/*.php` | legacy V1, no prefix | unchanged |

The versions live on the URLs holder as `scan_api_version`,
`scan_list_api_version`, `host_api_version` and friends. `api=` is only the
fallback for an endpoint that declares none; `pin_api_version=True` forces
every endpoint onto it:

```
from pyqualys.services.vulnerability import VulnerabilityService

service = VulnerabilityService(qualys.session, api="api/2.0/",
                               pin_api_version=True)
```


Breaking changes in 0.1.0
-----------

1. **TLS verification is now on by default.** `APISession.verify_ssl`
   flipped from `False` to `True`; every request this library made used to
   skip certificate verification. Opt out for private cloud or self-signed
   platforms with `pyqualys.QualysAPI(..., verify_ssl=False)`.
2. **Each endpoint now carries its own API version prefix** instead of one
   global `api/2.0/` string, and `api=` is only the fallback for an
   endpoint that declares no version of its own. The one existing URI that
   moved is the VM scan list: `scan_list()` and `scan_status()` now POST to
   `api/3.0/fo/scan/`, because `api/2.0/fo/scan/?action=list` reached EOS
   in December 2025 and reaches EOL in December 2026. Scan launch, fetch
   and the manage actions stay on `api/2.0/fo/scan/` - that is the only
   version Qualys documents for them. See the API versions table above.
   Pass `pin_api_version=True` to force every endpoint back onto `api=`,
   exactly as in 0.0.1.
3. **New exceptions** in `pyqualys.errors`: `QualysError` (base),
   `ParameterError` (also a `ValueError`), `QualysAPIError` (carries
   `status_code`) and `RateLimitError` (carries `retry_after` read from the
   `X-RateLimit-ToWait-Sec` header; Qualys signals limits with HTTP 409,
   not 429). `QualysAPI(...)` raises `ParameterError` on a missing
   username, password or host instead of logging and returning a
   half-constructed object, and `QualysAPI.service()` raises on an unknown
   service name instead of returning `None`.
4. **`start_scan()` validates** the combinations the Qualys API itself
   rejects (missing or duplicated `option_id`/`option_title`, no target,
   `asset_groups` together with `asset_group_ids`, `tag_*` parameters with
   `target_from=assets`, `iscanner_name` together with `iscanner_id`).
   Unknown parameters are still passed through untouched.
5. **`manage_scan()` raises** `ParameterError` when `action` or `scan_ref`
   is missing; it used to POST an empty body. An unrecognised action only
   logs a warning and is still sent.
6. **`session.get/put/delete` send parameters in the query string**
   (`params=`) instead of the request body. Filters that Qualys silently
   ignored are now honoured, so responses may legitimately change.
7. **`decode_xml()` never raises `ParseError`.** Non-XML bodies (CSV, JSON,
   an HTML error page, an empty 401) return the documented
   `{"type": "xml", "data": <raw body>}` fallback.
8. **`get_scan_report()` is output-format aware** - see the example above.
   Previously anything other than XML crashed.
9. `update_asset(ids=...)` no longer raises `UnboundLocalError`.

Not changed on purpose: `asset_ips.py` still targets the legacy V1
`msp/asset_ip.php` endpoints and `Reports` stays on `api/2.0/fo/report/`.


MCP server
-----------

`pyqualys` ships an optional [Model Context
Protocol](https://modelcontextprotocol.io) stdio server so an MCP client
can drive Qualys VM scans and read host detections.

**Requires Python 3.10 or newer** - the `mcp` SDK does. The library itself
still runs on 3.9; only this extra does not.

```
$ pip install 'pyqualys[mcp]'
$ pyqualys-mcp                 # or: python -m pyqualys.mcp
```

Or without installing anything:

```
$ uvx --python 3.12 --from 'pyqualys[mcp]' pyqualys-mcp
```

Configuration is environment-only; credentials are never tool arguments.

| Variable | Required | Default |
| --- | --- | --- |
| `QUALYS_USERNAME` | yes | - |
| `QUALYS_PASSWORD` | yes | - |
| `QUALYS_API_URL` | yes | - |
| `QUALYS_VERIFY_SSL` | no | `true` |
| `QUALYS_TIMEOUT` | no | `300` |
| `QUALYS_CONCURRENCY` | no | `2` |
| `QUALYS_MCP_LOG_LEVEL` | no | `INFO` |

`QUALYS_CONCURRENCY` matches the concurrency Qualys provisions for most
subscriptions (2). The server serialises calls with a semaphore rather than
retrying, because exceeding the limit returns HTTP 409.

Tools:

| Tool | What it does |
| --- | --- |
| `qualys_launch_vm_scan` | Launch a VM scan, returns a `scan_ref` |
| `qualys_list_vm_scans` | List scans, or poll one by `scan_ref` |
| `qualys_fetch_vm_scan_results` | Download a finished scan's results |
| `qualys_manage_vm_scan` | Cancel, pause, resume or delete a scan |
| `qualys_list_hosts` | Host List - "what assets do I have" |
| `qualys_list_host_detections` | Host List Detection - "my vulnerabilities" |

The repository ships a project-scoped `.mcp.json`. It holds no secrets - it
refers to shell variables by name:

```
{
  "mcpServers": {
    "qualys": {
      "command": "uvx",
      "args": ["--python", "3.12", "--from", "pyqualys[mcp]", "pyqualys-mcp"],
      "env": {
        "QUALYS_USERNAME": "${QUALYS_USERNAME}",
        "QUALYS_PASSWORD": "${QUALYS_PASSWORD}",
        "QUALYS_API_URL": "${QUALYS_API_URL:-https://qualysapi.qualys.com/}"
      }
    }
  }
}
```

Claude Code expands `${VAR}` and `${VAR:-default}` in `command`, `args` and
`env`. **Claude Desktop does not** - Desktop users must put literal values
in their own config file, outside version control.


Tests
-----------

The suite is offline: no network, no credentials.

```
$ python -m unittest discover -s pyqualys/tests -t . -p 'test_*.py' -v
```

The historical live tests are skipped unless `QUALYS_LIVE_TESTS` is set,
and the MCP tests are skipped on Python 3.9 or when `mcp` is not installed.

### Contract tests

`pyqualys/tests/contract_tests/` is a separate category. The rest of the
suite parses fixtures this project wrote, which proves the parsers are
self-consistent; the contract tests parse response bodies and HTTP headers
transcribed from the *Qualys API (VM and PA) User Guide* v10.39.1
(10 July 2026), each annotated with the page it came from. When one of
those disagrees with the code, the code is what is wrong.

They cover the three things that cannot be checked by reading our own
code: that every request goes to the URI and API version the guide
documents for that operation, that the vendor's own sample bodies parse
correctly including their CDATA indentation and pagination cursors, and
that both kinds of HTTP 409 are handled - the rate-limit block that
carries `X-RateLimit-ToWait-Sec` and the concurrency block that does not.

This is a substitute for live validation, not a replacement. Nothing in
this project has been run against a real Qualys subscription, so
authentication, real rate-limit behaviour under load and pagination at
volume remain unverified.
