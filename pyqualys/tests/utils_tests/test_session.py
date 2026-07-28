# -*- coding: utf-8 -*-
import unittest

import pyqualys
from pyqualys.errors import ParameterError
from pyqualys.utils import connect
from pyqualys.utils.session import APISession
from pyqualys.tests.fixtures import FakeResponse

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

HOST_NO_SLASH = "https://qualysapi.qualys.com"
SCAN_URI = "api/2.0/fo/scan/"


class TestAPISession(unittest.TestCase):

    def setUp(self):
        self.session = APISession(username="admin", password="secret",
                                  host=HOST_NO_SLASH)

    def test_01_host_is_normalised(self):
        self.assertEqual(self.session.host,
                         "https://qualysapi.qualys.com/")

    def test_02_post_builds_the_expected_url(self):
        with mock.patch("requests.Session.post") as post:
            post.return_value = FakeResponse("<OK/>")
            self.session.post(SCAN_URI, {"action": "list"})
        args, kwargs = post.call_args
        self.assertEqual(args[0],
                         "https://qualysapi.qualys.com/" + SCAN_URI)
        self.assertEqual(kwargs["data"], {"action": "list"})

    def test_03_get_uses_params_not_body(self):
        with mock.patch("requests.Session.get") as get:
            get.return_value = FakeResponse("<OK/>")
            self.session.get("api/2.0/fo/report/", {"action": "list"})
        args, kwargs = get.call_args
        self.assertEqual(kwargs["params"], {"action": "list"})
        self.assertNotIn("data", kwargs)

    def test_04_put_uses_params_not_body(self):
        with mock.patch("requests.Session.put") as put:
            put.return_value = FakeResponse("<OK/>")
            self.session.put("api/2.0/fo/report/", {"id": 1})
        args, kwargs = put.call_args
        self.assertEqual(kwargs["params"], {"id": 1})
        self.assertNotIn("data", kwargs)

    def test_05_delete_uses_params_not_body(self):
        with mock.patch("requests.Session.delete") as delete:
            delete.return_value = FakeResponse("<OK/>")
            self.session.delete("api/2.0/fo/report/", {"id": 1})
        args, kwargs = delete.call_args
        self.assertEqual(kwargs["params"], {"id": 1})
        self.assertNotIn("data", kwargs)

    def test_06_verify_ssl_defaults_to_true(self):
        self.assertTrue(self.session.verify_ssl)
        with mock.patch("requests.Session.post") as post:
            post.return_value = FakeResponse("<OK/>")
            self.session.post(SCAN_URI, {})
        self.assertTrue(post.call_args[1]["verify"])

    def test_07_verify_ssl_opt_out_is_honoured(self):
        api = pyqualys.QualysAPI(username="admin", password="secret",
                                 host=HOST_NO_SLASH, verify_ssl=False)
        self.assertFalse(api.session.verify_ssl)
        with mock.patch("requests.Session.post") as post:
            post.return_value = FakeResponse("<OK/>")
            api.session.post(SCAN_URI, {})
        self.assertFalse(post.call_args[1]["verify"])

    def test_08_timeout_is_forwarded_on_every_verb(self):
        session = APISession(username="admin", password="secret",
                             host=HOST_NO_SLASH, timeout=17)
        for verb in ("post", "get", "put", "delete"):
            with mock.patch("requests.Session." + verb) as sent:
                sent.return_value = FakeResponse("<OK/>")
                getattr(session, verb)(SCAN_URI, {})
            self.assertEqual(sent.call_args[1]["timeout"], 17)

    def test_09_headers(self):
        headers = self.session._APISession__session.headers
        self.assertEqual(headers["X-Requested-With"],
                         "pyqualys/python-3x")
        self.assertIn("pyqualys/", headers["User-Agent"])
        self.assertIn(pyqualys.__version__, headers["User-Agent"])


class TestQualysAPI(unittest.TestCase):

    def test_01_missing_username_raises(self):
        with self.assertRaises(ParameterError):
            pyqualys.QualysAPI(password="secret", host=HOST_NO_SLASH)

    def test_02_missing_password_raises(self):
        with self.assertRaises(ParameterError):
            pyqualys.QualysAPI(username="admin", host=HOST_NO_SLASH)

    def test_03_missing_host_raises(self):
        with self.assertRaises(ParameterError):
            pyqualys.QualysAPI(username="admin", password="secret")

    def test_04_unknown_service_raises(self):
        api = pyqualys.QualysAPI(username="admin", password="secret",
                                 host=HOST_NO_SLASH)
        with self.assertRaises(ParameterError):
            api.service("nope")

    def test_05_parameter_error_is_a_value_error(self):
        self.assertTrue(issubclass(ParameterError, ValueError))

    def test_06_session_property(self):
        api = pyqualys.QualysAPI(username="admin", password="secret",
                                 host=HOST_NO_SLASH)
        self.assertIsInstance(api.session, APISession)

    def test_07_services_list(self):
        api = pyqualys.QualysAPI(username="admin", password="secret",
                                 host=HOST_NO_SLASH)
        self.assertEqual(api.list_services(), connect.SERVICES)


if __name__ == '__main__':
    unittest.main(verbosity=2)
