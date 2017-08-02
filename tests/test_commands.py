# -*- coding: utf-8 -*-
"""Tests for autodetection of commands."""

from __future__ import unicode_literals

import inspect


def test_func_command(create_project, run):
    """Test that a single command is successfully generated."""
    with create_project('''
        def hello(name):
            """usage: say hello <name>"""
            print('Hello, {name}!'.format(name=name))
    '''):
        assert run('say hello world') == 'Hello, world!\n'


def test_class_command(create_project, run):
    """Test that class commands are generated correctly."""
    with create_project('''
        class Say:
            """usage: say hello <name>"""
            def __call__(self, name):
                print('Hello, {name}!'.format(name=name))
    '''):
        assert run('say --log-level DEBUG hello world') == 'Hello, world!\n'


def test_class_command_from_obj(create_project, run):
    """Test that class commands inheriting from object are generated."""
    with create_project('''
        class Say(object):
            """usage: say hello <name>"""
            def __call__(self, name):
                print('Hello, {name}!'.format(name=name))
    '''):
        assert run('say hello world') == 'Hello, world!\n'


def test_mod_command(create_project, run):
    """Test that module commands are generated and called correctly."""
    with create_project('''
        """usage: say hello <name>"""
        class Command(object):
            def __call__(self, name):
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

        def rawr():
            """usage: roar rawr"""
            print('RAWR!')
    '''):
        assert run('say hello world') == 'Hello, world!\n'
        assert run('say hiya') == 'Hiya!\n'
        assert run('roar rawr') == 'RAWR!\n'


def test_help(create_project, run):
    """Test that the help subcommand responds as expected."""
    help1 = 'usage: say help-1'
    help2 = 'usage: say help-2'
    with create_project('''
        def help1():
            """{}"""

        def help2():
            """{}"""
    '''.format(help1, help2)):
        commands_help = run('say help -a')
        assert 'help-1' in commands_help
        assert 'help-2' in commands_help
        assert run('say help help-1')[:-1] == help1
        assert run('say help-1 -h')[:-1] == help1
        assert run('say help-1 --help')[:-1] == help1
        assert run('say help help-2')[:-1] == help2
        assert run('say help-2 -h')[:-1] == help2
        assert run('say help-2 --help')[:-1] == help2


def test_custom_primary_command(create_project, run):
    """Test creating a command that overwrites the primary command."""
    usage = '''
        Usage: hello [--name <name>]

        Options:
          --name <name>  The name to print [default: world].
        '''
    with create_project('''
        def hello(name):
            """{usage}"""
            print('Hello, {{name}}!'.format(name=name))
    '''.format(usage=usage)):
        assert run('hello --name everyone') == 'Hello, everyone!\n'
        assert run('hello') == 'Hello, world!\n'
        assert inspect.cleandoc(run('hello -h')) == inspect.cleandoc(usage)


def test_primary_command_with_dispatch(create_project, run):
    """Test that custom primary commands support dispatch."""
    with create_project('''
        def roar():
            """
            Usage: roar [--log-level <level>] [<command>]

            Options:
              --log-level <level>  The log level.
            """
            print('ROAR!')

        def rawr():
            """usage: roar rawr"""
            print('RAWR!')
    '''):
        assert run('roar') == 'ROAR!\n'
        assert run('roar rawr') == 'RAWR!\n'


def test_primary_command_with_dispatch_args(create_project, run):
    """Test that custom primary commands support dispatch."""
    with create_project('''
        def roar():
            """
            Usage: roar [--log-level <level>] [<command> [<args>...]]

            Options:
              --log-level <level>  The log level.
            """
            print('ROAR!')

        def rawr():
            """usage: roar rawr"""
            print('RAWR!')
    '''):
        assert run('roar') == 'ROAR!\n'
        assert run('roar --log-level DEBUG rawr') == 'RAWR!\n'


def test_merge_primary_command(create_project, run):
    """Test that a simple primary command is attached to the default doc."""
    with create_project('''
        def roar():
            """usage: roar"""
            print('ROAR!')

        def rawr():
            """usage: roar rawr"""
            print('RAWR!')
    ''', '''
        [rcli]
        merge_primary_command = True
    '''):
        assert run('roar') == 'ROAR!\n'
        assert run('roar rawr') == 'RAWR!\n'


def test_subcommand_with_same_name(create_project, run):
    """Test that a command with a subcommand of the same name does not fail."""
    with create_project('''
        def say():
            """usage: say say"""
            print('Say!')
    '''):
        assert run('say say') == 'Say!\n'
        assert run('say --log-level DEBUG say') == 'Say!\n'


def test_dedent(create_project, run):
    """Verify that usage strings are dedented correctly."""
    usage = """Usage: say hello [--name <name>]

            Options:
              --name <name>  The name to print [default: world].
            """
    with create_project('''
        def hello(name):
            """{usage}"""
    '''.format(usage=usage)):
        assert run('say hello -h')[:-1] == inspect.cleandoc(usage)


def test_multiline_usage(create_project, run):
    """Verify that multiline usage strings are parsed correctly."""
    usage = '''Usage: say hello [--name <name>]
                                [--again]

            Options:
                --name <name>  The name to print [default: world].
                --again        Say it twice.
            '''
    with create_project('''
        def hello(name, again):
            """{usage}"""
    '''.format(usage=usage)):
        assert 'hello' in run('say help -a')[:-1]
        assert '[--again]' not in run('say help -a')[:-1]


def test_positional_args(create_project, run):
    """Verify that positional argument parameters work as expected."""
    with create_project('''
        def hello(*name):
            """usage: say hello <name>..."""
            print('Hello, {name}!'.format(name=name))
    '''):
        assert run('say hello world bob') == "Hello, ('world', 'bob')!\n"


def test_keyword_args(create_project, run):
    """Verify that unused keyword argument parameters work as expected."""
    with create_project('''
        def hello(**kwargs):
            """usage: say hello <name>"""
            print('Hello, {name}!'.format(name=kwargs['name']))
    '''):
        assert run('say hello world') == "Hello, world!\n"
