# -*- coding: utf-8 -*-
import logging
from requests import Request
from requests import Session
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)
HEADERS = {"X-Requested-With": "pyqualys/python-3x"}


class APISession(object):

    def __init__(self, username, password, host, max_retries=3):
        self.__host = host
        self.__session = Session()
        self.__session.auth = (username, password)
        self.__session.headers.update(HEADERS)
        self.__session.mount('http://', HTTPAdapter(max_retries=max_retries))
        self.__session.mount('https://', HTTPAdapter(max_retries=max_retries))

        self.verify_ssl = False

    def post(self, uri, data, headers={}):
        url = self.__host + uri
        logger.debug("{}-{}".format(url, data))
        resp = self.__session.post(url, data=data,
                                   headers=headers, verify=self.verify_ssl)
        return resp

    def get(self, uri, data):
        url = self.__host + uri
        logger.debug("{}-{}".format(url, data))
        resp = self.__session.get(url, data=data, verify=self.verify_ssl)
        return resp

    def put(self, uri, data):
        url = self.__host + uri
        logger.debug("{}-{}".format(url, data))
        resp = self.__session.put(url, data=data, verify=self.verify_ssl)
        return resp

    def delete(self, uri, data):
        url = self.__host + uri
        logger.debug("{}-{}".format(url, data))
        resp = self.__session.delete(url, data=data, verify=self.verify_ssl)
        return resp
