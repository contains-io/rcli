# -*- coding: utf-8 -*-
# pragma pylint: disable=unused-import
"""Common backported utilities.

Functions:
    get_terminal_size: Get the size of the terminal.
"""

from __future__ import absolute_import


try:
    from shutil import get_terminal_size
except ImportError:
    from backports.shutil_get_terminal_size import (
        get_terminal_size,
    )  # noqa: F401
