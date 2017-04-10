# -*- coding: utf-8 -*-
"""Tests for annotation type hint casting."""
# prama pylint: disable=eval-used

from __future__ import unicode_literals

from collections import Counter, deque
import sys

import pytest


PY3 = sys.version_info.major == 3
PY3_ONLY = pytest.mark.skipif(not PY3, reason='Python 3 Only')


def test_short_comment_types(create_project, run):
    """Test type hinting with short-form comments."""
    with create_project('''
        from typing import Any, AnyStr

        def types(str1, num):
            # type: (AnyStr, int) -> Any
            """usage: say types <str1> <num>"""
            print(type(str1))
            print(type(num))
    '''):
        type_reprs = run('say types world 4', stderr=True).strip().split('\n')
        assert type_reprs == [
            repr(str),
            repr(int)
        ]


def test_long_comment_types(create_project, run):
    """Test type hinting with long-form comments."""
    with create_project('''
        from typing import Any

        def types(str1,
                  num    # type: int
                  ):
            # type: (...) -> Any
            """usage: say types <str1> <num>"""
            print(type(str1))
            print(type(num))
    '''):
        type_reprs = run('say types world 4', stderr=True).strip().split('\n')
        assert type_reprs == [
            repr(str),
            repr(int)
        ]


@PY3_ONLY
def test_annotations(create_project, run):
    """Test type hinting with Python 3 annotations."""
    with create_project('''
        def types(str1: str, num: int):
            """usage: say types <str1> <num>"""
            print(type(str1))
            print(type(num))
    '''):
        type_reprs = run('say types world 4', stderr=True).strip().split('\n')
        assert type_reprs == [
            repr(str),
            repr(int)
        ]


def test_py2_annotations(create_project, run):
    """Test type hinting with Python 2 annotations."""
    with create_project('''
        def types(str1, num):
            """usage: say types <str1> <num>"""
            print(type(str1))
            print(type(num))
        types.__annotations__ = {'str1': str, 'num': int}
    '''):
        type_reprs = run('say types world 4', stderr=True).strip().split('\n')
        assert type_reprs == [
            repr(str),
            repr(int)
        ]


@pytest.mark.parametrize('type_, expected', [
    ('AnyStr', str),
    ('str', str),
    ('ByteString', bytes)
])
def test_string_types(create_project, run, type_, expected):
    """Test type hinting with string types."""
    with create_project('''
        from typing import Any, AnyStr, ByteString

        def types(value):
            # type: ({type}) -> Any
            """usage: say types <value>"""
            print(type(value))
    '''.format(type=type_)):
        assert run('say types abc').strip().split('\n') == [repr(expected)]


@pytest.mark.parametrize('type_', [
    'int',
    'float',
    'complex'
])
def test_numeric_types(create_project, run, type_):
    """Test type hinting with numeric types."""
    with create_project('''
        from typing import Any

        def types(num):
            # type: ({type}) -> Any
            """usage: say types <num>"""
            print(type(num))
    '''.format(type=type_)):
        assert run('say types 1').strip().split('\n') == [repr(eval(type_))]


@pytest.mark.parametrize('type_, expected_type, expected', [
    ('tuple', tuple, ('1', '2', '3', '3', '4')),
    ('typing.Tuple', tuple, ('1', '2', '3', '3', '4')),
    ('typing.Tuple[int, int, int, int, int]', tuple, (1, 2, 3, 3, 4)),
    ('list', list, ['1', '2', '3', '3', '4']),
    ('typing.List', list, ['1', '2', '3', '3', '4']),
    ('typing.List[int]', list, [1, 2, 3, 3, 4]),
    ('typing.MutableSequence', list, ['1', '2', '3', '3', '4']),
    ('typing.MutableSequence[int]', list, [1, 2, 3, 3, 4]),
    ('set', set, {'1', '2', '3', '4'}),
    ('typing.Set', set, {'1', '2', '3', '4'}),
    ('typing.Set[int]', set, {1, 2, 3, 4}),
    ('typing.MutableSet', set, {'1', '2', '3', '4'}),
    ('typing.MutableSet[int]', set, {1, 2, 3, 4}),
    ('frozenset', frozenset, frozenset(['1', '2', '3', '4'])),
    ('typing.FrozenSet', frozenset, frozenset(['1', '2', '3', '4'])),
    ('typing.FrozenSet[int]', frozenset, frozenset([1, 2, 3, 4])),
    ('deque', deque, deque(['1', '2', '3', '3', '4'])),
    ('Counter', Counter, Counter({'1': 1, '2': 1, '3': 2, '4': 1}))
])
def test_sequence_types(create_project, run, type_, expected_type, expected):
    """Test type hinting with sequence types."""
    with create_project('''
        from collections import Counter, deque
        import typing

        def types(value):
            # type: ({type}) -> typing.Any
            """usage: say types <value>..."""
            print(repr(value))
            print(type(value))
    '''.format(type=type_)):
        reprs = run('say types 1 2 3 3 4', stderr=True).strip().split('\n')
        reprs[0] = eval(reprs[0])
        assert reprs == [
            expected,
            repr(expected_type)
        ]


def test_function_as_type(create_project, run):
    """Test type hinting with dictionary types."""
    with create_project('''
        import json

        def types(dct):
            # type: (json.loads) -> None
            """usage: say types <dct>"""
            print(repr(dct))
            print(type(dct))
    '''):
        type_reprs = run(
            'say types \'{"1": 1}\'', stderr=True).strip().split('\n')
        type_reprs[0] = eval(type_reprs[0])
        assert type_reprs == [
            {'1': 1},
            repr(dict)
        ]


def test_bad_value(create_project, run):
    """Test that a bad value gives a reasonable descriptive message."""
    with create_project('''
        def types(value):
            # type: (int) -> None
            """usage: say types <value>"""
    '''):
        output = run('say types abc', stderr=True).strip()
        assert '<value>' in output
        assert 'abc' in output
        assert 'log' not in output


def test_positional_arg_casting(create_project, run):
    """Verify that positional arguments are cast as expected."""
    with create_project('''
        def types(*args):
            # type: (*int) -> None
            """usage: say types <args>..."""
            print(args)
    '''):
        actual = eval(run('say types 1 2 3')[:-1])
        assert actual == (1, 2, 3)


def test_keyword_arg_casting(create_project, run):
    """Verify that keyword arguments are cast as expected."""
    with create_project('''
        def types(**kwargs):
            # type: (**int) -> None
            """usage: say types <arg1> <arg2>"""
            print(kwargs)
    '''):
        actual = eval(run('say types 1 2')[:-1])
        assert actual == {'types': True, 'arg1': 1, 'arg2': 2}
