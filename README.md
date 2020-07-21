# pyqualys


pyqualys is simple, easy to use, Qualys public API based services.

Currently this project is in working progress, but there are few features are available(Check TODO).

Install
-----------
```
$ pip install pyqualys
```


Example
-----------
* Add Asset Group
```
# -*- coding: utf-8 -*-
import pyqualys

qualys = pyqualys.QualysAPI(username="admin",
                         password="admin",
                         host="https://abc123.com/")

service = qualys.service("vulnerability")
# Get response in json format, default is xml
service.FORMAT = "json"
asset = service.add_asset(title="myLinux", ips="10.10.10.1")
print("Response", asset)
```
