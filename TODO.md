### Asset

- [x] Add asset
- [x] Update asset
- [x] Delete asset
- [x] List of assets (now accepts truncation_limit / id_min / id_max)
- [x] Search asset
- [x] Add asset IP

### Scanner
/api/3.0/fo/scan/ for action=list, /api/2.0/fo/scan/ for launch, fetch
and the manage actions (the only version Qualys documents for those).

- [x] List of Scan
- [x] Start Scan (validates option profile / target combinations)
- [x] Manage Scan (cancel, pause, resume, delete)
- [x] Scan Report (XML, CSV and JSON output formats)
- [x] Scan Status (poll by scan_ref)

### Hosts
/api/5.0/fo/asset/host/ and /api/5.0/fo/asset/host/vm/detection/
(V5.0 is the only Active version; V2.0-V4.0 are EOS since Dec 2025)

- [x] Host List
- [x] Host List Detection
- [x] Host List pagination (iter_hosts / iter_host_detections follow the
      truncation WARNING/URL)

### MCP Server
`pip install 'pyqualys[mcp]'`, Python 3.10+

- [x] qualys_launch_vm_scan
- [x] qualys_list_vm_scans
- [x] qualys_fetch_vm_scan_results
- [x] qualys_manage_vm_scan
- [x] qualys_list_hosts
- [x] qualys_list_host_detections

### Reports
/api/2.0/fo/report/

- [ ] List Reports
- [ ] Download Reports
- [ ] Launch Report

### Not planned this round

Scope rule: add only a very small set of the most in-demand services.
Fewer, correct, well-tested services beats breadth. The following are
deliberately out of scope:

- [ ] KnowledgeBase - /api/4.0/fo/knowledge_base/vuln/. Useful for
      enriching detection QIDs, but a whole new endpoint family with
      payloads large enough to need local caching.
- [ ] Scheduled scans - /api/2.0/fo/scan/scheduled/ (list, create, update,
      delete), plus compliance, SCAP and cloud perimeter scans.
- [ ] Scanner Appliances - /api/2.0/fo/appliance/.
- [ ] Reports endpoint modernisation. `/api/2.0/fo/report/` already works;
      touching it risks regressions on report_type / output_format.
- [ ] IP List migration - /api/2.0/fo/asset/ip/. `asset_ips.py` still
      points at the legacy V1 `msp/asset_ip.php` and
      `msp/asset_ip_list.php` endpoints, and its URI construction
      deliberately omits the api version prefix. Migrating would break
      add_asset_ips / update_asset_ips / get_asset_ips.
- [ ] Session-cookie auth - /api/2.0/fo/session/. HTTP Basic is fully
      supported and sessions introduce a lockout hazard if logout is ever
      missed.
- [ ] WAS / CSAM / Global AssetView gateway APIs (JWT bearer auth,
      incompatible with this library's basic-auth session).
- [ ] Automatic retry/backoff on HTTP 409. `RateLimitError` carries
      `retry_after`; the caller decides. The MCP server serialises calls
      with a semaphore instead.
