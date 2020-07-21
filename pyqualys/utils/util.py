# -*- coding: utf-8 -*-
import lxml
import logging
from collections import defaultdict
from xml.etree import cElementTree as ET

logger = logging.getLogger(__name__)


def etree_to_dict(tree):
    new_dict = {tree.tag: {} if tree.attrib else None}
    children = list(tree)
    if children:
        dd = defaultdict(list)
        for dc in map(etree_to_dict, children):
            for k, v in dc.items():
                dd[k].append(v)
        new_dict = {tree.tag: {k:v[0] if len(v) == 1 else v for k, v in dd.items()}}
    if tree.attrib:
        new_dict[tree.tag].update(('@' + k, v) for k, v in tree.attrib.items())
    if tree.text:
        text = tree.text.strip()
        if children or tree.attrib:
            if text:
                new_dict[tree.tag]['#text'] = text
        else:
            new_dict[tree.tag] = text
    return new_dict


def decode_xml(xml_str):
    encoded = ET.XML(xml_str)
    try:
        encoded_obj = etree_to_dict(encoded)
        if 'ServiceResponse' in encoded_obj:
            encoded_obj = encoded_obj['ServiceResponse']
        return {"type": "json", "data": encoded_obj}
    except Exception as e:
        logger.error(e)
        return {"type": "xml", "data": xml_str}
