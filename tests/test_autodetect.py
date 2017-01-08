# -*- coding: utf-8 -*-
"""Tests for autodetection of commands."""

from __future__ import unicode_literals

import pytest


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


@pytest.mark.xfail
def test_subcmd_with_same_name(create_project, run):
    """Test that a command with a subcommand of the same name does not fail."""
    with create_project('''
        def hiya():
            """usage: say say"""
            print('Say!')
    '''):
        assert run('say say') == 'Say!\n'
