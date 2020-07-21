# -*- coding: utf-8 -*-
import os
import time
import unittest
import pyqualys
from pyqualys.utils import util


class TestTag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.__instance = pyqualys.QualysAPI(username="admin",
                                            password="admin",
                                            host="https://abc123.com/")
        cls.__service = cls.__instance.service("assetview")
        cls.__service.FORMAT = "json"
        TestTag.tag_id = None

    def test_01_add_tag(self):
        parameter = """<?xml version="1.0" encoding="UTF-8" ?>
                <ServiceRequest>
                    <data>
                        <Tag>
                            <name>API Test Tag</name>
                            <ruleType>GROOVY</ruleType>
                            <ruleText>if (!asset.isHostAsset()) return false;
        return asset.getOperatingSystem().contains("Windows XP Service Pack")
                            </ruleText>
                            <color>#008000</color>
                            <children>
                                <set>
                                    <TagSimple>
                                        <name>One</name>
                                    </TagSimple>
                                </set>
                            </children>
                        </Tag>
                    </data>
                </ServiceRequest>"""
        expected_output = 'SUCCESS'
        response = self.__service.create_tag(parameter)
        TestTag.tag_id = response['data']['data']['Tag']['id']
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_02_evaluate_tag(self):
        parameter = """<?xml version="1.0" encoding="UTF-8" ?>
                <ServiceRequest>
                    <data>
                        <Tag>
                            <name>API Test Tag</name>
                            <ruleType>GROOVY</ruleType>
                        </Tag>
                    </data>
                </ServiceRequest>"""
        expected_output = 'SUCCESS'
        response = self.__service.evaluate_tag(parameter)
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_03_update_tag(self):
        parameter = """<?xml version="1.0" encoding="UTF-8" ?>
                <ServiceRequest>
                    <data>
                        <Tag>
                            <name>API Test Tag (Update)</name>
                            <ruleType>GROOVY</ruleType>
                            <color>#FFFFFF</color>
                        </Tag>
                    </data>
                </ServiceRequest>"""
        expected_output = 'SUCCESS'
        response = self.__service.update_tag(parameter, TestTag.tag_id)
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_04_search_tag(self):
        parameter = """<?xml version="1.0" encoding="UTF-8" ?>
                <ServiceRequest>
                    <filters>
                        <Criteria field="ruleType" operator="EQUALS">
                            GROOVY</Criteria>
                    </filters>
                </ServiceRequest>"""
        expected_output = 'SUCCESS'
        response = self.__service.search_tag(parameter)
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_05_count_child_tag(self):
        parameter = """<?xml version="1.0" encoding="UTF-8" ?>
                <ServiceRequest>
                    <filters>
                        <Criteria field="parent" operator="EQUALS">
                            {tag_id}
                        </Criteria>
                    </filters>
                </ServiceRequest>""".format(tag_id=TestTag.tag_id)
        expected_output = 'SUCCESS'
        response = self.__service.count_child_tag(parameter)
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_06_get_assets(self):
        parameter = """<?xml version="1.0" encoding="UTF-8" ?>
                <ServiceRequest>
                    <filters>
                        <Criteria field="tagId" operator="EQUALS">
                            {tag_id}
                        </Criteria>
                    </filters>
                </ServiceRequest>""".format(tag_id="79664244")
        expected_output = 'SUCCESS'
        response = self.__service.get_assets(parameter)
        self.assertEqual(response['data']['responseCode'], expected_output)

    def test_07_delete_tag(self):
        expected_output = 'SUCCESS'
        response = self.__service.delete_tag(TestTag.tag_id)
        self.assertEqual(response['data']['responseCode'], expected_output)
