# -*- coding: utf-8 -*-
"""
Qualys blocks with HTTP 409, and the two ways it blocks are not alike.

Guide pages 15-17 document both. A rate limit block carries
``X-RateLimit-ToWait-Sec``, so a client can wait exactly that long. A
concurrency block does not: the guide states plainly that "in case where
the concurrency limit has been reached, no information about rate limits
will appear in the HTTP headers", and that the concurrency error takes
precedence when both conditions apply.

That asymmetry is the trap. Code written against the rate-limit sample
alone tends to assume the header is always there, and then either crashes
or sleeps for ``None`` seconds on the concurrency path - which is the
path a caller hits precisely when it is running several requests at once,
as the MCP server does.
"""
import unittest

import pyqualys
from pyqualys.errors import QualysAPIError, RateLimitError
from pyqualys.services.vulnerability import VulnerabilityService
from pyqualys.tests.contract_tests import vendor_samples as vendor
from pyqualys.tests.fixtures import FakeResponse, Recorder
from pyqualys.utils.session import APISession

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

HOST = "https://qualysapi.qualys.com/"
PASSWORD = "sup3r-s3cret"

# The guide does not print a body for either 409 sample, only the
# headers; Content-Type says application/xml, and the platform returns
# its usual error envelope.
BLOCKED_BODY = """<?xml version="1.0" encoding="UTF-8" ?>
<SIMPLE_RETURN>
  <RESPONSE>
    <DATETIME>2018-04-22T00:13:18Z</DATETIME>
    <CODE>1965</CODE>
    <TEXT>You have reached the maximum number of concurrent running
    API calls allowed for your account.</TEXT>
  </RESPONSE>
</SIMPLE_RETURN>"""


def build_service():
    api = pyqualys.QualysAPI(username="admin", password=PASSWORD, host=HOST)
    service = VulnerabilityService(api.session)
    service.FORMAT = "json"
    return service


def call(operation, response):
    """Run ``operation(service)`` against a single recorded response."""
    service = build_service()
    recorder = Recorder(response)
    with mock.patch.object(APISession, "post", recorder):
        return operation(service)


class TestRateLimitBlock(unittest.TestCase):
    """Page 16, Sample 2: HTTP 409 with X-RateLimit-ToWait-Sec: 181."""

    def response(self):
        return FakeResponse(BLOCKED_BODY, status_code=409,
                            headers=dict(vendor.RATE_LIMIT_409_HEADERS))

    def test_01_409_is_a_rate_limit_not_a_generic_error(self):
        with self.assertRaises(RateLimitError):
            call(lambda s: s.list_hosts(), self.response())

    def test_02_wait_period_is_taken_from_the_header(self):
        try:
            call(lambda s: s.list_hosts(), self.response())
        except RateLimitError as e:
            self.assertEqual(e.retry_after, 181)
            self.assertEqual(e.status_code, 409)
        else:                                           # pragma: no cover
            self.fail("expected RateLimitError")

    def test_03_retry_after_is_a_number_callers_can_sleep_on(self):
        # The header arrives as the string "181"; a caller that passes it
        # straight to time.sleep needs it converted here.
        try:
            call(lambda s: s.list_hosts(), self.response())
        except RateLimitError as e:
            self.assertIsInstance(e.retry_after, int)


class TestConcurrencyBlock(unittest.TestCase):
    """Page 17, Sample 3: HTTP 409 with no rate limit headers at all."""

    def response(self):
        return FakeResponse(BLOCKED_BODY, status_code=409,
                            headers=dict(vendor.CONCURRENCY_409_HEADERS))

    def test_01_the_sample_really_has_no_wait_header(self):
        # Guarding the premise of the tests below.
        self.assertNotIn("X-RateLimit-ToWait-Sec",
                         vendor.CONCURRENCY_409_HEADERS)

    def test_02_still_raises_a_rate_limit_error(self):
        with self.assertRaises(RateLimitError):
            call(lambda s: s.list_hosts(), self.response())

    def test_03_missing_header_gives_no_retry_after_and_does_not_crash(self):
        try:
            call(lambda s: s.list_hosts(), self.response())
        except RateLimitError as e:
            self.assertIsNone(
                e.retry_after,
                "a concurrency block carries no wait period; inventing "
                "one would send the caller back too early")
        else:                                           # pragma: no cover
            self.fail("expected RateLimitError")

    def test_04_every_endpoint_blocks_the_same_way(self):
        # Scans and assets have separate request paths in this library,
        # so the 409 handling is implemented twice.
        operations = [
            lambda s: s.list_hosts(),
            lambda s: s.list_host_detections(),
            lambda s: s.scanner.scan_list(),
            lambda s: s.scanner.get_scan_report(
                scan_ref=vendor.LAUNCH_SCAN_REF),
            lambda s: s.scanner.manage_scan(
                action="cancel", scan_ref=vendor.LAUNCH_SCAN_REF),
        ]
        for operation in operations:
            with self.assertRaises(RateLimitError):
                call(operation, self.response())


class TestNotBlocked(unittest.TestCase):

    def test_01_rate_limit_headers_on_a_200_are_not_an_error(self):
        # Every successful response carries the same X-RateLimit family
        # of headers. Keying off their presence rather than the status
        # code would turn every healthy call into a failure.
        result = call(lambda s: s.list_hosts(),
                      FakeResponse(vendor.HOST_LIST_OUTPUT_FINAL_PAGE,
                                   status_code=200,
                                   headers=dict(vendor.OK_200_HEADERS)))
        self.assertIn("HOST_LIST_OUTPUT", result["data"])

    def test_02_other_error_statuses_are_not_rate_limits(self):
        with self.assertRaises(QualysAPIError) as caught:
            call(lambda s: s.list_hosts(),
                 FakeResponse("<html>503</html>", status_code=503))
        self.assertNotIsInstance(caught.exception, RateLimitError)


class TestBlockedErrorsAreSafeToSurface(unittest.TestCase):
    """
    These exceptions reach logs and MCP clients, so they must not carry
    the credentials that produced them.
    """

    def test_01_no_credentials_in_the_message_or_body(self):
        try:
            call(lambda s: s.list_hosts(),
                 FakeResponse(BLOCKED_BODY, status_code=409,
                              headers=dict(vendor.RATE_LIMIT_409_HEADERS)))
        except RateLimitError as e:
            rendered = "{0}{1}".format(e, e.body)
            self.assertNotIn(PASSWORD, rendered)
            self.assertNotIn("admin", rendered)

    def test_02_a_large_body_is_truncated(self):
        try:
            call(lambda s: s.list_hosts(),
                 FakeResponse("x" * 5000, status_code=409,
                              headers=dict(vendor.RATE_LIMIT_409_HEADERS)))
        except RateLimitError as e:
            self.assertLess(len(e.body), 1000)


if __name__ == "__main__":                              # pragma: no cover
    unittest.main()
