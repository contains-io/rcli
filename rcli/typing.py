# -*- coding: utf-8 -*-
"""A module for handling with typing and type hints.

Functions:
    cast: Casts a value to a specific type.
    get_signature: Retrieves the signature of a function.
    get_type_hints: Gets all type hints for an object, including comment type
        hints.

Classes:
    Bounded: A sliceable subclass of any class that raises a ValueError if the
        initialization value is out of bounds.
    Length: A sliceable subclass of any class that implements __len__ that
        raises a ValueError if the length of the initialization value is out of
        bounds.
    Singleton: A metaclass to force a class to only ever be instantiated once.

Instances:
    NoneType: A type alias for type(None)
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from typing import (  # type: ignore
    _eval_type,
    _ForwardRef,
    _get_defaults
)
from typing import (  # noqa: F401 pylint: disable=unused-import
    Any,
    ByteString,
    Callable,
    cast as std_cast,
    Dict,
    Generator,
    get_type_hints as std_get_type_hints,
    List,
    MutableSequence,
    MutableSet,
    Optional,
    Sequence,
    Tuple,
    Type,
    TypeVar,
    Union
)
import collections
import functools
import inspect
import logging
import re
import sys
import tokenize
import types

import six

from . import exceptions as exc
from .decorators import memoize


_LOGGER = logging.getLogger(__name__)

_T = TypeVar('_T')

_SEQUENCE_TYPES = (
    list,
    tuple,
    set,
    frozenset,
    collections.deque,
    collections.Counter,
    MutableSequence,
    MutableSet,
    Tuple
)

NoneType = type(None)


class Singleton(type):
    """A metaclass to turn a class into a singleton."""

    __instance__ = None  # type: type

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> type
        """Instantiate the class only once."""
        if not cls.__instance__:
            cls.__instance__ = super(Singleton, cls).__call__(*args, **kwargs)
        return cls.__instance__


class _Uninstantiable(type):
    """A metaclass that disallows instantiation."""

    def __call__(cls, *args, **kwargs):
        # type: (*Any, **Any) -> None
        """Do not allow the class to be instantiated."""
        raise TypeError('Type {} cannot be instantiated.'.format(cls.__name__))


class _ClsReprMeta(type):
    """A metaclass that returns a custom type repr if defined."""

    __class_repr__ = None  # type: Optional[str]

    def __repr__(cls):
        # type: () -> str
        """Return a custom string for the type repr if defined."""
        if cls.__class_repr__:
            return cls.__class_repr__
        return super(cls.__class__, cls).__repr__()


class _BoundedMeta(_Uninstantiable):
    """A metaclass that adds slicing to a class that creates new classes."""

    def __getitem__(cls, args):
        # type: (Union[Tuple[_T, Any], Tuple[_T, Any, Callable]]) -> type
        """Create a new subclass of a type bounded by the arguments.

        If a callable is passed as the third argument of the slice, it will be
        used as the comparison function for the boundaries.

        Args:
            args: A tuple with two or three parameters: a type, a slice
                representing the minimum and maximum lengths allowed for values
                of that type and, optionally, a function to use on values
                before comparing against the bounds.
        """
        type_, bound, keyfunc = cls._get_args(args)
        keyfunc_name = cls._get_fullname(keyfunc)
        identity = cls._identity
        try:
            class _(type_):  # type: ignore
                """Check if type_ is subclassable."""
            BaseClass = type_
        except TypeError:
            BaseClass = object  # type: ignore

        class _BoundedSubclassMeta(
                _ClsReprMeta, BaseClass.__class__):  # type: ignore
            """Use the type_ metaclass and include class repr functionality."""

        @six.add_metaclass(_BoundedSubclassMeta)
        class _BoundedSubclass(BaseClass):  # type: ignore
            """A subclass of type_ or object, bounded by a slice."""

            def __new__(cls, __value, *args, **kwargs):
                # type: (Any, *Any, **Any) -> _T
                """Return __value cast to _T.

                Any additional arguments are passed as-is to the constructor.

                Args:
                    __value: A value that can be converted to type _T.
                    args: Any additional positional arguments passed to the
                        constructor.
                    kwargs: Any additional keyword arguments passed to the
                        constructor.
                """
                try:
                    instance = BaseClass(__value, *args, **kwargs)
                except TypeError:
                    instance = __value
                cmp_val = keyfunc(instance)
                if bound.start and cmp_val < bound.start:
                    if keyfunc is not identity:
                        raise ValueError(
                            'The value of {}({}) [{}] is below the minimum '
                            'allowed value of {}.'.format(
                                keyfunc_name, repr(__value), repr(cmp_val),
                                bound.start))
                    raise ValueError(
                        'The value {} is below the minimum allowed value '
                        'of {}.'.format(repr(__value), bound.start))
                if bound.stop and cmp_val > bound.stop:
                    if keyfunc is not identity:
                        raise ValueError(
                            'The value of {}({}) [{}] is above the maximum'
                            ' allowed value of {}.'.format(
                                keyfunc_name, repr(__value), repr(cmp_val),
                                bound.stop))
                    raise ValueError(
                        'The value {} is above the maximum allowed value '
                        'of {}.'.format(repr(__value), bound.stop))
                return instance

        _BoundedSubclass.__class_repr__ = cls._get_class_repr(
            type_, bound, keyfunc, keyfunc_name)
        return _BoundedSubclass

    def _get_class_repr(cls, type_, bound, keyfunc, keyfunc_name):
        # type: (Any, slice, Callable, str) -> str
        """Return a class representation using the slice parameters.

        Args:
            type_: The type the class was sliced with.
            bound: The boundaries specified for the values of type_.
            keyfunc: The comparison function used to check the value
                boundaries.
            keyfunc_name: The name of keyfunc.

        Returns:
            A string representing the class.
        """
        if keyfunc is not cls._default:
            return '{}.{}[{}, {}, {}]'.format(
                cls.__module__, cls.__name__, cls._get_fullname(type_),
                cls._get_bound_repr(bound), keyfunc_name)
        else:
            return '{}.{}[{}, {}]'.format(
                cls.__module__, cls.__name__, cls._get_fullname(type_),
                cls._get_bound_repr(bound))

    def _get_args(cls, args):
        # type: (tuple) -> Tuple[Any, slice, Callable]
        """Return the parameters necessary to check type boundaries.

        Args:
            args: A tuple with two or three elements: a type, a slice
                representing the minimum and maximum lengths allowed for values
                of that type and, optionally, a function to use on values
                before comparing against the bounds.

        Returns:
            A tuple with three elements: a type, a slice, and a function to
            apply to objects of the given type. If no function was specified,
            it returns the identity function.
        """
        if not isinstance(args, tuple):
            raise TypeError(
                '{}[...] takes two or three arguments.'.format(cls.__name__))
        elif len(args) == 2:
            type_, bound = args
            keyfunc = cls._identity
        elif len(args) == 3:
            type_, bound, keyfunc = args
        else:
            raise TypeError(
                'Too many parameters given to {}[...]'.format(cls.__name__))
        if not isinstance(bound, slice):
            bound = slice(bound)
        if isinstance(type_, six.string_types):
            # pragma pylint: disable=protected-access
            type_ = _ForwardRef(type_)._eval_type(globals(), globals())
            # pragma pylint: enable=protected-access
        return type_, bound, keyfunc

    @staticmethod
    def _get_bound_repr(bound):
        # type: (slice) -> str
        """Return a string representation of a boundary slice.

        Args:
            bound: A slice object.

        Returns:
            A string representing the slice.
        """
        if bound.start and not bound.stop:
            return '{}:'.format(bound.start)
        if bound.stop and not bound.start:
            return ':{}'.format(bound.stop)
        return '{}:{}'.format(bound.start, bound.stop)

    @staticmethod
    def _identity(obj):
        # type: (_T) -> _T
        """Return the given object.

        Args:
            obj: An object.

        Returns:
            The given object.
        """
        return obj

    _default = _identity  # type: Callable[[Any], Any]

    @staticmethod
    def _get_fullname(obj):
        # type: (Any) -> str
        """Get the full name of an object including the module.

        Args:
            obj: An object.

        Returns:
            The full class name of the object.
        """
        if not hasattr(obj, '__name__'):
            obj = obj.__class__
        if obj.__module__ in ('builtins', '__builtin__'):
            return obj.__name__
        return '{}.{}'.format(obj.__module__, obj.__name__)


@six.add_metaclass(_BoundedMeta)
class Bounded(object):
    """A type that creates a bounded version of a type when sliced.

    Bounded can be sliced with two or three elements: a type, a slice
    representing the minimum and maximum lengths allowed for values of that
    type and, optionally, a function to use on values before comparing against
    the bounds.

    >>> Bounded[int, 5:10](7)
    7
    >>> Bounded[int, 5:10](1)
    Traceback (most recent call last):
        ...
    ValueError: The value 1 is below the minimum allowed value of 5.
    >>> Bounded[int, 5:10](11)
    Traceback (most recent call last):
        ...
    ValueError: The value 11 is above the maximum allowed value of 10.
    >>> Bounded[str, 5:10, len]('abcde')
    'abcde'
    """


class _LengthBoundedMeta(_BoundedMeta):
    """A metaclass that bounds a type with the len function."""

    _default = len

    def _get_args(cls, args):
        # type: (tuple) -> Tuple[Type[_T], slice, Callable]
        """Return the parameters necessary to check type boundaries.

        Args:
            args: A tuple with two parameters: a type, and a slice representing
                the minimum and maximum lengths allowed for values of that
                type.

        Returns:
            A tuple with three parameters: a type, a slice, and the len
            function.
        """
        if not isinstance(args, tuple) or not len(args) == 2:
            raise TypeError(
                '{}[...] takes exactly two arguments.'.format(cls.__name__))
        return super(_LengthBoundedMeta, cls)._get_args(args + (len,))


@six.add_metaclass(_LengthBoundedMeta)
class Length(object):
    """A type that creates a length bounded version of a type when sliced.

    Length can be sliced with two parameters: a type, and a slice representing
    the minimum and maximum lengths allowed for values of that type.

    >>> Length[str, 5:10]('abcde')
    'abcde'
    >>> Length[str, 5:10]('abc')
    Traceback (most recent call last):
        ...
    ValueError: The value of len('abc') [3] is below the minimum ...
    >>> Length[str, 5:10]('abcdefghijk')
    Traceback (most recent call last):
        ...
    ValueError: The value of len('abcdefghijk') [11] is above the maximum ...
    """


@memoize
def get_signature(func):
    # type: (Callable) -> Tuple[Tuple[str, ...], str, str]
    """Return the signature of the given function.

    inspect.getargspec() no longer exists as of Python 3.6, so detect the
    correct method of accessing the signature for each language and return the
    list of argument names.

    Args:
        func: The function from which to retrieve parameter names.

    Returns:
        A list of valid parameter names for the given function.
    """
    getargspec = getattr(
        inspect, 'get{}argspec'.format('full' if six.PY3 else ''))
    args, vararg, kwarg = getargspec(func)[:3]
    args = args[1:] if isinstance(func, types.MethodType) else args
    _LOGGER.debug('Found signature parameters: %s', (args, vararg, kwarg))
    return args, vararg, kwarg


def get_type_hints(obj,  # type: Any
                   globalns=None,  # type: Optional[Dict[str, Any]]
                   localns=None  # type: Optional[Dict[str, Any]]
                   ):
    # type: (...) -> Dict[str, Any]
    """Return all type hints for the function.

    This attempts to use typing.get_type_hints first, but if that returns None
    then it will attempt to reuse much of the logic from the Python 3 version
    of typing.get_type_hints; the Python 2 version does nothing. In addition to
    this logic, if no code annotations exist, it will attempt to extract
    comment type hints for Python 2/3 compatibility.

    Args:
        obj: The object to search for type hints.
        globalns: The currently known global namespace.
        localns: The currently known local namespace.

    Returns:
        A mapping of value names to type hints.
    """
    # pragma pylint: disable=protected-access
    globalns, localns = _get_namespace(obj, globalns, localns)
    hints = std_get_type_hints(obj, globalns, localns) or {}  # type: ignore
    if not hints and not getattr(obj, '__no_type_check__', None):
        hints.update(getattr(obj, '__annotations__', {}))
        if not hints:
            hints.update(_get_comment_type_hints(obj, globalns, localns))
        for name, value in six.iteritems(hints):
            if value is None:
                value = NoneType
            if isinstance(value, six.string_types):
                value = _ForwardRef(value)
            value = _eval_type(
                value, globalns, localns)
            if _is_optional(obj, name):
                value = Optional[value]  # type: ignore
            hints[name] = value
    return hints
    # pragma pylint: enable=protected-access


def _get_namespace(obj,  # type: Any
                   globalns,  # type: Optional[Dict[str, Any]]
                   localns  # type: Optional[Dict[str, Any]]
                   ):
    # type: (...) -> Tuple[Dict[str, Any], Dict[str, Any]]
    """Retrieve the global and local namespaces for an object.

    Args:
        obj: An object.
        globalns: The currently known global namespace.
        localns: The currently known local namespace.

    Returns:
        A tuple containing two dictionaries for the global and local namespaces
        to be used by eval.
    """
    if globalns is None:
        globalns = getattr(obj, '__globals__', {})
        if localns is None:
            localns = globalns
    elif localns is None:
        localns = globalns
    return globalns, localns


def _get_comment_type_hints(func,  # type: Callable
                            globalns,  # type: Dict[str, Any]
                            localns  # type: Dict[str, Any]
                            ):
    # type: (...) -> Dict[str, Any]
    """Get a mapping of parameter names to type hints from type hint comments.

    Args:
        func: The function to search for type hint comments.

    Returns:
        A dictionary mapping the function parameters to the type hints found
        for each parameter in the type hint comments.
    """
    try:
        source = inspect.getsource(func)
    except IOError:
        return {}
    hints = {}
    full_signature = get_signature(func)
    signature = full_signature[0] + list(s for s in full_signature[1:] if s)
    for comment in _get_type_comments(source):
        name, value = comment
        name = name.strip()
        value = value.strip()
        if name in signature:
            hints[name] = value
        elif name.startswith('(') and name.endswith(')'):
            hints['return'] = value
            type_values = _parse_short_form(name, globalns, localns)
            if len(type_values) == len(signature) + 1:
                type_values = type_values[1:]
            if len(type_values) == len(signature):
                hints.update(zip(signature, type_values))  # type: ignore
    return hints


def _is_optional(func, name):
    # type: (Callable, str) -> bool
    """Determine if the argument is optional for the function.

    Args:
        func: A function that takes arguments.
        name: The name of an argument to the function.

    Returns:
        True if the argument is optional for the function; otherwise, False.
    """
    defaults = _get_func_defaults(func)
    return bool(name in defaults and defaults[name] is None)


@memoize
def _get_func_defaults(func):
    # type: (Callable) -> Dict[str, Any]
    """Get the default values for the function parameters.

    Args:
        func: The function to inspect.

    Returns:
        A mapping of parameter names to default values.
    """
    # pragma pylint: disable=protected-access
    _func_like = functools.wraps(func)(lambda: None)
    if not hasattr(_func_like, '__kwdefaults__'):  # type: ignore
        _func_like.__kwdefaults__ = {}  # type: ignore
    return _get_defaults(_func_like)
    # pragma pylint: enable=protected-access


def _get_type_comments(source):
    # type: (str) -> Generator[Tuple[str, str], None, None]
    """Yield type hint comments from the source code.

    Args:
        source: The source code of the function to search for type hint
            comments.

    Yields:
        All type comments that come before the body of the function as
        (name, type) pairs, where the name is the name of the variable and
        type is the type hint. If a short-form type hint is reached, it is
        yielded as a single string containing the entire type hint.
    """
    reader = six.StringIO(source).readline
    name = last_token = None
    tokens = tokenize.generate_tokens(reader)  # type: ignore
    for token, value, _, _, _ in tokens:
        if token == tokenize.INDENT:
            return
        if token == tokenize.NAME:
            name = value
        elif token == tokenize.COMMENT:
            match = re.match(r'#\s*type:(.+)', value)
            if match:
                type_sig = match.group(1).strip()
                if '->' in type_sig and last_token == tokenize.NEWLINE:
                    yield type_sig.split('->')
                elif name:
                    yield name, type_sig
                    name = None
        last_token = token


def _parse_short_form(comment, globalns, localns):
    # type: (str, Dict[str, Any], Dict[str, Any]) -> Tuple[type, ...]
    """Return the hints from the comment.

    Parses the left-hand side of a type comment into a list of type objects.
    (e.g. everything to the left of "->").

    Returns:
        A list of types evaluated from the type comment in the given global
        name space.
    """
    if '(...)' in comment:
        return ()
    comment = comment.replace('*', '')
    hints = eval(comment, globalns, localns)  # pylint: disable=eval-used
    if not isinstance(hints, tuple):
        hints = (hints,)
    return hints


def cast(type_, value):
    # type: (Type[_T], Any) -> _T
    """Cast the value to the given type.

    Args:
        type_: The type the value is expected to be cast.
        value: The value to cast.

    Returns:
        The cast value if it was possible to determine the type and cast it;
        otherwise, the original value.
    """
    assert type_ is not NoneType
    if type_ is Any:
        return value
    if type_ is ByteString:
        return value.encode(sys.stdin.encoding or sys.getdefaultencoding())
    if isinstance(type_, type):
        if any(issubclass(type_, typ)  # type: ignore
                for typ in _SEQUENCE_TYPES):
            return _cast_sequence(type_, value)  # type: ignore
    for typ in _get_cast_types(type_):
        try:
            return typ(value)
        except (TypeError, ValueError):
            pass
    raise exc.CastError(type_, value)


def _get_cast_types(type_):
    # type: (Any) -> List[Union[type, Callable]]
    """Return all type callable type constraints for the given type.

    Args:
        type_: The type variable that may be callable or constrainted.

    Returns:
        A list of all callable type constraints for the type.
    """
    cast_types = [type_] if callable(type_) else []
    if (hasattr(type_, '__constraints__') and
            isinstance(type_.__constraints__, collections.Iterable)):
        cast_types.extend(type_.__constraints__)
    if (hasattr(type_, '__args__') and
            isinstance(type_.__args__, collections.Iterable)):
        cast_types.extend(type_.__args__)
    return cast_types


def _cast_sequence(type_, value):
    # type: (Any, Any) -> Sequence[_T]
    """Cast the value to the given sequence type.

    Args:
        type_: The type the value is expected to be cast.
        value: The value to cast.

    Returns:
        A sequence containing all of the values in value cast to the
        appropriate type if it was possible to determine a type and
        successfully cast the value to it. If the value is a string, it will
        attempt to parse it as a CSV string.
    """
    if issubclass(type_, (tuple, Tuple)):  # type: ignore
        return _cast_tuple(type_, value)
    if hasattr(type_, '__args__') and type_.__args__:
        typ = type_.__args__[0]
        value = [cast(typ, v) for v in value]
    if issubclass(type_, (set, MutableSet)):
        return std_cast(Sequence[_T], set(value))
    if issubclass(type_, frozenset):
        return std_cast(Sequence[_T], frozenset(value))
    if issubclass(type_, collections.deque):
        return std_cast(Sequence[_T], collections.deque(value))
    if issubclass(type_, collections.Counter):
        return std_cast(Sequence[_T], collections.Counter(value))
    return list(value)


def _cast_tuple(type_, values):
    # type: (Type[_T], Any) -> Tuple[_T, ...]
    """Cast the value to a tuple.

    Args:
        type_: The type the value is expected to be cast.
        values: A list of values to be converted to a tuple and cast using
            tuple logic.

    Returns:
        A tuple containing all of the values cast to the appropriate types.

    Raises:
        ValueError: Raised if the number of tuple parameter type arguments does
            not match the number of arguments in the values.
    """
    has_args = hasattr(type_, '__args__') and type_.__args__  # type: ignore
    tuple_types = type_.__args__ if has_args else ()  # type: ignore
    if not tuple_types and hasattr(type_, '__tuple_params__'):
        tuple_types = type_.__tuple_params__  # type: ignore
    if tuple_types:
        if (len(tuple_types) == 2 and tuple_types[1] is Ellipsis) or (
                len(tuple_types) == 1 and
                getattr(type_, '__tuple_use_ellipsis__', None)):
            values = [cast(tuple_types[0], val) for val in values]
        elif len(values) != len(tuple_types):
            raise exc.CastError(type_, values)
        else:
            values = [cast(typ, val) for typ, val in zip(tuple_types, values)]
    return tuple(values)
