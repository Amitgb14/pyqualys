# -*- coding: utf-8 -*-
"""
The MCP tools against the vendor's documented response bodies.

This is the layer the Claude Code plugin exposes, so a parsing gap here
does not surface as an exception - it surfaces as a confident, wrong
answer. A tool that finds no ``<HOST>`` elements returns ``returned=0``
and an empty list, which reads exactly like a subscription with no
assets.

Skipped on Python < 3.10 or when the optional ``mcp`` extra is absent,
following ``pyqualys.tests.mcp_tests``.
"""
import sys
import unittest

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

server = None
anyio = None
SKIP_REASON = None

if sys.version_info < (3, 10):
    SKIP_REASON = "pyqualys.mcp requires Python 3.10 or newer"
else:
    try:
        import anyio
        from pyqualys.mcp import server
    except ImportError as e:                            # pragma: no cover
        SKIP_REASON = "mcp package is not installed ({0})".format(e)

if SKIP_REASON is None:
    import pyqualys
    from pyqualys.tests.contract_tests import vendor_samples as vendor
    from pyqualys.tests.fixtures import FakeResponse, Recorder
    from pyqualys.utils.session import APISession

HOST = "https://qualysapi.qualys.com/"


class FakeRequestContext(object):

    def __init__(self, lifespan_context):
        self.lifespan_context = lifespan_context


class FakeContext(object):

    def __init__(self, lifespan_context):
        self.request_context = FakeRequestContext(lifespan_context)


@unittest.skipUnless(SKIP_REASON is None, SKIP_REASON or "")
class ContractToolTestCase(unittest.IsolatedAsyncioTestCase):

    def build_service(self):
        api = pyqualys.QualysAPI(username="admin", password="secret",
                                 host=HOST)
        service = api.service("vulnerability")
        service.FORMAT = "json"
        return service

    async def invoke(self, tool, responses, **kwargs):
        ctx = FakeContext(server.QualysCtx(service=self.build_service(),
                                           gate=anyio.Semaphore(2),
                                           timeout=30))
        recorder = Recorder(responses)
        with mock.patch.object(APISession, "post", recorder):
            result = await tool(ctx, **kwargs)
        return recorder, result


class TestLaunchContract(ContractToolTestCase):

    async def test_01_scan_ref_comes_from_the_documented_item_list(self):
        _, result = await self.invoke(
            server.qualys_launch_vm_scan,
            FakeResponse(vendor.LAUNCH_SIMPLE_RETURN),
            scan_title="nightly", option_id=1234, ip="10.0.0.1")
        self.assertEqual(result.scan_ref, vendor.LAUNCH_SCAN_REF)
        self.assertEqual(result.message, "New vm scan launched")

    async def test_02_the_caller_is_told_the_scan_is_asynchronous(self):
        # Launch returns a reference, not results. Without this note a
        # model reasonably reports the scan as complete.
        _, result = await self.invoke(
            server.qualys_launch_vm_scan,
            FakeResponse(vendor.LAUNCH_SIMPLE_RETURN),
            scan_title="nightly", option_id=1234, ip="10.0.0.1")
        self.assertIn("asynchronously", result.note)


class TestScanListContract(ContractToolTestCase):

    async def test_01_summary_fields_map_to_the_documented_elements(self):
        _, result = await self.invoke(server.qualys_list_vm_scans,
                                      FakeResponse(vendor.SCAN_LIST_OUTPUT))
        self.assertEqual(result.returned, 1)
        scan = result.scans[0]
        self.assertEqual(scan.scan_ref, "scan/1735543972.16308")
        self.assertEqual(scan.state, "Finished")
        self.assertEqual(scan.launch_datetime, "2024-12-30T07:32:52Z")
        self.assertEqual(scan.processed, "1")

    async def test_02_cdata_values_arrive_clean(self):
        # TITLE and TARGET are printed as indented CDATA in the guide.
        _, result = await self.invoke(server.qualys_list_vm_scans,
                                      FakeResponse(vendor.SCAN_LIST_OUTPUT))
        scan = result.scans[0]
        self.assertEqual(scan.title, "Azure Scan Internal Test")
        self.assertNotIn("\n", scan.target or "")
        self.assertTrue((scan.target or "").startswith("65188eb1"))

    async def test_03_single_scan_is_not_flattened_into_characters(self):
        # One <SCAN> collapses to a dict rather than a list of dicts.
        # Iterating that dict directly yields its keys, and every scan
        # summary comes back empty.
        _, result = await self.invoke(server.qualys_list_vm_scans,
                                      FakeResponse(vendor.SCAN_LIST_OUTPUT))
        self.assertEqual(len(result.scans), 1)
        self.assertIsNotNone(result.scans[0].scan_ref)

    async def test_04_the_30_day_default_is_disclosed(self):
        _, result = await self.invoke(server.qualys_list_vm_scans,
                                      FakeResponse(vendor.SCAN_LIST_OUTPUT))
        self.assertIn("30 days", result.note or "")


class TestHostListContract(ContractToolTestCase):

    async def test_01_hosts_are_parsed_from_the_documented_body(self):
        _, result = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(vendor.HOST_LIST_OUTPUT_TRUNCATED))
        self.assertEqual(result.returned, 1)
        host = result.hosts[0]
        self.assertEqual(host.id, "135151")
        self.assertEqual(host.ip, "11.11.1.111")
        self.assertEqual(host.tracking_method, "EC2")
        self.assertEqual(host.dns, "i-0bb87c3281243cdfd")
        self.assertEqual(host.os, "Amazon Linux 2016.09")

    async def test_02_truncation_is_reported_to_the_caller(self):
        _, result = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(vendor.HOST_LIST_OUTPUT_TRUNCATED))
        self.assertTrue(result.truncated)
        self.assertEqual(result.next_id_min, vendor.HOST_LIST_NEXT_ID_MIN)

    async def test_03_final_page_is_not_reported_as_truncated(self):
        _, result = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(vendor.HOST_LIST_OUTPUT_FINAL_PAGE))
        self.assertFalse(result.truncated)
        self.assertIsNone(result.next_id_min)


class TestDetectionContract(ContractToolTestCase):

    async def test_01_detections_are_flattened_per_host(self):
        _, result = await self.invoke(
            server.qualys_list_host_detections,
            FakeResponse(vendor.HOST_LIST_VM_DETECTION_OUTPUT))
        self.assertEqual(result.returned, 1)
        row = result.detections[0]
        self.assertEqual(row.host_id, "4203254")
        self.assertEqual(row.ip, "11.11.11.11")
        self.assertEqual(row.qid, "11")
        self.assertEqual(row.severity, "2")
        self.assertEqual(row.status, "New")
        self.assertEqual(row.type, "Confirmed")

    async def test_02_indented_cdata_dns_is_not_padded(self):
        _, result = await self.invoke(
            server.qualys_list_host_detections,
            FakeResponse(vendor.HOST_LIST_VM_DETECTION_OUTPUT))
        self.assertEqual(result.detections[0].dns,
                         "w2kserver-tmp3.vuln.example.com")

    async def test_03_truncation_cursor_is_surfaced(self):
        _, result = await self.invoke(
            server.qualys_list_host_detections,
            FakeResponse(vendor.HOST_LIST_VM_DETECTION_TRUNCATED))
        self.assertTrue(result.truncated)
        self.assertEqual(result.next_id_min, vendor.DETECTION_NEXT_ID_MIN)


class TestUnrecognisedRootElement(ContractToolTestCase):
    """
    A known divergence, recorded rather than asserted as correct.

    Guide page 1011 prints one Host List response with every element name
    in lower case, unlike every other sample in that chapter. Whether the
    platform emits that or the guide is misprinted cannot be settled from
    documentation, and this project has no live subscription to ask.

    What the test below fixes in place is the *shape* of the failure, not
    an endorsement of it: an unrecognised root produces an empty result
    and no error, which a caller cannot distinguish from a subscription
    that genuinely has no hosts. If a live subscription ever confirms the
    lower-case form, this test is the one to change - and the fix is to
    fail loudly on an unrecognised root, not only to accept lower case.
    """

    async def test_01_lowercase_body_yields_no_hosts_and_no_error(self):
        _, result = await self.invoke(
            server.qualys_list_hosts,
            FakeResponse(vendor.HOST_LIST_OUTPUT_LOWERCASE))
        self.assertEqual(result.returned, 0)
        self.assertEqual(result.hosts, [])

    async def test_02_the_sample_does_contain_a_host(self):
        # Guarding the premise: the body is not simply empty.
        self.assertIn("<id>2584392</id>",
                      vendor.HOST_LIST_OUTPUT_LOWERCASE)


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
