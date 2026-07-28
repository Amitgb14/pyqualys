# -*- coding: utf-8 -*-
"""
Offline fixtures: canned Qualys response bodies and a fake response
object, so the test suite needs no data files, no network and no
credentials.
"""

SIMPLE_RETURN_LAUNCH = """<?xml version="1.0" encoding="UTF-8" ?>
<SIMPLE_RETURN>
  <RESPONSE>
    <DATETIME>2026-07-28T09:00:00Z</DATETIME>
    <TEXT>New vm scan launched</TEXT>
    <ITEM_LIST>
      <ITEM>
        <KEY>ID</KEY>
        <VALUE>4276458</VALUE>
      </ITEM>
      <ITEM>
        <KEY>REFERENCE</KEY>
        <VALUE>scan/1234567890.12345</VALUE>
      </ITEM>
    </ITEM_LIST>
  </RESPONSE>
</SIMPLE_RETURN>"""

SIMPLE_RETURN_OK = """<?xml version="1.0" encoding="UTF-8" ?>
<SIMPLE_RETURN>
  <RESPONSE>
    <DATETIME>2026-07-28T09:05:00Z</DATETIME>
    <TEXT>Scan cancelled</TEXT>
  </RESPONSE>
</SIMPLE_RETURN>"""

SIMPLE_RETURN_ERROR = """<?xml version="1.0" encoding="UTF-8" ?>
<SIMPLE_RETURN>
  <RESPONSE>
    <DATETIME>2026-07-28T09:05:00Z</DATETIME>
    <CODE>1960</CODE>
    <TEXT>This API cannot be run again until 1 currently running
    instance has finished.</TEXT>
  </RESPONSE>
</SIMPLE_RETURN>"""

SCAN_LIST_OUTPUT = """<?xml version="1.0" encoding="UTF-8" ?>
<SCAN_LIST_OUTPUT>
  <RESPONSE>
    <DATETIME>2026-07-28T09:10:00Z</DATETIME>
    <SCAN_LIST>
      <SCAN>
        <REF>scan/1234567890.12345</REF>
        <TYPE>On-Demand</TYPE>
        <TITLE>pyqualys nightly</TITLE>
        <USER_LOGIN>acme_ab</USER_LOGIN>
        <LAUNCH_DATETIME>2026-07-28T09:00:00Z</LAUNCH_DATETIME>
        <DURATION>00:10:00</DURATION>
        <PROCESSED>0</PROCESSED>
        <STATUS>
          <STATE>Running</STATE>
        </STATUS>
        <TARGET>10.0.0.1</TARGET>
      </SCAN>
      <SCAN>
        <REF>scan/1234567890.99999</REF>
        <TYPE>On-Demand</TYPE>
        <TITLE>pyqualys weekly</TITLE>
        <USER_LOGIN>acme_ab</USER_LOGIN>
        <LAUNCH_DATETIME>2026-07-21T09:00:00Z</LAUNCH_DATETIME>
        <DURATION>01:02:03</DURATION>
        <PROCESSED>1</PROCESSED>
        <STATUS>
          <STATE>Finished</STATE>
        </STATUS>
        <TARGET>10.0.0.0/24</TARGET>
      </SCAN>
    </SCAN_LIST>
  </RESPONSE>
</SCAN_LIST_OUTPUT>"""

SCAN_FETCH_CSV = '''"Scan Results"
"Launch Date","Active Hosts","Total Hosts"
"07/28/2026 09:00:00","2","2"

"IP","DNS","NetBIOS","QID","Title","Type","Severity"
"10.0.0.1","web01.acme.test","WEB01","38170","SSL Certificate","Vuln","3"
"10.0.0.2","db01.acme.test","DB01","90194","Weak Password","Vuln","5"
'''

SCAN_FETCH_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<SCAN>
  <HEADER>
    <KEY value="SCAN">scan/1234567890.12345</KEY>
  </HEADER>
  <IP value="10.0.0.1" name="web01.acme.test">
    <VULN number="38170" severity="3">
      <TITLE>SSL Certificate</TITLE>
    </VULN>
  </IP>
</SCAN>"""

SCAN_FETCH_JSON = '''[
  {"ip": "10.0.0.1", "dns": "web01.acme.test", "qid": "38170"},
  {"ip": "10.0.0.2", "dns": "db01.acme.test", "qid": "90194"}
]'''

HOST_LIST_OUTPUT = """<?xml version="1.0" encoding="UTF-8" ?>
<HOST_LIST_OUTPUT>
  <RESPONSE>
    <DATETIME>2026-07-28T09:20:00Z</DATETIME>
    <HOST_LIST>
      <HOST>
        <ID>145358</ID>
        <IP>10.0.0.1</IP>
        <TRACKING_METHOD>IP</TRACKING_METHOD>
        <DNS>web01.acme.test</DNS>
        <NETBIOS>WEB01</NETBIOS>
        <OS>Linux 5.x</OS>
        <LAST_VULN_SCAN_DATETIME>2026-07-27T09:00:00Z\
</LAST_VULN_SCAN_DATETIME>
      </HOST>
      <HOST>
        <ID>145359</ID>
        <IP>10.0.0.2</IP>
        <TRACKING_METHOD>IP</TRACKING_METHOD>
        <DNS>db01.acme.test</DNS>
        <NETBIOS>DB01</NETBIOS>
        <OS>Windows 2022</OS>
        <LAST_VULN_SCAN_DATETIME>2026-07-27T09:30:00Z\
</LAST_VULN_SCAN_DATETIME>
      </HOST>
    </HOST_LIST>
  </RESPONSE>
</HOST_LIST_OUTPUT>"""

HOST_LIST_OUTPUT_TRUNCATED = """<?xml version="1.0" encoding="UTF-8" ?>
<HOST_LIST_OUTPUT>
  <RESPONSE>
    <DATETIME>2026-07-28T09:20:00Z</DATETIME>
    <HOST_LIST>
      <HOST>
        <ID>145357</ID>
        <IP>10.0.0.9</IP>
        <TRACKING_METHOD>IP</TRACKING_METHOD>
        <DNS>app01.acme.test</DNS>
      </HOST>
    </HOST_LIST>
    <WARNING>
      <CODE>1980</CODE>
      <TEXT>Ouput truncated after 100 records.</TEXT>
      <URL><![CDATA[https://qualysapi.qualys.com/api/5.0/fo/asset/host/\
?action=list&truncation_limit=100&id_min=145359]]></URL>
    </WARNING>
  </RESPONSE>
</HOST_LIST_OUTPUT>"""

HOST_LIST_VM_DETECTION_OUTPUT = """<?xml version="1.0" encoding="UTF-8" ?>
<HOST_LIST_VM_DETECTION_OUTPUT>
  <RESPONSE>
    <DATETIME>2026-07-28T09:30:00Z</DATETIME>
    <HOST_LIST>
      <HOST>
        <ID>145358</ID>
        <IP>10.0.0.1</IP>
        <DNS>web01.acme.test</DNS>
        <DETECTION_LIST>
          <DETECTION>
            <QID>38170</QID>
            <TYPE>Confirmed</TYPE>
            <SEVERITY>3</SEVERITY>
            <STATUS>Active</STATUS>
            <LAST_FOUND_DATETIME>2026-07-27T09:00:00Z\
</LAST_FOUND_DATETIME>
          </DETECTION>
          <DETECTION>
            <QID>90194</QID>
            <TYPE>Confirmed</TYPE>
            <SEVERITY>5</SEVERITY>
            <STATUS>New</STATUS>
            <LAST_FOUND_DATETIME>2026-07-27T09:00:00Z\
</LAST_FOUND_DATETIME>
          </DETECTION>
        </DETECTION_LIST>
      </HOST>
    </HOST_LIST>
  </RESPONSE>
</HOST_LIST_VM_DETECTION_OUTPUT>"""

HOST_LIST_VM_DETECTION_OUTPUT_TRUNCATED = """<?xml version="1.0"?>
<HOST_LIST_VM_DETECTION_OUTPUT>
  <RESPONSE>
    <DATETIME>2026-07-28T09:30:00Z</DATETIME>
    <HOST_LIST>
      <HOST>
        <ID>145357</ID>
        <IP>10.0.0.9</IP>
        <DETECTION_LIST>
          <DETECTION>
            <QID>11111</QID>
            <SEVERITY>2</SEVERITY>
            <STATUS>Active</STATUS>
          </DETECTION>
        </DETECTION_LIST>
      </HOST>
    </HOST_LIST>
    <WARNING>
      <CODE>1980</CODE>
      <TEXT>Ouput truncated after 25 records.</TEXT>
      <URL><![CDATA[https://qualysapi.qualys.com/api/5.0/fo/asset/host/\
vm/detection/?action=list&truncation_limit=25&id_min=145359]]></URL>
    </WARNING>
  </RESPONSE>
</HOST_LIST_VM_DETECTION_OUTPUT>"""

ASSET_GROUP_LIST_OUTPUT = """<?xml version="1.0" encoding="UTF-8" ?>
<ASSET_GROUP_LIST_OUTPUT>
  <RESPONSE>
    <DATETIME>2026-07-28T09:40:00Z</DATETIME>
    <ASSET_GROUP_LIST>
      <ASSET_GROUP>
        <ID>1234</ID>
        <TITLE>myLinux</TITLE>
      </ASSET_GROUP>
    </ASSET_GROUP_LIST>
  </RESPONSE>
</ASSET_GROUP_LIST_OUTPUT>"""

HTML_ERROR_PAGE = """<html>
<head><title>502 Bad Gateway</title></head>
<body><h1>502 Bad Gateway</h1><p>nginx</p>
</body>
"""

JSON_BODY = '{"responseCode": "SUCCESS", "count": 2}'

SERVICE_RESPONSE_XML = """<?xml version="1.0" encoding="UTF-8" ?>
<ServiceResponse>
  <responseCode>SUCCESS</responseCode>
  <count>1</count>
</ServiceResponse>"""


class FakeResponse(object):
    """Minimal stand-in for ``requests.Response``."""

    def __init__(self, text, status_code=200, headers=None):
        self.text = text
        self.status_code = status_code
        self.headers = headers if headers is not None else {}

    def json(self):
        import json
        return json.loads(self.text)


class Recorder(object):
    """
    Callable replacement for ``APISession.post``/``get``.

    Records every ``(uri, data)`` pair and replays canned responses.
    """

    def __init__(self, responses):
        if not isinstance(responses, (list, tuple)):
            responses = [responses]
        self.responses = list(responses)
        self.calls = []

    def __call__(self, uri, data=None, headers=None, **kwargs):
        self.calls.append((uri, dict(data or {})))
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]

    @property
    def last_uri(self):
        return self.calls[-1][0]

    @property
    def last_data(self):
        return self.calls[-1][1]
