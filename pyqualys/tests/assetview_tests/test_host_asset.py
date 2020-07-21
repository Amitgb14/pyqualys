# -*- coding: utf-8 -*-
import os
import time
import unittest
import pyqualys
from pyqualys.utils import util


class TestHostAsset(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__instance = pyqualys.QualysAPI(username="admin",
                                            password="admin",
                                            host="https://abc123.com/")
        cls.__service = cls.__instance.service("assetview")
        cls.__service.FORMAT = "json"
        TestHostAsset.host_asset_id = None

    def test_01_add_host_asset(self):
        test_script_loc = os.path.dirname(os.path.realpath(__file__))
        with open(test_script_loc + "/create_host_asset.xml") as fread:
            content = fread.read()
        expected_output = 'SUCCESS'
        response = self.__service.create_host_asset(content)
        self.assertEqual(response['data']['responseCode'], expected_output)
        TestHostAsset.host_asset_id = int(response['data']['data']['HostAsset']['id'])

    def test_02_get_host_asset(self):
        expected_output = 'SUCCESS'
        response = self.__service.get_host_asset(asset_id=TestHostAsset.host_asset_id)
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_03_delete_host_asset(self):
        expected_output = 'SUCCESS'
        response = self.__service.delete_host_asset(asset_id=TestHostAsset.host_asset_id)
        self.assertEqual(response['data']['responseCode'], expected_output)


