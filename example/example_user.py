# -*- coding: utf-8 -*-
import re
import pyqualys

obj = pyqualys.QualysAPI(username="admin",
                         password="admin",
                         host="https://host.com/")

service = obj.service("vulnerability")
service.FORMAT = "json"

# Add new business unit user
info = {}
info["business_unit"] = "my Business"

info["first_name"] = "Amit"
info["last_name"] = "Ghadge"
info["phone"] = "1234567890"
info["email"] = "hello@qualys.com"

user = service.add_user(data=info, acceptEULA=True)