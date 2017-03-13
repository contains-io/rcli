# -*- coding: utf-8 -*-
"""Common utility decorators.

Decorators:
    memoize: Cache the results of a function call.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from typing import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Callable,
    Dict,
    Tuple
)
import functools


def memoize(func):
    # type: (Callable) -> Callable
    """Cache the results of the function.

    Args:
        func: The function to memoize.

    Returns:
        A wrapper function that caches the results of the given function.
    """
    cache = {}  # type: Dict[Tuple[Any, ...], Any]

    @functools.wraps(func)
    def _inner(*key):
        # type: (*Any) -> Any
        """Check the cache for the key.

        Args:
            key: The arguments to the function used to cache the results.

        Returns:
            The results of the function.
        """
        if key not in cache:
            cache[key] = func(*key)
        return cache[key]

    return _inner
