# -*- coding: utf-8 -*-
import re
import pyqualys

obj = pyqualys.QualysAPI(username="admin",
                         password="admin",
                         host="https://host.com/")

service = obj.service("vulnerability")

# Lit out the all reports
data = {'action': 'list'}
report_list = service.report.list_report(**data)
print(report_list)


# Launch the scan report
data = {
        'report_title': 'pyqualys report',
        'action': 'launch',
        'report_type': 'Scan',
        'template_id': '134271',
        'output_format': 'pdf',
}
scan_report = service.report.scan_report(**data)
print(scan_report)

# Get report the scanner
report = service.scanner.get_scan_report(echo_request=1,
                               scan_ref="scan/1525944287.01369",
                               output_format="json")
print(report)
