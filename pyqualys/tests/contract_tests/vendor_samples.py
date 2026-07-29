# -*- coding: utf-8 -*-
"""
Response bodies and HTTP headers transcribed from the vendor's own
documentation.

Source: *Qualys API (VM and PA) User Guide*, version 10.39.1, dated
10 July 2026, published at
https://cdn2.qualys.com/docs/qualys-api-vmpc-user-guide.pdf

Every constant below carries the guide page it was copied from. These
differ from :mod:`pyqualys.tests.fixtures` in one way that matters: the
fixtures there were written by hand to exercise the parsers, so they
agree with the parsers by construction. These were copied out of the
vendor documentation without reference to the code, so when a parser
disagrees with one of them, the parser is what is wrong.

Two deliberate deviations from a byte-for-byte copy:

* The PDF hard-wraps long lines, which splits timestamps such as
  ``2023-10-11T07:11:13Z`` across two lines. Those wraps are an artefact
  of the page layout and have been rejoined.
* ``<qualys_base_url>`` placeholders are replaced with a concrete host.

Everything else is preserved as printed, including the whitespace around
CDATA sections and the empty ``<ASSET_GROUP_LIST />`` element, because
that incidental formatting is exactly what a parser can trip over.
"""

# ---------------------------------------------------------------------
# Scans
# ---------------------------------------------------------------------

# Guide page 55, "Launch VM Scan" - XML output.
LAUNCH_SIMPLE_RETURN = """<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE SIMPLE_RETURN SYSTEM
"https://qualysapi.qualys.com/api/2.0/simple_return.dtd">
<SIMPLE_RETURN>
  <RESPONSE>
    <DATETIME>2018-02-25T21:32:40Z</DATETIME>
    <TEXT>New vm scan launched</TEXT>
    <ITEM_LIST>
      <ITEM>
        <KEY>ID</KEY>
        <VALUE>136992</VALUE>
      </ITEM>
      <ITEM>
        <KEY>REFERENCE</KEY>
        <VALUE>scan/1358285558.36992</VALUE>
      </ITEM>
    </ITEM_LIST>
  </RESPONSE>
</SIMPLE_RETURN>"""

LAUNCH_SCAN_REF = "scan/1358285558.36992"

# Guide pages 44-45, "List Scans" - XML response for
# /api/3.0/fo/scan/?action=list. The TARGET of the real sample is a
# 41-entry CDATA list of Azure resource UUIDs; two are kept here, which
# is enough to prove CDATA and comma joining survive the parser.
SCAN_LIST_OUTPUT = """<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE SCAN_LIST_OUTPUT SYSTEM
"https://qualysapi.qualys.com/api/3.0/fo/scan/scan_list_output.dtd">
<SCAN_LIST_OUTPUT>
    <RESPONSE>
        <DATETIME>2024-12-09T09:11:17Z</DATETIME>
        <SCAN_LIST>
            <SCAN>
                <REF>scan/1735543972.16308</REF>
                <TYPE>Scheduled</TYPE>
                <TITLE>
                    <![CDATA[Azure Scan Internal Test]]>
                </TITLE>
                <USER_LOGIN>vmsp_ag1</USER_LOGIN>
                <LAUNCH_DATETIME>2024-12-30T07:32:52Z</LAUNCH_DATETIME>
                <DURATION>00:00:27</DURATION>
                <PROCESSING_PRIORITY>2 - Ultimate</PROCESSING_PRIORITY>
                <PROCESSED>1</PROCESSED>
                <STATUS>
                    <STATE>Finished</STATE>
                    <SUB_STATE>No_Host</SUB_STATE>
                </STATUS>
                <TARGET>
                    <![CDATA[65188eb1-02b7-405e-861c-fb44c98a20d7,\
cc681b26-8899-4ca8-bedd-b187bdbb8bdb]]>
                </TARGET>
            </SCAN>
        </SCAN_LIST>
    </RESPONSE>
</SCAN_LIST_OUTPUT>"""

# ---------------------------------------------------------------------
# Assets - Host List
# ---------------------------------------------------------------------

# Guide pages 1010-1011, "Sample - Record Limit Exceeded Warning".
#
# Three details are load bearing and none of them appear in the
# hand-written fixtures:
#   * the <URL> body is padded with newlines around the CDATA;
#   * the truncation URL carries parameters the original request never
#     sent (details, cloud_agent_activationkey), which the next request
#     has to merge rather than discard;
#   * the host in the sample is EC2 tracked, so DNS and OS arrive as
#     CDATA rather than as plain text.
HOST_LIST_OUTPUT_TRUNCATED = """<?xml version="1.0" encoding="UTF-8" ?>
<HOST_LIST_OUTPUT>
  <RESPONSE>
    <DATETIME>2017-04-15T09:50:46Z</DATETIME>
    <HOST_LIST>
       <HOST>
       <ID>135151</ID>
       <IP>11.11.1.111</IP>
       <TRACKING_METHOD>EC2</TRACKING_METHOD>
       <DNS><![CDATA[i-0bb87c3281243cdfd]]></DNS>
       <EC2_INSTANCE_ID><![CDATA[i-0bb87c3281243cdfd]]></EC2_INSTANCE_ID>
       <OS><![CDATA[Amazon Linux 2016.09]]></OS>
       <LAST_VULN_SCAN_DATETIME>2017-03-21T13:39:38Z\
</LAST_VULN_SCAN_DATETIME>
       <LAST_VM_SCANNED_DATE>2017-03-21T13:39:38Z</LAST_VM_SCANNED_DATE>
       <LAST_VM_SCANNED_DURATION>229</LAST_VM_SCANNED_DURATION>
     </HOST>
    </HOST_LIST>
    <WARNING>
        <CODE>1980</CODE>
        <TEXT>100 record limit exceeded. Use URL to get next batch of
results.</TEXT>
        <URL>
            <![CDATA[https://qualysapi.p01.eng.sjc01.qualys.com\
/api/4.0/fo/asset/host/?action=list&details=None&truncation_limit=100\
&cloud_agent_activationkey=0&id_min=145359]]>
        </URL>
    </WARNING>
  </RESPONSE>
</HOST_LIST_OUTPUT>"""

# The id_min the WARNING above hands back for the following page.
HOST_LIST_NEXT_ID_MIN = "145359"

# The same body without the WARNING element - what the guide describes as
# the final page, once fewer records remain than the truncation limit.
# Derived from the sample above rather than copied from a separate page,
# because the guide prints the untruncated shape everywhere else in the
# chapter and only annotates the truncated one.
HOST_LIST_OUTPUT_FINAL_PAGE = HOST_LIST_OUTPUT_TRUNCATED.replace(
    HOST_LIST_OUTPUT_TRUNCATED[
        HOST_LIST_OUTPUT_TRUNCATED.index("    <WARNING>"):
        HOST_LIST_OUTPUT_TRUNCATED.index("    </WARNING>") + len(
            "    </WARNING>\n")],
    "")

# Guide page 1011, "Sample - Display the hosts that have completed the
# compliance scan before the given date".
#
# The guide prints this response with every element name in lower case,
# unlike every other Host List sample in the same chapter. Whether the
# platform genuinely emits this or the guide is misprinted is not
# something documentation can settle - see the test that consumes this
# constant.
HOST_LIST_OUTPUT_LOWERCASE = """<?xml version="1.0" encoding="utf-8"?>
<host_list_output>
  <response>
    <datetime>2024-09-16T10:58:10Z</datetime>
    <host_list>
      <host>
        <id>2584392</id>
        <ip>11.11.11.111</ip>
        <tracking_method>Cloud Agent</tracking_method>
        <dns>compaix6lpr01</dns>
        <dns_data>
          <hostname>compaix6lpr01</hostname>
          <domain/>
          <fqdn/>
        </dns_data>
        <os>AIX 6.1.0.0</os>
      </host>
    </host_list>
  </response>
</host_list_output>"""

# ---------------------------------------------------------------------
# Assets - Host List Detection
# ---------------------------------------------------------------------

# Guide page 1151, host detection output for
# ?action=list&ips=10.10.40.10&truncation_limit=4.
#
# Note <ASSET_GROUP_LIST /> - an empty element among populated siblings -
# and the CDATA values sitting on their own lines, indented.
HOST_LIST_VM_DETECTION_OUTPUT = """<?xml version="1.0" encoding="UTF-8" ?>
<HOST_LIST_VM_DETECTION_OUTPUT>
    <RESPONSE>
      <DATETIME>2024-03-28T09:03:45Z</DATETIME>
      <HOST_LIST>
        <HOST>
          <ID>4203254</ID>
          <IP>11.11.11.11</IP>
          <TRACKING_METHOD>IP</TRACKING_METHOD>
          <ASSET_GROUP_LIST />
          <NETWORK_ID>2458227</NETWORK_ID>
          <NETWORK_NAME>network1</NETWORK_NAME>
          <OS>
            <![CDATA[Windows XP]]>
          </OS>
          <DNS>
            <![CDATA[w2kserver-tmp3.vuln.example.com]]>
          </DNS>
          <DNS_DATA>
            <HOSTNAME>
              <![CDATA[w2kserver-tmp3]]>
            </HOSTNAME>
            <DOMAIN>
              <![CDATA[vuln.example.com]]>
            </DOMAIN>
            <FQDN>
              <![CDATA[w2kserver-tmp3.vuln.example.com]]>
            </FQDN>
          </DNS_DATA>
          <LAST_SCAN_DATETIME>2023-10-11T07:18:36Z</LAST_SCAN_DATETIME>
          <LAST_VM_SCANNED_DATE>2023-10-11T07:11:13Z\
</LAST_VM_SCANNED_DATE>
          <LAST_VM_SCANNED_DURATION>149</LAST_VM_SCANNED_DURATION>
          <DETECTION_LIST>
            <DETECTION>
              <UNIQUE_VULN_ID>61198372</UNIQUE_VULN_ID>
              <QID>11</QID>
              <TYPE>Confirmed</TYPE>
              <SEVERITY>2</SEVERITY>
              <SSL>0</SSL>
              <RESULTS>
                <![CDATA[NameProgramVersionProtocolPort
portmap/rpcbind1000002-4tcp111
portmap/rpcbind1000002-4udp895]]>
              </RESULTS>
              <STATUS>New</STATUS>
              <FIRST_FOUND_DATETIME>2023-10-11T07:11:13Z\
</FIRST_FOUND_DATETIME>
              <LAST_FOUND_DATETIME>2023-10-11T07:11:13Z\
</LAST_FOUND_DATETIME>
            </DETECTION>
          </DETECTION_LIST>
        </HOST>
      </HOST_LIST>
    </RESPONSE>
</HOST_LIST_VM_DETECTION_OUTPUT>"""

# Guide page 1153, "Sample - Host Detection XML Output, with truncation".
HOST_LIST_VM_DETECTION_TRUNCATED = """<?xml version="1.0" encoding="UTF-8" ?>
<HOST_LIST_VM_DETECTION_OUTPUT>
  <RESPONSE>
    <DATETIME>2024-03-28T09:03:45Z</DATETIME>
    <HOST_LIST>
      <HOST>
        <ID>4203254</ID>
        <IP>11.11.11.11</IP>
        <DETECTION_LIST>
          <DETECTION>
            <QID>11</QID>
            <SEVERITY>2</SEVERITY>
            <STATUS>New</STATUS>
          </DETECTION>
        </DETECTION_LIST>
      </HOST>
    </HOST_LIST>
    <WARNING>
      <CODE>1980</CODE>
      <TEXT>100 record limit exceeded. Use URL to get next batch of
results.</TEXT>
      <URL><![CDATA[https://qualysapi.qualys.com\
/api/5.0/fo/asset/host/vm/detection/?action=list&truncation_limit=100\
&id_min=5641289]]></URL>
    </WARNING>
  </RESPONSE>
</HOST_LIST_VM_DETECTION_OUTPUT>"""

DETECTION_NEXT_ID_MIN = "5641289"

# ---------------------------------------------------------------------
# Rate limiting and concurrency
# ---------------------------------------------------------------------
#
# Guide pages 15-17. Qualys blocks with HTTP 409 Conflict, not 429, and
# the guide is explicit that the two blocking conditions do not carry the
# same headers: "In case where the concurrency limit has been reached, no
# information about rate limits will appear in the HTTP headers."
#
# So a client that reads X-RateLimit-ToWait-Sec to decide how long to
# sleep gets nothing to read on the concurrency path, and the guide says
# the concurrency error takes precedence when both apply.

# Page 16, Sample 2: rate limit exceeded.
RATE_LIMIT_409_HEADERS = {
    "Date": "Fri, 22 Apr 2018 00:13:18 GMT",
    "Server": "qweb",
    "X-RateLimit-Limit": "15",
    "X-RateLimit-Window-Sec": "360",
    "X-Concurrency-Limit-Limit": "3",
    "X-Concurrency-Limit-Running": "1",
    "X-RateLimit-ToWait-Sec": "181",
    "X-RateLimit-Remaining": "0",
    "Content-Type": "application/xml",
}

# Page 17, Sample 3: concurrency limit exceeded. No X-RateLimit-ToWait-Sec.
CONCURRENCY_409_HEADERS = {
    "Date": "Fri, 22 Apr 2018 00:13:18 GMT",
    "Server": "qweb",
    "Expires": "Mon, 24 Oct 1970 07:30:00 GMT",
    "Cache-Control": "post-check=0,pre-check=0",
    "Pragma": "no-cache",
    "X-RateLimit-Limit": "15",
    "X-RateLimit-Window-Sec": "360",
    "X-Concurrency-Limit-Limit": "3",
    "X-Concurrency-Limit-Running": "3",
    "Content-Type": "application/xml",
}

# Page 16, Sample 1: a normal, unblocked call.
OK_200_HEADERS = {
    "Date": "Fri, 22 Apr 2018 00:13:18 GMT",
    "Server": "qweb",
    "X-RateLimit-Limit": "15",
    "X-RateLimit-Window-Sec": "360",
    "X-Concurrency-Limit-Limit": "3",
    "X-Concurrency-Limit-Running": "1",
    "X-RateLimit-ToWait-Sec": "0",
    "X-RateLimit-Remaining": "4",
    "Content-Type": "application/xml",
}

# ---------------------------------------------------------------------
# Documented endpoint versions
# ---------------------------------------------------------------------
#
# Copied from the "API Version History" tables. EOS/EOL columns are
# included because they are the reason the newer prefixes are the right
# default: as of this guide the 2.0/3.0/4.0 variants below are already
# past End of Support.
#
#   page 48    /api/3.0/fo/scan/?action=list                 Active
#              /api/2.0/fo/scan/?action=list                 EOS Dec 2025
#   page 56    /api/2.0/fo/scan/?action={action}             only version
#              (the "Manage VM Scans" section, which the guide states
#               covers cancel, pause, resume, delete and fetch)
#   page 51    /api/2.0/fo/scan/?action=launch               only version
#   page 1021  /api/5.0/fo/asset/host/?action=list           Active
#              /api/4.0, /api/3.0, /api/2.0                  EOS Dec 2025
#   page 1172  /api/5.0/fo/asset/host/vm/detection/?action=list  Active
#              /api/4.0, /api/3.0, /api/2.0                  EOS Dec 2025
DOCUMENTED_URIS = {
    "scan_launch": "api/2.0/fo/scan/",
    "scan_manage": "api/2.0/fo/scan/",
    "scan_fetch": "api/2.0/fo/scan/",
    "scan_list": "api/3.0/fo/scan/",
    "host_list": "api/5.0/fo/asset/host/",
    "host_detection_list": "api/5.0/fo/asset/host/vm/detection/",
}
