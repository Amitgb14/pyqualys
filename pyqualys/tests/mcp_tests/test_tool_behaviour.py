# -*- coding: utf-8 -*-
"""
Offline behaviour tests for the six MCP tool bodies.

``test_tools.py`` only proves the registry is right; this module actually
awaits every tool coroutine against a mocked ``APISession.post`` and
checks the summary model it builds, plus the error translation paths.

Skipped on Python < 3.10 or when the optional ``mcp`` extra is absent.
"""
import sys
import unittest

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

server = None
anyio = None
ToolError = None
SKIP_REASON = None

if sys.version_info < (3, 10):
    SKIP_REASON = "pyqualys.mcp requires Python 3.10 or newer"
else:
    try:
        import anyio
        from mcp.server.fastmcp.exceptions import ToolError
        from pyqualys.mcp import server
    except ImportError as e:                            # pragma: no cover
        SKIP_REASON = "mcp package is not installed ({0})".format(e)

if SKIP_REASON is None:
    import pyqualys
    from pyqualys.utils.session import APISession
    from pyqualys.tests import fixtures
    from pyqualys.tests.fixtures import FakeResponse, Recorder

HOST = "https://qualysapi.qualys.com/"
SCAN_REF = "scan/1234567890.12345"


class FakeRequestContext(object):

    def __init__(self, lifespan_context):
        self.lifespan_context = lifespan_context


class FakeContext(object):
    """Stand-in for ``mcp.server.fastmcp.Context``."""

    def __init__(self, lifespan_context):
        self.request_context = FakeRequestContext(lifespan_context)


@unittest.skipUnless(SKIP_REASON is None, SKIP_REASON or "")
class ToolTestCase(unittest.IsolatedAsyncioTestCase):

    def build_service(self):
        api = pyqualys.QualysAPI(username="admin", password="secret",
                                 host=HOST)
        service = api.service("vulnerability")
        service.FORMAT = "json"
        return service

    async def invoke(self, tool, responses, **kwargs):
        """Await ``tool`` with ``responses`` replayed by the recorder."""
        ctx = FakeContext(server.QualysCtx(service=self.build_service(),
                                           gate=anyio.Semaphore(2),
                                           timeout=30))
        recorder = Recorder(responses)
        with mock.patch.object(APISession, "post", recorder):
            result = await tool(ctx, **kwargs)
        return recorder, result


class TestLaunchTool(ToolTestCase):

    async def test_01_returns_the_scan_ref(self):
        recorder, result = await self.invoke(
            server.qualys_launch_vm_scan,
            FakeResponse(fixtures.SIMPLE_RETURN_LAUNCH),
            scan_title="nightly", option_id=1234, ip="10.0.0.1")
        self.assertEqual(recorder.last_uri, "api/2.0/fo/scan/")
        self.assertEqual(recorder.last_data["action"], "launch")
        self.assertEqual(result.scan_ref, SCAN_REF)
        self.assertEqual(result.message, "New vm scan launched")
        self.assertIn("Poll", result.note)

    async def test_02_unset_arguments_are_not_sent(self):
        recorder, _ = await self.invoke(
            server.qualys_launch_vm_scan,
            FakeResponse(fixtures.SIMPLE_RETURN_LAUNCH),
            scan_title="nightly", option_id=1234, ip="10.0.0.1")
        for absent in ("option_title", "fqdn", "asset_groups",
                       "asset_group_ids", "iscanner_name", "priority"):
            self.assertNotIn(absent, recorder.last_data)

    async def test_03_parameter_error_becomes_tool_error(self):
        with self.assertRaises(ToolError) as caught:
            await self.invoke(server.qualys_launch_vm_scan,
                              FakeResponse("<OK/>"),
                              scan_title="nightly", option_id=1234)
        self.assertIn("Invalid parameters", str(caught.exception))

    async def test_04_qualys_error_body_becomes_tool_error(self):
        with self.assertRaises(ToolError) as caught:
            await self.invoke(server.qualys_launch_vm_scan,
                              FakeResponse(fixtures.SIMPLE_RETURN_ERROR),
                              scan_title="nightly", option_id=1234,
                              ip="10.0.0.1")
        self.assertIn("1960", str(caught.exception))


class TestListScansTool(ToolTestCase):

    async def test_01_parses_both_scans(self):
        recorder, result = await self.invoke(
            server.qualys_list_vm_scans,
            FakeResponse(fixtures.SCAN_LIST_OUTPUT))
        self.assertEqual(recorder.last_uri, "api/3.0/fo/scan/")
        self.assertEqual(recorder.last_data["action"], "list")
        self.assertEqual(result.total, 2)
        self.assertEqual(result.returned, 2)
        self.assertEqual([s.state for s in result.scans],
                         ["Running", "Finished"])
        self.assertEqual(result.scans[0].scan_ref, SCAN_REF)
        self.assertIn("30 days", result.note)

    async def test_02_scan_ref_is_forwarded_for_polling(self):
        recorder, result = await self.invoke(
            server.qualys_list_vm_scans,
            FakeResponse(fixtures.SCAN_LIST_OUTPUT), scan_ref=SCAN_REF)
        self.assertEqual(recorder.last_data["scan_ref"], SCAN_REF)
        self.assertIsNotNone(result.scans[0].state)

    async def test_03_limit_caps_the_rows(self):
        _, result = await self.invoke(
            server.qualys_list_vm_scans,
            FakeResponse(fixtures.SCAN_LIST_OUTPUT), limit=1)
        self.assertEqual(result.total, 2)
        self.assertEqual(result.returned, 1)

    async def test_04_launched_after_suppresses_the_note(self):
        _, result = await self.invoke(
            server.qualys_list_vm_scans,
            FakeResponse(fixtures.SCAN_LIST_OUTPUT),
            launched_after_datetime="2026-01-01")
        self.assertIsNone(result.note)

    async def test_05_rate_limit_mentions_the_wait(self):
        response = FakeResponse(fixtures.SIMPLE_RETURN_ERROR,
                                status_code=409,
                                headers={"X-RateLimit-ToWait-Sec": "9"})
        with self.assertRaises(ToolError) as caught:
            await self.invoke(server.qualys_list_vm_scans, response)
        message = str(caught.exception)
        self.assertIn("retry in 9s", message)
        self.assertNotIn("secret", message)

    async def test_06_http_error_does_not_leak_credentials(self):
        response = FakeResponse("Bad Login", status_code=401)
        with self.assertRaises(ToolError) as caught:
            await self.invoke(server.qualys_list_vm_scans, response)
        message = str(caught.exception)
        self.assertIn("401", message)
        self.assertNotIn("secret", message)
        self.assertNotIn("admin", message)


class TestFetchTool(ToolTestCase):

    async def test_01_brief_mode_requests_json(self):
        recorder, result = await self.invoke(
            server.qualys_fetch_vm_scan_results,
            FakeResponse(fixtures.SCAN_FETCH_JSON), scan_ref=SCAN_REF)
        self.assertEqual(recorder.last_data["output_format"], "json")
        self.assertEqual(recorder.last_data["action"], "fetch")
        self.assertEqual(result.total, 2)
        self.assertEqual(result.returned, 2)
        self.assertFalse(result.truncated)
        self.assertEqual(result.rows[0]["ip"], "10.0.0.1")

    async def test_02_extended_mode_requests_json_extended(self):
        recorder, _ = await self.invoke(
            server.qualys_fetch_vm_scan_results,
            FakeResponse(fixtures.SCAN_FETCH_JSON), scan_ref=SCAN_REF,
            mode="extended")
        self.assertEqual(recorder.last_data["output_format"],
                         "json_extended")

    async def test_03_max_rows_truncates(self):
        _, result = await self.invoke(
            server.qualys_fetch_vm_scan_results,
            FakeResponse(fixtures.SCAN_FETCH_JSON), scan_ref=SCAN_REF,
            max_rows=1)
        self.assertEqual(result.returned, 1)
        self.assertEqual(result.total, 2)
        self.assertTrue(result.truncated)
        self.assertIn("max_rows", result.note)

    async def test_04_non_json_body_is_reported_clearly(self):
        with self.assertRaises(ToolError) as caught:
            await self.invoke(server.qualys_fetch_vm_scan_results,
                              FakeResponse(fixtures.SIMPLE_RETURN_ERROR),
                              scan_ref=SCAN_REF)
        self.assertIn("not Finished", str(caught.exception))


class TestManageTool(ToolTestCase):

    async def test_01_cancel_posts_both_fields(self):
        recorder, result = await self.invoke(
            server.qualys_manage_vm_scan,
            FakeResponse(fixtures.SIMPLE_RETURN_OK), scan_ref=SCAN_REF,
            action="cancel")
        self.assertEqual(recorder.last_data["action"], "cancel")
        self.assertEqual(recorder.last_data["scan_ref"], SCAN_REF)
        self.assertEqual(result.action, "cancel")
        self.assertEqual(result.scan_ref, SCAN_REF)
        self.assertEqual(result.message, "Scan cancelled")

    async def test_02_qualys_error_becomes_tool_error(self):
        with self.assertRaises(ToolError):
            await self.invoke(server.qualys_manage_vm_scan,
                              FakeResponse(fixtures.SIMPLE_RETURN_ERROR),
                              scan_ref=SCAN_REF, action="delete")


class TestHostTools(ToolTestCase):

    async def test_01_list_hosts_uses_api_5_0(self):
        recorder, result = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(fixtures.HOST_LIST_OUTPUT), ids="1-100")
        self.assertEqual(recorder.last_uri, "api/5.0/fo/asset/host/")
        self.assertEqual(recorder.last_data["action"], "list")
        self.assertEqual(recorder.last_data["ids"], "1-100")
        self.assertEqual(result.returned, 2)
        self.assertEqual(result.hosts[0].ip, "10.0.0.1")
        self.assertEqual(result.hosts[1].os, "Windows 2022")
        self.assertFalse(result.truncated)
        self.assertIsNone(result.next_id_min)

    async def test_02_truncated_page_exposes_next_id_min(self):
        _, result = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(fixtures.HOST_LIST_OUTPUT_TRUNCATED))
        self.assertTrue(result.truncated)
        self.assertEqual(result.next_id_min, "145359")
        self.assertEqual(result.returned, 1)

    async def test_03_detections_are_flattened(self):
        recorder, result = await self.invoke(
            server.qualys_list_host_detections,
            FakeResponse(fixtures.HOST_LIST_VM_DETECTION_OUTPUT),
            severities="4-5")
        self.assertEqual(recorder.last_uri,
                         "api/5.0/fo/asset/host/vm/detection/")
        self.assertEqual(recorder.last_data["severities"], "4-5")
        self.assertEqual(result.returned, 2)
        self.assertEqual([d.qid for d in result.detections],
                         ["38170", "90194"])
        self.assertEqual(result.detections[0].host_id, "145358")
        self.assertEqual(result.detections[0].ip, "10.0.0.1")
        self.assertIn("show_igs=1", result.note)

    async def test_04_detections_truncation(self):
        truncated = fixtures.HOST_LIST_VM_DETECTION_OUTPUT_TRUNCATED
        _, result = await self.invoke(
            server.qualys_list_host_detections, FakeResponse(truncated))
        self.assertTrue(result.truncated)
        self.assertEqual(result.next_id_min, "145359")

    async def test_05_tool_level_defaults_are_sent(self):
        recorder, _ = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(fixtures.HOST_LIST_OUTPUT))
        self.assertEqual(recorder.last_data["details"], "Basic")
        self.assertEqual(recorder.last_data["truncation_limit"], 100)
        recorder, _ = await self.invoke(
            server.qualys_list_host_detections,
            FakeResponse(fixtures.HOST_LIST_VM_DETECTION_OUTPUT))
        self.assertEqual(recorder.last_data["show_igs"], 0)
        self.assertEqual(recorder.last_data["truncation_limit"], 25)


@unittest.skipUnless(SKIP_REASON is None, SKIP_REASON or "")
class TestToolSchemas(unittest.TestCase):
    """The wire contract every MCP client sees."""

    def tools(self):
        return server.mcp._tool_manager.list_tools()

    def test_01_ctx_is_never_exposed_to_the_model(self):
        for tool in self.tools():
            properties = tool.parameters.get("properties", {})
            self.assertNotIn("ctx", properties, tool.name)

    def test_02_every_tool_has_an_output_schema(self):
        for tool in self.tools():
            self.assertTrue(tool.output_schema, tool.name)

    def test_03_destructive_tools_are_annotated(self):
        by_name = dict((t.name, t) for t in self.tools())
        manage = by_name["qualys_manage_vm_scan"]
        self.assertTrue(manage.annotations.destructiveHint)
        launch = by_name["qualys_launch_vm_scan"]
        self.assertFalse(launch.annotations.readOnlyHint)
        for name in ("qualys_list_vm_scans", "qualys_list_hosts",
                     "qualys_list_host_detections",
                     "qualys_fetch_vm_scan_results"):
            self.assertTrue(by_name[name].annotations.readOnlyHint, name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
