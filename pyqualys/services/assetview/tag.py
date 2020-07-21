# -*- coding: utf-8 -*-
import logging

from ...utils import util
logger = logging.getLogger(__name__)


class Tags(object):
    def __init__(self, session, api_version, urls_map):
        self.session = session
        self.api_version = api_version
        self.tag_urls_map = urls_map.tag
        self.headers = {"Content-Type": "application/xml"}
        super(Tags, self).__init__(session=session,
                                   api_version=api_version,
                                   urls_map=urls_map)

    def __get_obj(self, parameter="", uri=""):
        uri = self.tag_urls_map + self.api_version + uri
        resp = self.session.post(uri, parameter, self.headers)
        response = util.decode_xml(resp.text) if self.FORMAT == "json" \
                                                                else resp.text
        return response

    def create_tag(self, parameter):
        """
        Create the tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "create/am/tag"
        return self.__get_obj(parameter=parameter, uri=uri)

    def evaluate_tag(self, parameter):
        """
        Evaluate the tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "evaluate/am/tag"
        return self.__get_obj(parameter=parameter, uri=uri)

    def update_tag(self, parameter, tag_id):
        """
        Update the tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "update/am/tag/%s" % (tag_id)
        return self.__get_obj(parameter=parameter, uri=uri)

    def search_tag(self, parameter):
        """
        Search the tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "search/am/tag"
        return self.__get_obj(parameter=parameter, uri=uri)

    def count_child_tag(self, parameter):
        """
        Count the child tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "count/am/tag"
        return self.__get_obj(parameter=parameter, uri=uri)

    def get_assets(self, parameter):
        """
        Get the attached assets.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "search/am/asset"
        return self.__get_obj(parameter=parameter, uri=uri)

    def search_host_asset(self, parameter):
        """
        Get the attached assets.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "search/am/hostasset"
        return self.__get_obj(parameter=parameter, uri=uri)

    def tag_asset_count(self, parameter):
        """
        Count the asset of perticular tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "count/am/asset"
        return self.__get_obj(parameter=parameter, uri=uri)

    def delete_tag(self, tag_id):
        """
        Delete the tag.

        :param parameter: contain the tag details.
        :type parameter: dict
        """

        uri = "delete/am/tag/%s" % (tag_id)
        return self.__get_obj(uri=uri)
