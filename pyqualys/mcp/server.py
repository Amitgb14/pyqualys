# -*- coding: utf-8 -*-
"""
Model Context Protocol server exposing the most in demand Qualys VM
operations: launch, poll and fetch a VM scan, manage a running scan,
list host assets and list host detections.

Run it with::

    QUALYS_USERNAME=... QUALYS_PASSWORD=... QUALYS_API_URL=... \\
        python -m pyqualys.mcp

Credentials come from the environment only, never from tool arguments.

This is the one module of the project that requires Python 3.10 at
runtime, because the `mcp` SDK does. It is still written with
``typing.Optional`` rather than PEP 604 unions so that it byte-compiles
under 3.9 - `pip` compiles every shipped module at install time.
"""
import os
import sys
import logging
import functools
from dataclasses import dataclass
from contextlib import asynccontextmanager
from urllib.parse import urlparse, parse_qsl
from typing import Any, AsyncIterator, Dict, List, Literal, Optional

if sys.version_info < (3, 10):                          # pragma: no cover
    sys.stderr.write(
        "pyqualys-mcp requires Python 3.10 or newer (the mcp SDK does).\n"
        "Try: uvx --python 3.12 --from 'pyqualys[mcp]' pyqualys-mcp\n")
    raise SystemExit(1)

# stdout is the JSON-RPC wire, so every log record must go to stderr.
# pyqualys/__init__.py also calls basicConfig, and basicConfig is a no-op
# once the root logger owns a handler, so ours has to win the race.
logging.basicConfig(
    stream=sys.stderr,
    level=os.environ.get("QUALYS_MCP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

import anyio                                            # noqa: E402
from anyio import to_thread                             # noqa: E402
from pydantic import BaseModel, Field                   # noqa: E402
from mcp.server.fastmcp import Context, FastMCP         # noqa: E402
from mcp.server.fastmcp.exceptions import ToolError     # noqa: E402
from mcp.types import ToolAnnotations                   # noqa: E402

import pyqualys                                         # noqa: E402
from pyqualys.errors import (                           # noqa: E402
    ParameterError, QualysAPIError, RateLimitError)

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://qualysapi.qualys.com/"
TRUE_VALUES = ("1", "true", "yes", "on")


@dataclass
class QualysConfig:
    """Everything the server needs, all of it from the environment."""

    username: str
    password: str
    api_url: str
    verify_ssl: bool = True
    timeout: int = 300
    concurrency: int = 2


@dataclass
class QualysCtx:
    """Lifespan context handed to every tool."""

    service: Any
    gate: Any
    timeout: int


def _require_env(name):
    # type: (str) -> str
    value = os.environ.get(name)
    if not value or not value.strip():
        raise ValueError(
            "{0} is not set. Export it before starting the "
            "server.".format(name))
    value = value.strip()
    if "${" in value:
        raise ValueError(
            "{0} still contains an unexpanded ${{...}} placeholder. The "
            "shell variable it refers to is unset.".format(name))
    return value


def _env_int(name, default):
    # type: (str, int) -> int
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        return int(raw.strip())
    except ValueError:
        raise ValueError("{0} must be an integer.".format(name))


def _load_config():
    # type: () -> QualysConfig
    """
    Build the configuration from the environment.

    :raises ValueError: when a required variable is missing or still
            holds an unexpanded ``${VAR}`` placeholder.
    """
    username = _require_env("QUALYS_USERNAME")
    password = _require_env("QUALYS_PASSWORD")
    api_url = _require_env("QUALYS_API_URL")
    verify_raw = os.environ.get("QUALYS_VERIFY_SSL")
    verify_ssl = True
    if verify_raw is not None and verify_raw.strip():
        verify_ssl = verify_raw.strip().lower() in TRUE_VALUES
    return QualysConfig(
        username=username,
        password=password,
        api_url=api_url.rstrip("/") + "/",
        verify_ssl=verify_ssl,
        timeout=_env_int("QUALYS_TIMEOUT", 300),
        concurrency=_env_int("QUALYS_CONCURRENCY", 2))


@asynccontextmanager
async def lifespan(server):
    # type: (FastMCP) -> AsyncIterator[QualysCtx]
    config = _load_config()
    api = pyqualys.QualysAPI(username=config.username,
                             password=config.password,
                             host=config.api_url,
                             verify_ssl=config.verify_ssl,
                             timeout=config.timeout)
    service = api.service("vulnerability")
    service.FORMAT = "json"
    logger.info("pyqualys MCP server ready (concurrency=%s)",
                config.concurrency)
    yield QualysCtx(service=service,
                    gate=anyio.Semaphore(config.concurrency),
                    timeout=config.timeout)


mcp = FastMCP("pyqualys", lifespan=lifespan)


def _ctx(ctx):
    # type: (Context) -> QualysCtx
    return ctx.request_context.lifespan_context


async def _run(ctx, fn, **kwargs):
    # type: (Context, Any, Any) -> Any
    """
    Run a blocking pyqualys call off the event loop.

    FastMCP calls synchronous tool functions directly on the event loop,
    so every tool here is ``async def`` and every blocking call is
    offloaded through this helper, serialised by the concurrency gate.
    """
    qualys = _ctx(ctx)
    call = functools.partial(fn, **kwargs)
    try:
        async with qualys.gate:
            # fail_after cannot interrupt a blocking requests call - the
            # cancel scope only fires once the worker thread returns. The
            # real ceiling is APISession's own timeout, set to the same
            # value; this is the belt to that braces.
            with anyio.fail_after(qualys.timeout):
                return await to_thread.run_sync(call)
    except TimeoutError:
        raise ToolError(
            "Qualys did not answer within {0}s.".format(qualys.timeout))
    except ParameterError as e:
        raise ToolError("Invalid parameters: {0}".format(e))
    except RateLimitError as e:
        if e.retry_after is None:
            raise ToolError("Qualys rate/concurrency limit reached, "
                            "retry shortly.")
        raise ToolError(
            "Qualys rate/concurrency limit reached, retry in "
            "{0}s.".format(e.retry_after))
    except QualysAPIError as e:
        raise ToolError("Qualys returned HTTP {0}.".format(e.status_code))
    except ToolError:
        raise
    except Exception as e:
        # Anything else (requests ConnectionError, SSLError, ...) must
        # not reach the client verbatim: those messages carry the full
        # platform URL. Log the detail to stderr instead.
        logger.exception("Qualys call failed")
        raise ToolError(
            "Could not reach the Qualys platform ({0}).".format(
                type(e).__name__))


def _clean(kwargs):
    # type: (Dict[str, Any]) -> Dict[str, Any]
    """Drop the parameters the caller left unset."""
    return dict((k, v) for k, v in kwargs.items() if v is not None)


def _payload(response):
    # type: (Any) -> Any
    """Unwrap the {'type': ..., 'data': ...} envelope decode_xml uses."""
    if isinstance(response, dict) and "data" in response and \
            "type" in response:
        return response["data"]
    return response


def _dig(obj, *keys):
    # type: (Any, str) -> Any
    """Walk nested dicts, returning None as soon as a key is absent."""
    for key in keys:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(key)
    return obj


def _as_list(node):
    # type: (Any) -> List[Any]
    """etree_to_dict collapses a single child to a dict; re-expand it."""
    if node is None:
        return []
    if isinstance(node, list):
        return node
    return [node]


def _text(node):
    # type: (Any) -> Optional[str]
    if node is None:
        return None
    if isinstance(node, dict):
        node = node.get("#text")
        if node is None:
            return None
    return str(node)


def _error_text(payload):
    # type: (Any) -> Optional[str]
    """Return the Qualys SIMPLE_RETURN error text, when there is one."""
    response = _dig(payload, "SIMPLE_RETURN", "RESPONSE")
    if not isinstance(response, dict):
        return None
    code = _text(response.get("CODE"))
    if code is None:
        return None
    return "Qualys error {0}: {1}".format(code, _text(response.get("TEXT")))


class ScanSummary(BaseModel):
    scan_ref: Optional[str] = Field(None, description="Scan reference.")
    title: Optional[str] = None
    state: Optional[str] = Field(None, description="Running, Finished, ...")
    launch_datetime: Optional[str] = None
    target: Optional[str] = None
    processed: Optional[str] = None


class ScanList(BaseModel):
    total: int = Field(..., description="Scans Qualys returned.")
    returned: int = Field(..., description="Scans in this response.")
    scans: List[ScanSummary] = []
    note: Optional[str] = None


class LaunchResult(BaseModel):
    scan_ref: Optional[str] = Field(None, description="Poll this ref.")
    message: Optional[str] = None
    note: str = Field(
        "The scan runs asynchronously. Poll qualys_list_vm_scans with "
        "this scan_ref until state is Finished, then call "
        "qualys_fetch_vm_scan_results.")


class ScanResults(BaseModel):
    scan_ref: str
    returned: int = Field(..., description="Rows in this response.")
    total: int = Field(..., description="Rows Qualys returned.")
    truncated: bool = False
    rows: List[Dict[str, Any]] = []
    note: Optional[str] = None


class ManageResult(BaseModel):
    scan_ref: str
    action: str
    message: Optional[str] = None


class HostSummary(BaseModel):
    id: Optional[str] = None
    ip: Optional[str] = None
    tracking_method: Optional[str] = None
    dns: Optional[str] = None
    netbios: Optional[str] = None
    os: Optional[str] = None
    last_vuln_scan_datetime: Optional[str] = None


class HostList(BaseModel):
    returned: int
    hosts: List[HostSummary] = []
    truncated: bool = Field(
        False, description="More records exist on the Qualys side.")
    next_id_min: Optional[str] = Field(
        None, description="Pass as id_min to fetch the next page.")


class DetectionSummary(BaseModel):
    host_id: Optional[str] = None
    ip: Optional[str] = None
    dns: Optional[str] = None
    qid: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    status: Optional[str] = None
    last_found_datetime: Optional[str] = None


class DetectionList(BaseModel):
    returned: int
    detections: List[DetectionSummary] = []
    truncated: bool = False
    next_id_min: Optional[str] = None
    note: str = Field(
        "Qualys returns only New, Active and Re-Opened detections "
        "unless status='New,Active,Re-Opened,Fixed' is passed, and "
        "hides information gathered QIDs unless show_igs=1.")


@mcp.tool(
    name="qualys_launch_vm_scan",
    annotations=ToolAnnotations(title="Launch Qualys VM scan",
                                readOnlyHint=False,
                                destructiveHint=False,
                                idempotentHint=False,
                                openWorldHint=True))
async def qualys_launch_vm_scan(
    ctx: Context,
    scan_title: str,
    option_id: Optional[int] = None,
    option_title: Optional[str] = None,
    ip: Optional[str] = None,
    asset_group_ids: Optional[str] = None,
    asset_groups: Optional[str] = None,
    fqdn: Optional[str] = None,
    iscanner_name: Optional[str] = None,
    priority: Optional[int] = None,
) -> LaunchResult:
    """Launch a Qualys VM scan.

    ASYNCHRONOUS: returns a scan_ref immediately and does NOT wait for
    the scan to finish. Poll qualys_list_vm_scans with that scan_ref to
    check the state, then call qualys_fetch_vm_scan_results once it is
    Finished.

    Supply exactly one option profile (option_id OR option_title) and at
    least one target (ip, asset_group_ids, asset_groups or fqdn);
    asset_groups and asset_group_ids cannot be combined. This starts
    real scanning traffic against real hosts.

    :param scan_title: name for the scan.
    :param option_id: option profile id.
    :param option_title: option profile title.
    :param ip: comma separated IPs or ranges.
    :param asset_group_ids: comma separated asset group ids.
    :param asset_groups: comma separated asset group titles.
    :param fqdn: comma separated FQDN targets.
    :param iscanner_name: scanner appliance name.
    :param priority: 0 to 9, 0 means no priority.
    """
    service = _ctx(ctx).service
    params = _clean({
        "scan_title": scan_title,
        "option_id": option_id,
        "option_title": option_title,
        "ip": ip,
        "asset_group_ids": asset_group_ids,
        "asset_groups": asset_groups,
        "fqdn": fqdn,
        "iscanner_name": iscanner_name,
        "priority": priority,
    })
    response = await _run(ctx, service.scanner.start_scan, **params)
    payload = _payload(response)
    error = _error_text(payload)
    if error:
        raise ToolError(error)

    scan_ref = None
    items = _dig(payload, "SIMPLE_RETURN", "RESPONSE", "ITEM_LIST", "ITEM")
    for item in _as_list(items):
        if _text(_dig(item, "KEY")) == "REFERENCE":
            scan_ref = _text(_dig(item, "VALUE"))
    message = _text(_dig(payload, "SIMPLE_RETURN", "RESPONSE", "TEXT"))
    return LaunchResult(scan_ref=scan_ref, message=message)


@mcp.tool(
    name="qualys_list_vm_scans",
    annotations=ToolAnnotations(title="List Qualys VM scans",
                                readOnlyHint=True,
                                openWorldHint=True))
async def qualys_list_vm_scans(
    ctx: Context,
    scan_ref: Optional[str] = None,
    state: Optional[str] = None,
    launched_after_datetime: Optional[str] = None,
    processed: Optional[int] = None,
    limit: int = 50,
) -> ScanList:
    """List Qualys VM scans and their state.

    Pass scan_ref to poll ONE scan's status - Qualys has no separate
    status endpoint, this is how you check whether a scan is done.
    States are Running, Paused, Canceled, Finished, Error, Queued and
    Loading.

    IMPORTANT: with no launched_after_datetime filter Qualys returns
    only scans from the past 30 days.

    :param scan_ref: scan reference, e.g. scan/1234567890.12345.
    :param state: filter by state.
    :param launched_after_datetime: YYYY-MM-DD[THH:MM:SSZ].
    :param processed: 1 for processed scans, 0 for unprocessed.
    :param limit: client side cap on the rows returned.
    """
    service = _ctx(ctx).service
    params = _clean({
        "scan_ref": scan_ref,
        "state": state,
        "launched_after_datetime": launched_after_datetime,
        "processed": processed,
    })
    response = await _run(ctx, service.scanner.scan_list, **params)
    payload = _payload(response)
    error = _error_text(payload)
    if error:
        raise ToolError(error)

    scans = _as_list(_dig(payload, "SCAN_LIST_OUTPUT", "RESPONSE",
                          "SCAN_LIST", "SCAN"))
    rows = []
    for scan in scans[:max(limit, 0)]:
        rows.append(ScanSummary(
            scan_ref=_text(_dig(scan, "REF")),
            title=_text(_dig(scan, "TITLE")),
            state=_text(_dig(scan, "STATUS", "STATE")),
            launch_datetime=_text(_dig(scan, "LAUNCH_DATETIME")),
            target=_text(_dig(scan, "TARGET")),
            processed=_text(_dig(scan, "PROCESSED"))))
    note = None
    if not launched_after_datetime:
        note = ("No launched_after_datetime filter: Qualys returned only "
                "the last 30 days of scans.")
    return ScanList(total=len(scans), returned=len(rows), scans=rows,
                    note=note)


@mcp.tool(
    name="qualys_fetch_vm_scan_results",
    annotations=ToolAnnotations(title="Fetch Qualys VM scan results",
                                readOnlyHint=True,
                                openWorldHint=True))
async def qualys_fetch_vm_scan_results(
    ctx: Context,
    scan_ref: str,
    mode: Literal["brief", "extended"] = "brief",
    ips: Optional[str] = None,
    max_rows: int = 200,
) -> ScanResults:
    """Download the results of a finished Qualys VM scan.

    Only valid for scans in state Finished, Canceled, Paused or Error -
    check with qualys_list_vm_scans first.

    mode=brief returns ip, dns, netbios, qid and result; mode=extended
    adds protocol, port, ssl and fqdn. Output is truncated to max_rows to
    protect context; raise max_rows only when the user asks for more.

    :param scan_ref: scan reference to fetch.
    :param mode: brief or extended output.
    :param ips: restrict the results to these IPs.
    :param max_rows: client side cap on the rows returned.
    """
    service = _ctx(ctx).service
    output_format = "json" if mode == "brief" else "json_extended"
    params = _clean({
        "scan_ref": scan_ref,
        "output_format": output_format,
        "ips": ips,
    })
    response = await _run(ctx, service.scanner.get_scan_report, **params)
    payload = _payload(response)
    if isinstance(payload, str):
        raise ToolError(
            "Qualys did not return JSON results for {0}; the scan is "
            "probably not Finished yet.".format(scan_ref))
    error = _error_text(payload)
    if error:
        raise ToolError(error)

    rows = payload if isinstance(payload, list) else [payload]
    rows = [row for row in rows if isinstance(row, dict)]
    capped = rows[:max(max_rows, 0)]
    note = None
    if len(capped) < len(rows):
        note = ("Truncated to max_rows; raise max_rows to see the "
                "remaining rows.")
    return ScanResults(scan_ref=scan_ref, returned=len(capped),
                       total=len(rows), truncated=len(capped) < len(rows),
                       rows=capped, note=note)


@mcp.tool(
    name="qualys_manage_vm_scan",
    annotations=ToolAnnotations(title="Manage a Qualys VM scan",
                                readOnlyHint=False,
                                destructiveHint=True,
                                idempotentHint=False,
                                openWorldHint=True))
async def qualys_manage_vm_scan(
    ctx: Context,
    scan_ref: str,
    action: Literal["cancel", "pause", "resume", "delete"],
) -> ManageResult:
    """Cancel, pause, resume or delete a Qualys VM scan.

    DESTRUCTIVE: delete permanently removes the scan and its results,
    and cancel cannot be undone. Confirm with the user before calling
    with action=delete or action=cancel.

    :param scan_ref: scan reference to act on.
    :param action: cancel, pause, resume or delete.
    """
    service = _ctx(ctx).service
    response = await _run(ctx, service.scanner.manage_scan,
                          scan_ref=scan_ref, action=action)
    payload = _payload(response)
    error = _error_text(payload)
    if error:
        raise ToolError(error)
    message = _text(_dig(payload, "SIMPLE_RETURN", "RESPONSE", "TEXT"))
    return ManageResult(scan_ref=scan_ref, action=action, message=message)


@mcp.tool(
    name="qualys_list_hosts",
    annotations=ToolAnnotations(title="List Qualys host assets",
                                readOnlyHint=True,
                                openWorldHint=True))
async def qualys_list_hosts(
    ctx: Context,
    ids: Optional[str] = None,
    ips: Optional[str] = None,
    ag_ids: Optional[str] = None,
    details: Literal["None", "Basic", "Basic/AGs", "All",
                     "All/AGs"] = "Basic",
    id_min: Optional[int] = None,
    truncation_limit: int = 100,
) -> HostList:
    """List the scanned host assets in the Qualys subscription.

    This is the "what assets do I have" call and the way to get host IDs
    for qualys_list_host_detections. details="None" returns IDs only and
    is the cheapest option; details="All" is large.

    Results are paginated by Qualys - when more records exist,
    next_id_min is returned; call again with id_min set to continue.

    :param ids: host ids or ranges, e.g. "1-100,205".
    :param ips: IPs or ranges.
    :param ag_ids: asset group ids.
    :param details: level of detail per host.
    :param id_min: continue from a previous page.
    :param truncation_limit: records per page.
    """
    service = _ctx(ctx).service
    params = _clean({
        "ids": ids,
        "ips": ips,
        "ag_ids": ag_ids,
        "details": details,
        "id_min": id_min,
        "truncation_limit": truncation_limit,
    })
    response = await _run(ctx, service.list_hosts, **params)
    payload = _payload(response)
    error = _error_text(payload)
    if error:
        raise ToolError(error)

    root = _dig(payload, "HOST_LIST_OUTPUT", "RESPONSE")
    hosts = _as_list(_dig(root, "HOST_LIST", "HOST"))
    rows = []
    for host in hosts:
        rows.append(HostSummary(
            id=_text(_dig(host, "ID")),
            ip=_text(_dig(host, "IP")),
            tracking_method=_text(_dig(host, "TRACKING_METHOD")),
            dns=_text(_dig(host, "DNS")),
            netbios=_text(_dig(host, "NETBIOS")),
            os=_text(_dig(host, "OS")),
            last_vuln_scan_datetime=_text(
                _dig(host, "LAST_VULN_SCAN_DATETIME"))))
    next_id_min = _next_id_min(root)
    return HostList(returned=len(rows), hosts=rows,
                    truncated=next_id_min is not None,
                    next_id_min=next_id_min)


@mcp.tool(
    name="qualys_list_host_detections",
    annotations=ToolAnnotations(title="List Qualys host detections",
                                readOnlyHint=True,
                                openWorldHint=True))
async def qualys_list_host_detections(
    ctx: Context,
    ids: Optional[str] = None,
    ips: Optional[str] = None,
    qids: Optional[str] = None,
    severities: Optional[str] = None,
    status: Optional[str] = None,
    detection_updated_since: Optional[str] = None,
    show_igs: int = 0,
    truncation_limit: int = 25,
) -> DetectionList:
    """List Qualys hosts joined with their vulnerability detections.

    This is what "show me my vulnerabilities" means. Returns host, QID,
    severity, detection status and last found dates.

    IMPORTANT DEFAULTS: Qualys returns only New, Active and Re-Opened
    detections unless you explicitly pass
    status="New,Active,Re-Opened,Fixed"; information gathered QIDs are
    hidden unless show_igs=1. Use detection_updated_since for
    incremental syncs. Responses are very large, so truncation_limit is
    deliberately small - raise it only when asked.

    :param ids: host ids or ranges.
    :param ips: IPs or ranges.
    :param qids: QIDs or ranges.
    :param severities: severity filter, e.g. "4-5".
    :param status: e.g. "New,Active,Re-Opened,Fixed".
    :param detection_updated_since: YYYY-MM-DD[THH:MM:SSZ].
    :param show_igs: 1 to include information gathered QIDs.
    :param truncation_limit: records per page.
    """
    service = _ctx(ctx).service
    params = _clean({
        "ids": ids,
        "ips": ips,
        "qids": qids,
        "severities": severities,
        "status": status,
        "detection_updated_since": detection_updated_since,
        "show_igs": show_igs,
        "truncation_limit": truncation_limit,
    })
    response = await _run(ctx, service.list_host_detections, **params)
    payload = _payload(response)
    error = _error_text(payload)
    if error:
        raise ToolError(error)

    root = _dig(payload, "HOST_LIST_VM_DETECTION_OUTPUT", "RESPONSE")
    rows = []
    for host in _as_list(_dig(root, "HOST_LIST", "HOST")):
        detections = _as_list(_dig(host, "DETECTION_LIST", "DETECTION"))
        for detection in detections:
            rows.append(DetectionSummary(
                host_id=_text(_dig(host, "ID")),
                ip=_text(_dig(host, "IP")),
                dns=_text(_dig(host, "DNS")),
                qid=_text(_dig(detection, "QID")),
                severity=_text(_dig(detection, "SEVERITY")),
                type=_text(_dig(detection, "TYPE")),
                status=_text(_dig(detection, "STATUS")),
                last_found_datetime=_text(
                    _dig(detection, "LAST_FOUND_DATETIME"))))
    next_id_min = _next_id_min(root)
    return DetectionList(returned=len(rows), detections=rows,
                         truncated=next_id_min is not None,
                         next_id_min=next_id_min)


def _next_id_min(root):
    # type: (Any) -> Optional[str]
    """Read id_min out of the truncation WARNING Qualys embeds."""
    url = _text(_dig(root, "WARNING", "URL"))
    if not url:
        return None
    params = dict(parse_qsl(urlparse(url.strip()).query))
    return params.get("id_min")


def main():
    # type: () -> None
    """Console script entry point."""
    try:
        # Fail fast and legibly rather than deep inside the lifespan.
        _load_config()
    except ValueError as e:
        sys.stderr.write("pyqualys-mcp: {0}\n".format(e))
        raise SystemExit(2)
    mcp.run(transport="stdio")
