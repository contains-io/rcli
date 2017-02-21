# -*- coding: utf-8 -*-
"""A module for calling subcommands and handling type hint casting.

Functions:
    call: Calls a function and casts the docopt-style args to the appropriate
        names and types.
    get_callable: Retrieves a callable object from a subcommand.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from types import (  # noqa: F401 pylint: disable=unused-import
    FunctionType,
    MethodType,
    ModuleType
)
from typing import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Dict,
    Generator,
    Tuple,
    Union
)
import collections
import keyword
import logging
import re

import six

from . import config  # noqa: F401 pylint: disable=unused-import
from . import exceptions as exc
from .typing import (
    cast,
    get_signature,
    get_type_hints
)


_LOGGER = logging.getLogger(__name__)


def call(func, args):
    """Call the function with args normalized and cast to the correct types.

    Args:
        func: The function to call.
        args: The arguments parsed by docopt.

    Returns:
        The return value of func.
    """
    assert hasattr(func, '__call__'), 'Cannot call func: {}'.format(
        func.__name__)
    is_func = isinstance(func, FunctionType)
    raw_func = func if is_func else func.__class__.__call__
    hints = collections.defaultdict(lambda: Any, get_type_hints(raw_func))
    params, vararg, kwarg = get_signature(raw_func)
    params += [vararg, kwarg]
    keyword_args = {}
    positional_args = ()
    for k, nk, v in _normalize(args):
        if nk == vararg:
            hints[nk] = Tuple[hints[nk], ...]
        elif nk not in params and kwarg in hints:
            hints[nk] = hints[kwarg]
        try:
            value = cast(hints[nk], v)
        except exc.CastError as e:
            six.raise_from(exc.InvalidCliValueError(k, v), e)
        if nk == vararg:
            positional_args = value
        elif (nk in params or kwarg) and (
                nk not in keyword_args or keyword_args[nk] is None):
            keyword_args[nk] = value
    return func(*positional_args, **keyword_args)


def get_callable(subcommand):
    # type: (config.RcliEntryPoint) -> Union[FunctionType, MethodType]
    """Return a callable object from the subcommand.

    Args:
        subcommand: A object loaded from an entry point. May be a module,
            class, or function.

    Returns:
        The callable entry point for the subcommand. If the subcommand is a
        function, it will be returned unchanged. If the subcommand is a module
        or a class, an instance of the command class will be returned.

    Raises:
        AssertionError: Raised when a module entry point does not have a
            callable class named Command.
    """
    _LOGGER.debug(
        'Creating callable from subcommand "%s".', subcommand.__name__)
    if isinstance(subcommand, ModuleType):
        _LOGGER.debug('Subcommand is a module.')
        assert hasattr(subcommand, 'Command'), (
            'Module subcommand must have callable "Command" class definition.')
        callable_ = subcommand.Command  # type: ignore
    else:
        callable_ = subcommand
    if any(isinstance(callable_, t) for t in six.class_types):
        return callable_()
    return callable_


def _normalize(args):
    # type: (Dict[str, Any]) -> Generator[Tuple[str, str, Any], None, None]
    """Yield a 3-tuple containing the key, a normalized key, and the value.

    Args:
        args:  The arguments parsed by docopt.

    Yields:
        A 3-tuple that contains the docopt parameter name, the parameter name
        normalized to be a valid python identifier, and the value assigned to
        the parameter.
    """
    for k, v in six.iteritems(args):
        nk = re.sub(r'\W|^(?=\d)', '_', k).strip('_').lower()
        if keyword.iskeyword(nk):
            nk += '_'
        _LOGGER.debug('Normalized "%s" to "%s".', k, nk)
        yield k, nk, v
