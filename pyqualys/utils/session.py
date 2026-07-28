# -*- coding: utf-8 -*-
import logging
from requests import Session
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)

# X-Requested-With is mandatory for Qualys basic-auth calls (CSRF guard).
HEADERS = {"X-Requested-With": "pyqualys/python-3x"}

DEFAULT_TIMEOUT = 300
PROJECT_URL = "https://github.com/Amitgb14/pyqualys"


def user_agent():
    """
    Build the User-Agent header value.

    The version is imported lazily: ``pyqualys/__init__.py`` imports this
    module, so a module level import would be circular.
    """
    try:
        from .. import __version__ as version
    except Exception:                                   # pragma: no cover
        version = "unknown"
    return "pyqualys/{0} ({1})".format(version, PROJECT_URL)


class APISession(object):

    def __init__(self, username, password, host, max_retries=3,
                 verify_ssl=True, timeout=DEFAULT_TIMEOUT, **kwargs):
        """
        Thin wrapper around ``requests.Session`` for the Qualys API.

        :param verify_ssl: verify the platform TLS certificate. Defaults
                           to True; set False only for private cloud
                           platforms using self signed certificates.
        :param timeout: per request timeout in seconds.
        """
        self.__host = host.rstrip("/") + "/"
        self.__session = Session()
        self.__session.auth = (username, password)
        self.__session.headers.update(HEADERS)
        self.__session.headers["User-Agent"] = user_agent()
        self.__session.mount('http://', HTTPAdapter(max_retries=max_retries))
        self.__session.mount('https://', HTTPAdapter(max_retries=max_retries))

        self.verify_ssl = verify_ssl
        self.timeout = timeout

    @property
    def host(self):
        """Normalised platform host, always with a trailing slash."""
        return self.__host

    def post(self, uri, data, headers={}):
        url = self.__host + uri
        logger.debug("POST {}".format(url))
        resp = self.__session.post(url, data=data, headers=headers,
                                   verify=self.verify_ssl,
                                   timeout=self.timeout)
        return resp

    def get(self, uri, data):
        url = self.__host + uri
        logger.debug("GET {}".format(url))
        resp = self.__session.get(url, params=data, verify=self.verify_ssl,
                                  timeout=self.timeout)
        return resp

    def put(self, uri, data):
        url = self.__host + uri
        logger.debug("PUT {}".format(url))
        resp = self.__session.put(url, params=data, verify=self.verify_ssl,
                                  timeout=self.timeout)
        return resp

    def delete(self, uri, data):
        url = self.__host + uri
        logger.debug("DELETE {}".format(url))
        resp = self.__session.delete(url, params=data, verify=self.verify_ssl,
                                     timeout=self.timeout)
        return resp
