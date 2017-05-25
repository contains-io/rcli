# -*- coding: utf-8 -*-
"""Tests that verify that usage string manipulation works as expected."""

from __future__ import unicode_literals

from rcli import usage


def test_merge_doc():
    """Test two usage strings are merged correctly."""
    s1 = '''Usage:
  test --command1'''
    s2 = '''Usage:
  test --command2'''
    expected = '''Usage:
  test --command1
  test --command2'''
    assert usage._merge_doc(s1, s2) == expected


def test_wrap():
    """Test that a large usage string is wrapped correctly."""
    initial = (
        '''I like pizza. Do you like pizza? We should be friends! '''
        '''Do you like bananas? I like bananas! But really, who doesn't? '''
        '''Everyone should have bananas!

        Usage:
          contain [--help] [--version] [--log-level <level> | --debug | '''
        '''--verbose] <command> [<args>...]
          contain bob [--help] [--version] [--log-level <level> | --debug |
                      --verbose]
                      <command> [<args>...]

        Options:
          -h, --help           Display this help message and exit.
          -V, --version        Display the version and exit.
          -d, --debug          Set the log level to DEBUG.
          -v, --verbose        Set the log level to INFO.
          --log-level <level>  Set the log level to one of DEBUG, INFO, '''
        '''WARN, or ERROR, PIZZA, PICKLE, DOGGY, MEOWTH, POKEMON, '''
        '''SUPERCALIFRAGILISTICEXPIALIDOCIOUS.

        'contain help -a' lists all available subcommands.
        See 'contain help <command>' for more information on a specific '''
        '''command.
    ''')
    expected = '''
I like pizza. Do you like pizza? We should be friends! Do you like bananas? I
like bananas! But really, who doesn't? Everyone should have bananas!

Usage:
  contain [--help] [--version] [--log-level <level> | --debug | --verbose]
          <command> [<args>...]
  contain bob [--help] [--version] [--log-level <level> | --debug | --verbose]
              <command> [<args>...]

Options:
  -h, --help           Display this help message and exit.
  -V, --version        Display the version and exit.
  -d, --debug          Set the log level to DEBUG.
  -v, --verbose        Set the log level to INFO.
  --log-level <level>  Set the log level to one of DEBUG, INFO, WARN, or ERROR,
                       PIZZA, PICKLE, DOGGY, MEOWTH, POKEMON,
                       SUPERCALIFRAGILISTICEXPIALIDOCIOUS.

'contain help -a' lists all available subcommands.
See 'contain help <command>' for more information on a specific command.'''
    assert usage.format_usage(initial, 80) == expected[1:]
