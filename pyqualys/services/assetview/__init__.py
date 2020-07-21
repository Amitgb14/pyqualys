# -*- coding: utf-8 -*-
from .tag import Tags
from .host_assets import HostAsset
from .api_v2 import URLs


class AssetviewService(Tags, HostAsset):

    def __init__(self, session, api="2.0/", urls=URLs):
        self.FORMAT = "xml"
        super(AssetviewService, self).__init__(session=session,
                                               api_version=api,
                                               urls_map=urls)

    def __call__(self):
        return "Hello, AssetView"
