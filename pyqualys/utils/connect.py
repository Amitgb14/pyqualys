# -*- coding: utf-8 -*-
import logging
import importlib
from .session import APISession

logger = logging.getLogger(__name__)
SERVICES = ["vulnerability", "assetview"]


class QualysAPI(object):

    def __init__(self, **kwargs):
        username = kwargs.get("username")
        password = kwargs.get("password")
        host = kwargs.get("host")
        if not username or not password:
            logger.error("Error: username or password missing.")
            return
        elif not host:
            logger.error("Error: host parameter is missing.")
            return
        self.__session = APISession(**kwargs)

    def list_services(self):
        # return "Services:\n\t"+"\n\t".join(SERVICES)
        return SERVICES

    def service(self, service_name):
        if service_name not in SERVICES:
            logger.error("{} Service is not available.".format(service_name))
            return
        s = "pyqualys.services.{0}".format(service_name)
        Service = getattr(importlib.import_module(s),
                          service_name.title()+"Service")
        return Service(self.__session)
