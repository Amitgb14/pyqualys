# -*- coding: utf-8 -*-
import logging
from .utils.connect import QualysAPI

__version__ = "0.1.1"

# basicConfig defaults to stderr, so this is safe for the stdio MCP
# transport. pyqualys.mcp.server still calls basicConfig first, because
# basicConfig is a no-op once the root logger owns a handler.
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s \
                    - %(name)s - \
                    %(levelname)s - \
                    %(message)s")
