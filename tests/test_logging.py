# -*- coding: utf-8 -*-
"""Tests for autodetection of commands."""

from __future__ import unicode_literals


def test_invalid_log_level(create_project, run):
    """Test that an invalid log level does not show an exception."""
    with create_project('''
        def log():
            """usage: say log"""
    '''):
        assert run('say --log-level INVALID log', stderr=True) == (
            'Invalid value "INVALID" supplied to --log-level. Valid '
            'options are: DEBUG, INFO, WARN, ERROR\n'
        )
