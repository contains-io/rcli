# -*- coding: utf-8 -*-
"""Tests for display widgets."""

from __future__ import unicode_literals

import contextlib
import re
import sys

import colorama

import rcli.display


_CTRL_CHAR = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')


def test_run_tasks(capsys):
    """Test that run tasks prints the expected messages."""
    with _colorama(strip=False), _force_tty():
        try:
            rcli.display.run_tasks(
                'Test Header',
                [
                    ('Task 1', lambda: None),
                    ('Task 2', lambda: None, 20),
                    ('Task 3', _custom_status),
                    ('Task 4', _error)
                ]
            )
        except RuntimeError:
            pass
    output, _ = capsys.readouterr()
    assert output.count(colorama.Fore.GREEN) == 2
    assert output.count(colorama.Fore.RED) == 1
    assert output.count(colorama.Fore.YELLOW) == 1
    assert output.count(colorama.Style.BRIGHT) == 6
    lines = [i.strip() for i in _CTRL_CHAR.sub('', output).split('\n')
             if i.strip()]
    assert lines[0] == ('=' * 33) + ' Test Header ' + ('=' * 34)
    assert lines[1].startswith('Task 1') and lines[1].endswith('[  OK  ]')
    assert lines[2].startswith('Task 2') and lines[2].endswith('[  OK  ]')
    assert lines[3].startswith('Task 3') and lines[3].endswith('[CUSTOM]')
    assert lines[4].startswith('Task 4') and lines[4].endswith('[FAILED]')
    assert re.match(r'{0} completed in \d.\d\ds {0}'.format(('=' * 30)),
                    lines[5])


def test_run_tasks_no_tty(capsys):
    """Test that run tasks prints the expected messages."""
    with _colorama():
        try:
            rcli.display.run_tasks(
                'Test Header',
                [
                    ('Task 1', lambda: None),
                    ('Task 2', lambda: None, 20),
                    ('Task 3', _custom_status),
                    ('Task 4', _error)
                ]
            )
        except RuntimeError:
            pass
    output, _ = capsys.readouterr()
    lines = output.split('\n')
    assert lines[0] == ('=' * 33) + ' Test Header ' + ('=' * 34)
    assert lines[1].startswith('Task 1') and lines[1].endswith('[  OK  ]')
    assert lines[2].startswith('Task 2') and lines[2].endswith('[  OK  ]')
    assert lines[3].startswith('Task 3') and lines[3].endswith('[CUSTOM]')
    assert lines[4].startswith('Task 4') and lines[4].endswith('[FAILED]')
    assert re.match(r'{0} completed in \d.\d\ds {0}'.format(('=' * 30)),
                    lines[5])


@contextlib.contextmanager
def _colorama(*args, **kwargs):
    """Temporarily enable colorama."""
    colorama.init(*args, **kwargs)
    try:
        yield
    finally:
        colorama.deinit()


def _error():
    """Raise a RuntimeError."""
    raise RuntimeError()


def _custom_status():
    """Raise a custom status."""
    raise rcli.display.Status('CUSTOM', colorama.Fore.YELLOW)


@contextlib.contextmanager
def _force_tty():
    """Force TTY detection to be true."""
    stdout_isatty = sys.stdout.isatty
    stderr_isatty = sys.stderr.isatty
    stdin_isatty = sys.stdin.isatty
    sys.stdout.isatty = sys.stderr.isatty = sys.stdin.isatty = lambda: True
    try:
        yield
    finally:
        sys.stdout.isatty = stdout_isatty
        sys.stderr.isatty = stderr_isatty
        sys.stdin.isatty = stdin_isatty
