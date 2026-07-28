# -*- coding: utf-8 -*-
import unittest

from pyqualys.utils import util
from pyqualys.tests import fixtures


class TestDecodeXml(unittest.TestCase):
    """decode_xml must never raise, whatever Qualys sends back."""

    def test_01_html_error_page_falls_back(self):
        response = util.decode_xml(fixtures.HTML_ERROR_PAGE)
        self.assertEqual(response["type"], "xml")
        self.assertEqual(response["data"], fixtures.HTML_ERROR_PAGE)

    def test_02_csv_body_falls_back(self):
        response = util.decode_xml(fixtures.SCAN_FETCH_CSV)
        self.assertEqual(response["type"], "xml")
        self.assertEqual(response["data"], fixtures.SCAN_FETCH_CSV)

    def test_03_empty_body_falls_back(self):
        response = util.decode_xml("")
        self.assertEqual(response["type"], "xml")
        self.assertEqual(response["data"], "")

    def test_04_json_body_falls_back(self):
        response = util.decode_xml(fixtures.JSON_BODY)
        self.assertEqual(response["type"], "xml")
        self.assertEqual(response["data"], fixtures.JSON_BODY)

    def test_05_none_body_falls_back(self):
        response = util.decode_xml(None)
        self.assertEqual(response["type"], "xml")
        self.assertIsNone(response["data"])

    def test_06_valid_xml_is_decoded(self):
        response = util.decode_xml(fixtures.SCAN_LIST_OUTPUT)
        self.assertEqual(response["type"], "json")
        scans = response["data"]["SCAN_LIST_OUTPUT"]["RESPONSE"]
        self.assertEqual(len(scans["SCAN_LIST"]["SCAN"]), 2)

    def test_07_service_response_is_unwrapped(self):
        response = util.decode_xml(fixtures.SERVICE_RESPONSE_XML)
        self.assertEqual(response["type"], "json")
        self.assertEqual(response["data"]["responseCode"], "SUCCESS")
        self.assertNotIn("ServiceResponse", response["data"])


if __name__ == '__main__':
    unittest.main(verbosity=2)
