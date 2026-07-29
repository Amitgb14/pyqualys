# -*- coding: utf-8 -*-
"""
Every request this library makes must land on the URI the vendor
documents for that operation, at the API version the vendor still
supports.

This is the check that would have caught the mistake the project came
closest to shipping: a single ``api/2.0/`` prefix applied to all five
operations. Qualys versions endpoints - and in the case of ``/fo/scan/``,
individual *actions* of one endpoint - independently, and as of the
July 2026 guide the 2.0 variants of Host List, Host List Detection and
scan listing are all past End of Support.

The expected values come from :data:`vendor_samples.DOCUMENTED_URIS`,
which cites the guide page each one was read from.
"""
import unittest

import pyqualys
from pyqualys.services.vulnerability import VulnerabilityService
from pyqualys.tests.contract_tests import vendor_samples as vendor
from pyqualys.tests.fixtures import FakeResponse, Recorder
from pyqualys.utils.session import APISession

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

HOST = "https://qualysapi.qualys.com/"


def build_service(fmt="xml", **kwargs):
    api = pyqualys.QualysAPI(username="admin", password="secret", host=HOST)
    service = VulnerabilityService(api.session, **kwargs)
    service.FORMAT = fmt
    return service


def record(call, response, service=None):
    """Run ``call(service)`` against a recorded session."""
    service = service or build_service()
    recorder = Recorder(FakeResponse(response))
    with mock.patch.object(APISession, "post", recorder):
        call(service)
    return recorder


class TestScanEndpointVersions(unittest.TestCase):
    """/fo/scan/ is versioned per action, not per endpoint."""

    def test_01_launch_uses_2_0(self):
        recorder = record(
            lambda s: s.scanner.start_scan(option_id=1234, ip="10.0.0.1"),
            vendor.LAUNCH_SIMPLE_RETURN)
        self.assertEqual(recorder.last_uri,
                         vendor.DOCUMENTED_URIS["scan_launch"])
        self.assertEqual(recorder.last_data["action"], "launch")

    def test_02_list_uses_3_0(self):
        recorder = record(lambda s: s.scanner.scan_list(),
                          vendor.SCAN_LIST_OUTPUT)
        self.assertEqual(recorder.last_uri,
                         vendor.DOCUMENTED_URIS["scan_list"])
        self.assertEqual(recorder.last_data["action"], "list")

    def test_03_fetch_uses_2_0(self):
        recorder = record(
            lambda s: s.scanner.get_scan_report(
                scan_ref=vendor.LAUNCH_SCAN_REF),
            vendor.LAUNCH_SIMPLE_RETURN)
        self.assertEqual(recorder.last_uri,
                         vendor.DOCUMENTED_URIS["scan_fetch"])
        self.assertEqual(recorder.last_data["action"], "fetch")

    def test_04_every_manage_action_uses_2_0(self):
        # Guide page 56 lists cancel, pause, resume, delete and fetch
        # together under one heading, "Manage VM Scans", at one version.
        for action in ("cancel", "pause", "resume", "delete"):
            recorder = record(
                lambda s, a=action: s.scanner.manage_scan(
                    action=a, scan_ref=vendor.LAUNCH_SCAN_REF),
                vendor.LAUNCH_SIMPLE_RETURN)
            self.assertEqual(recorder.last_uri,
                             vendor.DOCUMENTED_URIS["scan_manage"],
                             "action={0} went to the wrong version".format(
                                 action))

    def test_05_listing_is_the_only_action_that_differs(self):
        # If a future edit moves the whole endpoint to one prefix again,
        # list and launch collapsing onto the same URI is the symptom.
        launch = record(
            lambda s: s.scanner.start_scan(option_id=1234, ip="10.0.0.1"),
            vendor.LAUNCH_SIMPLE_RETURN).last_uri
        listing = record(lambda s: s.scanner.scan_list(),
                         vendor.SCAN_LIST_OUTPUT).last_uri
        self.assertNotEqual(launch, listing)


class TestAssetEndpointVersions(unittest.TestCase):

    def test_01_host_list_uses_5_0(self):
        recorder = record(lambda s: s.list_hosts(),
                          vendor.HOST_LIST_OUTPUT_TRUNCATED)
        self.assertEqual(recorder.last_uri,
                         vendor.DOCUMENTED_URIS["host_list"])
        self.assertEqual(recorder.last_data["action"], "list")

    def test_02_host_detection_uses_5_0(self):
        recorder = record(lambda s: s.list_host_detections(),
                          vendor.HOST_LIST_VM_DETECTION_OUTPUT)
        self.assertEqual(recorder.last_uri,
                         vendor.DOCUMENTED_URIS["host_detection_list"])
        self.assertEqual(recorder.last_data["action"], "list")

    def test_03_detection_is_not_nested_under_host_list(self):
        # /fo/asset/host/vm/detection/ is a distinct endpoint, not a
        # parameter on Host List. Building it by string concatenation
        # from the host URI is a plausible refactor that would break it.
        self.assertTrue(
            vendor.DOCUMENTED_URIS["host_detection_list"].startswith(
                vendor.DOCUMENTED_URIS["host_list"]))
        recorder = record(lambda s: s.list_host_detections(),
                          vendor.HOST_LIST_VM_DETECTION_OUTPUT)
        self.assertNotEqual(recorder.last_uri,
                            vendor.DOCUMENTED_URIS["host_list"])


class TestPinnedVersionEscapeHatch(unittest.TestCase):
    """
    ``pin_api_version=True`` collapses everything back onto one prefix.

    It exists so a subscription on an older platform build can keep
    working, but the guide's EOS dates have already passed for those
    prefixes, so this is a debugging aid rather than a supported mode.
    The test pins the behaviour so nobody quietly makes it the default.
    """

    def test_01_pinning_overrides_the_documented_versions(self):
        service = build_service(pin_api_version=True)
        recorder = record(lambda s: s.list_hosts(),
                          vendor.HOST_LIST_OUTPUT_TRUNCATED,
                          service=service)
        self.assertEqual(recorder.last_uri, "api/2.0/fo/asset/host/")
        self.assertNotEqual(recorder.last_uri,
                            vendor.DOCUMENTED_URIS["host_list"])

    def test_02_default_is_not_pinned(self):
        service = build_service()
        recorder = record(lambda s: s.list_hosts(),
                          vendor.HOST_LIST_OUTPUT_TRUNCATED,
                          service=service)
        self.assertEqual(recorder.last_uri,
                         vendor.DOCUMENTED_URIS["host_list"])


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
