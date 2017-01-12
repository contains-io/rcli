# -*- coding: utf-8 -*-
"""Tests for autodetection of commands."""

from __future__ import unicode_literals

import textwrap


def test_single_command(create_project, run):
    """Test that a single command is successfully generated."""
    with create_project('''
        def hello(name):
            """usage: say hello <name>"""
            print('Hello, {name}!'.format(name=name))
    '''):
        assert run('say hello world') == 'Hello, world!\n'


def test_multiple_commands(create_project, run):
    """Test that a multiple commands are successfully generated."""
    with create_project('''
        def hello(name):
            """usage: say hello <name>"""
            print('Hello, {name}!'.format(name=name))

        def hiya():
            """usage: say hiya"""
            print('Hiya!')
    '''):
        assert run('say hello world') == 'Hello, world!\n'
        assert run('say hiya') == 'Hiya!\n'


def test_primary_command_only(create_project, run):
    """Test creating a command that overwrites the primary command."""
    usage = """
            Usage: hello [--name <name>]

            Options:
                --name <name>  The name to print [default: world].
            """
    with create_project('''
        def hello(name):
            """{usage}"""
            print('Hello, {{name}}!'.format(name=name))
    '''.format(usage=usage)):
        assert run('hello --name everyone') == 'Hello, everyone!\n'
        assert run('hello') == 'Hello, world!\n'
        assert (textwrap.dedent(run('hello -h')).strip() ==
                textwrap.dedent(usage).strip())


def test_subcmd_with_same_name(create_project, run):
    """Test that a command with a subcommand of the same name does not fail."""
    with create_project('''
        def say():
            """usage: say say"""
            print('Say!')
    '''):
        assert run('say say') == 'Say!\n'
        assert run('say --log-level DEBUG say') == 'Say!\n'
