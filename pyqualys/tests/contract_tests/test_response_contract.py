# -*- coding: utf-8 -*-
"""
Parse the vendor's own documented response bodies.

The existing suite parses fixtures this project wrote, which proves the
parsers are self-consistent and nothing more. These bodies were copied
out of the Qualys API user guide instead, so they carry the incidental
formatting a hand-written fixture never has: CDATA sections indented onto
their own lines, empty elements sitting among populated siblings, a
pagination URL padded with newlines and carrying parameters the original
request never sent.

Each of those is a plausible way for a parser to fail against the real
platform while passing its own tests.
"""
import unittest

import pyqualys
from pyqualys.services.vulnerability import VulnerabilityService
from pyqualys.services.vulnerability.host import next_page_params
from pyqualys.tests.contract_tests import vendor_samples as vendor
from pyqualys.tests.fixtures import FakeResponse, Recorder
from pyqualys.utils.session import APISession
from pyqualys.utils.util import decode_xml

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

HOST = "https://qualysapi.qualys.com/"


def build_service(fmt="json"):
    api = pyqualys.QualysAPI(username="admin", password="secret", host=HOST)
    service = VulnerabilityService(api.session)
    service.FORMAT = fmt
    return service


class TestTruncationCursor(unittest.TestCase):
    """
    Pagination is the highest-consequence parser in the library.

    When it silently fails to find the next page, nothing raises: the
    caller just receives the first page and believes it saw everything.
    An inventory or triage answer built on that is quietly wrong rather
    than visibly broken, which is the worst failure mode available here.
    """

    def test_01_host_list_warning_yields_the_next_id_min(self):
        params = next_page_params(vendor.HOST_LIST_OUTPUT_TRUNCATED)
        self.assertIsNotNone(
            params, "the documented WARNING block was not recognised")
        self.assertEqual(params["id_min"], vendor.HOST_LIST_NEXT_ID_MIN)

    def test_02_detection_warning_yields_the_next_id_min(self):
        params = next_page_params(vendor.HOST_LIST_VM_DETECTION_TRUNCATED)
        self.assertIsNotNone(params)
        self.assertEqual(params["id_min"], vendor.DETECTION_NEXT_ID_MIN)

    def test_03_newline_padded_url_is_still_read(self):
        # The Host List sample prints <URL> with the CDATA indented on
        # its own line, so the element text begins and ends with
        # whitespace. Feeding that to a URL parser unstripped produces a
        # scheme of "\n            https", and no query at all.
        self.assertIn("\n", vendor.HOST_LIST_OUTPUT_TRUNCATED[
            vendor.HOST_LIST_OUTPUT_TRUNCATED.index("<URL>"):
            vendor.HOST_LIST_OUTPUT_TRUNCATED.index("</URL>")])
        params = next_page_params(vendor.HOST_LIST_OUTPUT_TRUNCATED)
        self.assertEqual(params["id_min"], vendor.HOST_LIST_NEXT_ID_MIN)

    def test_04_only_query_parameters_are_taken(self):
        # The truncation URL is absolute and, in this sample, points at a
        # different platform host (p01.eng.sjc01) than the one the client
        # is configured for. APISession builds its URI by appending to
        # the configured host, so anything but the query string here
        # would send the next page request to the wrong platform.
        params = next_page_params(vendor.HOST_LIST_OUTPUT_TRUNCATED)
        joined = "".join(str(v) for v in params.values())
        self.assertNotIn("qualysapi", joined)
        self.assertNotIn("/api/", joined)
        self.assertNotIn("http", joined)

    def test_05_parameters_the_request_never_sent_are_preserved(self):
        # Qualys echoes its own defaults back in the truncation URL:
        # details=None and cloud_agent_activationkey=0 were not in the
        # original request. Dropping them changes what the next page
        # returns, so they have to survive into the following call.
        params = next_page_params(vendor.HOST_LIST_OUTPUT_TRUNCATED)
        self.assertEqual(params["details"], "None")
        self.assertEqual(params["cloud_agent_activationkey"], "0")
        self.assertEqual(params["truncation_limit"], "100")

    def test_06_final_page_reports_no_cursor(self):
        self.assertIsNone(
            next_page_params(vendor.HOST_LIST_OUTPUT_FINAL_PAGE))

    def test_07_iteration_follows_the_documented_cursor(self):
        service = build_service()
        recorder = Recorder([
            FakeResponse(vendor.HOST_LIST_OUTPUT_TRUNCATED),
            FakeResponse(vendor.HOST_LIST_OUTPUT_FINAL_PAGE),
        ])
        with mock.patch.object(APISession, "post", recorder):
            pages = list(service.iter_hosts(truncation_limit=100))

        self.assertEqual(len(pages), 2)
        self.assertEqual(len(recorder.calls), 2)

        first, second = recorder.calls[0][1], recorder.calls[1][1]
        self.assertNotIn("id_min", first)
        self.assertEqual(second["id_min"], vendor.HOST_LIST_NEXT_ID_MIN)
        # The caller's own parameters must not be lost when the cursor
        # parameters are merged in.
        self.assertEqual(second["action"], "list")

    def test_08_iteration_stops_at_the_final_page(self):
        # Recorder replays its last response for every call beyond the
        # list, so a parser that kept finding a cursor would loop until
        # the test times out. Reaching the assertion at all is the point.
        service = build_service()
        recorder = Recorder([
            FakeResponse(vendor.HOST_LIST_VM_DETECTION_TRUNCATED),
            FakeResponse(vendor.HOST_LIST_VM_DETECTION_OUTPUT),
        ])
        with mock.patch.object(APISession, "post", recorder):
            pages = list(service.iter_host_detections())
        self.assertEqual(len(pages), 2)


class TestVendorBodyDecoding(unittest.TestCase):
    """The formatting quirks the vendor's samples carry."""

    def test_01_indented_cdata_loses_its_surrounding_whitespace(self):
        # <OS>\n  <![CDATA[Windows XP]]>\n</OS> must not decode to
        # "\n            Windows XP\n          ".
        payload = decode_xml(vendor.HOST_LIST_VM_DETECTION_OUTPUT)["data"]
        host = payload["HOST_LIST_VM_DETECTION_OUTPUT"]["RESPONSE"][
            "HOST_LIST"]["HOST"]
        self.assertEqual(host["OS"], "Windows XP")
        self.assertEqual(host["DNS"], "w2kserver-tmp3.vuln.example.com")

    def test_02_empty_element_among_siblings_decodes_to_none(self):
        payload = decode_xml(vendor.HOST_LIST_VM_DETECTION_OUTPUT)["data"]
        host = payload["HOST_LIST_VM_DETECTION_OUTPUT"]["RESPONSE"][
            "HOST_LIST"]["HOST"]
        self.assertIn("ASSET_GROUP_LIST", host)
        self.assertIsNone(host["ASSET_GROUP_LIST"])

    def test_03_nested_structures_survive(self):
        payload = decode_xml(vendor.HOST_LIST_VM_DETECTION_OUTPUT)["data"]
        host = payload["HOST_LIST_VM_DETECTION_OUTPUT"]["RESPONSE"][
            "HOST_LIST"]["HOST"]
        self.assertEqual(host["DNS_DATA"]["FQDN"],
                         "w2kserver-tmp3.vuln.example.com")

    def test_04_scan_status_carries_a_sub_state(self):
        # STATUS is a container, not a leaf: reading it as text gives
        # nothing useful, and SUB_STATE explains states like Finished
        # with No_Host that otherwise look like a successful empty scan.
        payload = decode_xml(vendor.SCAN_LIST_OUTPUT)["data"]
        scan = payload["SCAN_LIST_OUTPUT"]["RESPONSE"]["SCAN_LIST"]["SCAN"]
        self.assertEqual(scan["STATUS"]["STATE"], "Finished")
        self.assertEqual(scan["STATUS"]["SUB_STATE"], "No_Host")

    def test_05_launch_reference_is_addressed_by_key_not_position(self):
        # SIMPLE_RETURN returns ID and REFERENCE as an unordered ITEM
        # list of KEY/VALUE pairs. Reading items[1] happens to work on
        # this sample and is not what the DTD promises.
        payload = decode_xml(vendor.LAUNCH_SIMPLE_RETURN)["data"]
        items = payload["SIMPLE_RETURN"]["RESPONSE"]["ITEM_LIST"]["ITEM"]
        pairs = dict((item["KEY"], item["VALUE"]) for item in items)
        self.assertEqual(pairs["REFERENCE"], vendor.LAUNCH_SCAN_REF)
        self.assertEqual(pairs["ID"], "136992")


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
