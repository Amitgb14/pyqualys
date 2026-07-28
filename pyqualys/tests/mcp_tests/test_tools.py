# -*- coding: utf-8 -*-
import os
import sys
import inspect
import unittest

try:
    from unittest import mock
except ImportError:                                     # pragma: no cover
    import mock

EXPECTED_TOOLS = set([
    "qualys_launch_vm_scan",
    "qualys_list_vm_scans",
    "qualys_fetch_vm_scan_results",
    "qualys_manage_vm_scan",
    "qualys_list_hosts",
    "qualys_list_host_detections",
])

REQUIRED_ENV = ("QUALYS_USERNAME", "QUALYS_PASSWORD", "QUALYS_API_URL")

server = None
SKIP_REASON = None

if sys.version_info < (3, 10):
    SKIP_REASON = "pyqualys.mcp requires Python 3.10 or newer"
else:
    try:
        from pyqualys.mcp import server
    except ImportError as e:                            # pragma: no cover
        SKIP_REASON = "mcp package is not installed ({0})".format(e)


def registered_tools():
    """Return {name: function} for every tool on the FastMCP instance."""
    manager = server.mcp._tool_manager
    tools = manager.list_tools()
    return dict((tool.name, tool.fn) for tool in tools)


@unittest.skipUnless(SKIP_REASON is None, SKIP_REASON or "")
class TestMcpToolRegistry(unittest.TestCase):

    def test_01_exactly_the_expected_tools(self):
        self.assertEqual(set(registered_tools()), EXPECTED_TOOLS)

    def test_02_every_tool_is_a_coroutine(self):
        for name, fn in registered_tools().items():
            self.assertTrue(inspect.iscoroutinefunction(fn),
                            "{0} must be async def".format(name))

    def test_03_tools_are_documented(self):
        for name, fn in registered_tools().items():
            self.assertTrue((fn.__doc__ or "").strip(),
                            "{0} needs a docstring".format(name))

    def test_04_main_is_callable(self):
        self.assertTrue(callable(server.main))


@unittest.skipUnless(SKIP_REASON is None, SKIP_REASON or "")
class TestMcpConfig(unittest.TestCase):

    BASE = {
        "QUALYS_USERNAME": "admin",
        "QUALYS_PASSWORD": "secret",
        "QUALYS_API_URL": "https://qualysapi.qualys.com",
    }

    def env(self, **overrides):
        environ = dict(self.BASE)
        environ.update(overrides)
        for key in list(environ):
            if environ[key] is None:
                del environ[key]
        return mock.patch.dict(os.environ, environ, clear=True)

    def test_01_url_is_normalised(self):
        with self.env():
            config = server._load_config()
        self.assertEqual(config.api_url,
                         "https://qualysapi.qualys.com/")
        self.assertTrue(config.verify_ssl)
        self.assertEqual(config.timeout, 300)
        self.assertEqual(config.concurrency, 2)

    def test_02_trailing_slash_is_not_doubled(self):
        with self.env(QUALYS_API_URL="https://qualysapi.qualys.com/"):
            config = server._load_config()
        self.assertEqual(config.api_url,
                         "https://qualysapi.qualys.com/")

    def test_03_missing_variables_raise(self):
        for name in REQUIRED_ENV:
            with self.env(**{name: None}):
                with self.assertRaises(ValueError):
                    server._load_config()

    def test_04_unexpanded_placeholder_raises(self):
        for name in REQUIRED_ENV:
            with self.env(**{name: "${" + name + "}"}):
                with self.assertRaises(ValueError):
                    server._load_config()

    def test_05_verify_ssl_opt_out(self):
        with self.env(QUALYS_VERIFY_SSL="false"):
            config = server._load_config()
        self.assertFalse(config.verify_ssl)

    def test_06_numeric_overrides(self):
        with self.env(QUALYS_TIMEOUT="60", QUALYS_CONCURRENCY="1"):
            config = server._load_config()
        self.assertEqual(config.timeout, 60)
        self.assertEqual(config.concurrency, 1)

    def test_07_bad_numeric_value_raises(self):
        with self.env(QUALYS_TIMEOUT="soon"):
            with self.assertRaises(ValueError):
                server._load_config()


class TestImportSafety(unittest.TestCase):
    """`import pyqualys` must never drag in the optional MCP server."""

    def test_01_pyqualys_does_not_import_mcp(self):
        import subprocess
        code = ("import sys, pyqualys; "
                "sys.exit(1 if 'pyqualys.mcp' in sys.modules else 0)")
        result = subprocess.call([sys.executable, "-c", code])
        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
