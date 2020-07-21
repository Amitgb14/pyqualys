# -*- coding: utf-8 -*-
import re
import pyqualys

obj = pyqualys.QualysAPI(username="admin",
                         password="admin",
                         host="https://host.com/")

service = obj.service("vulnerability")
service.FORMAT = "json"

# Add Asset Group and IP
new_asset_group = service.add_asset(title="myLinux", ips="10.10.10.1")
print("Add asset group: %s" % new_asset_group)

# Update Asset Group
update_asset_group = service.update_asset(asset_group_id=1234, title="myOS", ips="10.10.10.1")
print("Update asset group: %s" % update_asset_group)

# List of Asset Group
all_assets_group = service.list_assets()
print("List out all assets group: %s" % all_assets_group)

# Get Asset Group
get_asset_group = service.search_asset(ids=1234)
print("Get asset group: %s" % get_asset_group)

# Delete Asset Group
delete_asset_group = service.delete_asset(asset_id=1234)
print("Delete asset group: %s" % delete_asset_group)
