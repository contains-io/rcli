# -*- coding: utf-8 -*-
"""The primary module for the program."""

import sys


if sys.excepthook is sys.__excepthook__:
    import logging

    from . import log

    sys.excepthook = log.excepthook
    log.enable_logging(None)
