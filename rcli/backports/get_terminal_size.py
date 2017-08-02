# -*- coding: utf-8 -*-
# pragma pylint: disable=unused-import
"""An automatic command that handles subcommand dispatch.

Functions:
    main: The console script entry point set by autodetected CLI scripts.
"""

from __future__ import absolute_import


try:
    from shutil import get_terminal_size
except ImportError:
    from backports.shutil_get_terminal_size import (  # noqa: F401
        get_terminal_size
    )
