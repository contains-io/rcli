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
import collections
import inspect
import keyword
import logging
import re

from typingplus import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Dict,
    Generator,
    Tuple,
    Union,
    cast,
    get_type_hints
)
import six

from . import config  # noqa: F401 pylint: disable=unused-import
from . import exceptions as exc


_LOGGER = logging.getLogger(__name__)

_getspec = getattr(inspect, 'get{}argspec'.format('full' if six.PY3 else ''))
_ArgSpec = collections.namedtuple('_ArgSpec', ('args', 'varargs', 'varkw'))


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
    raw_func = (
        func if isinstance(func, FunctionType) else func.__class__.__call__)
    hints = collections.defaultdict(lambda: Any, get_type_hints(raw_func))
    argspec = _getargspec(raw_func)
    named_args = {}
    varargs = ()
    for k, nk, v in _normalize(args):
        if nk == argspec.varargs:
            hints[nk] = Tuple[hints[nk], ...]
        elif nk not in argspec.args and argspec.varkw in hints:
            hints[nk] = hints[argspec.varkw]
        try:
            value = cast(hints[nk], v)
        except TypeError as e:
            _LOGGER.exception(e)
            six.raise_from(exc.InvalidCliValueError(k, v), e)
        if nk == argspec.varargs:
            varargs = value
        elif (nk in argspec.args or argspec.varkw) and (
                nk not in named_args or named_args[nk] is None):
            named_args[nk] = value
    return func(*varargs, **named_args)


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


def _getargspec(func):
    """Return a Python 3-like argspec object.

    Note:
        args contains varargs and varkw if they exist. This behavior differs
        from getargspec and getfullargspec.

    Args:
        func: The function to inspect.

    Returns:
        A named tuple with three parameters:
            args: All named arguments, including varargs and varkw if they are
                not None.
            varargs: The name of the *args variable. May be None.
            varkw: The name of the **kwargs variable. May be None.
    """
    argspec = _getspec(func)
    args = list(argspec.args)
    if argspec.varargs:
        args += [argspec.varargs]
    if argspec[2]:  # "keywords" in PY2 and "varkw" in PY3
        args += [argspec[2]]
    return _ArgSpec(args, argspec.varargs, argspec[2])


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
        do_not_shadow = dir(six.moves.builtins)  # type: ignore
        if keyword.iskeyword(nk) or nk in do_not_shadow:
            nk += '_'
        _LOGGER.debug('Normalized "%s" to "%s".', k, nk)
        yield k, nk, v
