# -*- coding: utf-8 -*-
import logging
logger = logging.getLogger(__name__)


def ReportFormat(func, format=None):
    def inner(*args, **kwargs):
        output = func(*args, **kwargs)
    return inner
