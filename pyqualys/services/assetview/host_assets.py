# -*- coding: utf-8 -*-
import logging

from ...utils import util
logger = logging.getLogger(__name__)


class HostAsset(object):
    def __init__(self, session, api_version, urls_map):
        self.session = session
        self.api_version = api_version
        self.tag_urls_map = urls_map.tag
        self.headers = {"Content-Type": "application/xml"}
        super(HostAsset, self).__init__()

    def __get_obj(self, parameter="", uri="", method="POST"):
        uri = self.tag_urls_map + self.api_version + uri
        if method == "GET":
            resp = self.session.get(uri, data="")
        else:
            resp = self.session.post(uri, parameter, self.headers)
        response = util.decode_xml(resp.text) if self.FORMAT == "json" \
                                                                else resp.text
        return response

    def create_host_asset(self, parameter):
        uri = "create/am/hostasset"
        return self.__get_obj(parameter=parameter, uri=uri)

    def get_host_asset(self, asset_id):
        uri = "get/am/hostasset/%d" % int(asset_id)
        return self.__get_obj(uri=uri, method="GET")

    def delete_host_asset(self, asset_id):
        uri = "delete/am/hostasset/%d" % int(asset_id)
        return self.__get_obj(uri=uri)
