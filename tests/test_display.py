# -*- coding: utf-8 -*-
"""Tests for display widgets."""

from __future__ import unicode_literals

import re

import colorama

import rapcom.display


_CTRL_CHAR = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')


def test_run_tasks(capsys):
    """Test that run tasks prints the expected messages."""
    def _error():
        raise RuntimeError

    def _custom_error():
        raise rapcom.display.Status('CUSTOM', colorama.Fore.YELLOW)

    try:
        rapcom.display.run_tasks(
            'Test Header',
            [
                ('Task 1', lambda: None),
                ('Task 2', lambda: None, 20),
                ('Task 3', _custom_error),
                ('Task 4', _error)
            ]
        )
    except RuntimeError:
        pass
    output, _ = capsys.readouterr()
    lines = [i.strip() for i in _CTRL_CHAR.sub('', output).split('\n')
             if i.strip()]
    assert lines[0] == ('=' * 33) + ' Test Header ' + ('=' * 34)
    assert lines[1] == 'Task 1\r[  OK  ]'
    assert lines[2] == 'Task 2\r[  OK  ]'
    assert lines[3] == 'Task 3\r[CUSTOM]'
    assert lines[4] == 'Task 4\r[FAILED]'
    assert lines[5] == ('=' * 30) + ' completed in 0.00s ' + ('=' * 30)
