# -*- coding: utf-8 -*-
import logging
import importlib
from .session import APISession
from ..errors import ParameterError

logger = logging.getLogger(__name__)
SERVICES = ["vulnerability", "assetview"]


class QualysAPI(object):

    def __init__(self, **kwargs):
        """
        Entry point of the library.

        :param username: Qualys account user name. (required)
        :param password: Qualys account password. (required)
        :param host: Qualys platform URL, e.g.
                     ``https://qualysapi.qualys.com/``. (required)
        :param verify_ssl: verify the TLS certificate, default True.
        :param timeout: per request timeout in seconds, default 300.
        :param max_retries: urllib3 connection retries, default 3.

        :raises pyqualys.errors.ParameterError: when a credential or the
                host is missing.
        """
        username = kwargs.get("username")
        password = kwargs.get("password")
        host = kwargs.get("host")
        if not username or not password:
            raise ParameterError("username and password are required.")
        elif not host:
            raise ParameterError("host parameter is required.")
        self.__session = APISession(**kwargs)

    @property
    def session(self):
        """The underlying :class:`~pyqualys.utils.session.APISession`."""
        return self.__session

    def list_services(self):
        return SERVICES

    def service(self, service_name):
        """
        Return the service handler for ``service_name``.

        :raises pyqualys.errors.ParameterError: on an unknown service.
        """
        if service_name not in SERVICES:
            raise ParameterError(
                "{0} service is not available, choose one of {1}.".format(
                    service_name, ", ".join(SERVICES)))
        s = "pyqualys.services.{0}".format(service_name)
        Service = getattr(importlib.import_module(s),
                          service_name.title()+"Service")
        return Service(self.__session)
