# -*- coding: utf-8 -*-
import logging
from .utils.connect import QualysAPI

__version__ = "0.0.1"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s \
                    - %(name)s - \
                    %(levelname)s - \
                    %(message)s")
