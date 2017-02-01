# -*- coding: utf-8 -*-
"""Autodetection of docopt-style commands and subcommands.

Functions:
    setup_keyword: Adds a keyword to setuptools.setup to autodetect commands.
"""

from __future__ import unicode_literals

import ast
import collections
import inspect
import os.path
import re
import setuptools
import six

import docopt


_EntryPoint = collections.namedtuple(  # All data representing an entry point.
    '_EntryPoint', ('command', 'subcommand', 'module', 'callable'))


_USAGE_PATTERN = re.compile(r'^([^\n]*usage\:[^\n]*\n?(?:[ \t].*?(?:\n|$))*)',
                            re.IGNORECASE | re.MULTILINE)


def setup_keyword(dist, _, value):
    """Add autodetected commands as entry points.

    Args:
        dist: The distutils Distribution object for the project being
            installed.
        _: The keyword used in the setup function. Unused.
        value: The value set to the keyword in the setup function. If the value
            is not True, this function will do nothing.
    """
    if value is not True:
        return
    if dist.entry_points is None:
        dist.entry_points = {}
    for command, subcommands in six.iteritems(_get_commands(dist)):
        dist.entry_points.setdefault('console_scripts', []).append(
            '{command} = rcli.dispatcher:main'.format(command=command)
        )
        dist.entry_points.setdefault('rcli', []).extend(subcommands)


def _get_commands(dist):
    """Find all commands belonging to the given distribution.

    Args:
        dist: The Distribution to search for docopt-compatible docstrings that
            can be used to generate command entry points.

    Returns:
        A list of entry point strings for each autodetected subcommand.
    """
    py_files = (f for f in setuptools.findall()
                if os.path.splitext(f)[1].lower() == '.py')
    pkg_files = (f for f in py_files if _get_package_name(f) in dist.packages)
    commands = {}
    for file_name in pkg_files:
        with open(file_name) as py_file:
            module = ast.parse(py_file.read())
        module.__name__ = _get_module_name(file_name)
        _append_commands(commands, _get_module_commands(module))
        _append_commands(commands, _get_class_commands(module))
        _append_commands(commands, _get_function_commands(module))
    return commands


def _append_commands(dct, commands):
    """Append entry point strings representing the given Command objects.

    Args:
        dct: The dictionary to append with entry point strings. Each key will
            be a primary command with a value containing a list of entry point
            strings representing a Command.
        commands: A list of Command objects to convert to entry point strings.
    """
    for command in commands:
        entry_point = '{command}{subcommand} = {module}{callable}'.format(
            command=command.command,
            subcommand=(':{}'.format(command.subcommand)
                        if command.subcommand else ''),
            module=command.module,
            callable=(':{}'.format(command.callable)
                      if command.callable else ''),
        )
        dct.setdefault(command.command, set()).add(entry_point)


def _get_package_name(file_name):
    """Return the python package name for the given file.

    Args:
        file_name: The file name of a python file.

    Returns:
        Converts the file name to a python-style module name and retrieves the
        package component.
    """
    return _get_module_name(file_name).rsplit('.', 1)[0]


def _get_module_name(file_name):
    """Return the python module name for the given file.

    Args:
        file_name: The file name of a python file.

    Returns:
        Converts the file name to a python-style module and returns the name.
    """
    return file_name[:-3].replace('/', '.')


def _get_module_commands(module):
    """Yield all Command objects represented by the python module.

    Module commands consist of a docopt-style module docstring and a callable
    Command class.

    Args:
        module: An ast.Module object used to retrieve docopt-style commands.

    Yields:
        Command objects that represent entry points to append to setup.py.
    """
    cls = next((n for n in module.body
                if isinstance(n, ast.ClassDef) and n.name == 'Command'), None)
    if not cls:
        return
    methods = (n.name for n in cls.body if isinstance(n, ast.FunctionDef))
    if '__call__' not in methods:
        return
    docstring = ast.get_docstring(module)
    for command, subcommand in _parse_commands(docstring):
        yield _EntryPoint(command, subcommand, module.__name__, None)


def _get_class_commands(module):
    """Yield all Command objects represented by python classes in the module.

    Class commands are detected by inspecting all callable classes in the
    module for docopt-style docstrings.

    Args:
        module: An ast.Module object used to retrieve docopt-style commands.

    Yields:
        Command objects that represent entry points to append to setup.py.
    """
    nodes = (n for n in module.body if isinstance(n, ast.ClassDef))
    for cls in nodes:
        methods = (n.name for n in cls.body if isinstance(n, ast.FunctionDef))
        if '__call__' in methods:
            docstring = ast.get_docstring(cls)
            for command, subcommand in _parse_commands(docstring):
                yield _EntryPoint(command, subcommand, module.__name__,
                                  cls.name)


def _get_function_commands(module):
    """Yield all Command objects represented by python functions in the module.

    Function commands consist of all top-level functions that contain
    docopt-style docstrings.

    Args:
        module: An ast.Module object used to retrieve docopt-style commands.

    Yields:
        Command objects that represent entry points to append to setup.py.
    """
    nodes = (n for n in module.body if isinstance(n, ast.FunctionDef))
    for func in nodes:
        docstring = ast.get_docstring(func)
        for command, subcommand in _parse_commands(docstring):
            yield _EntryPoint(command, subcommand, module.__name__, func.name)


def _parse_commands(docstring):
    """Parse a docopt-style string for commands and subcommands.

    Args:
        docstring: A docopt-style string to parse. If the string is not a valid
            docopt-style string, it will not yield and values.

    Yields:
        All tuples of commands and subcommands found in the docopt docstring.
    """
    try:
        docopt.docopt(docstring, argv=())
    except (TypeError, docopt.DocoptLanguageError):
        return
    except docopt.DocoptExit:
        pass
    match = _USAGE_PATTERN.findall(docstring)[0]
    usage = inspect.cleandoc(match.strip()[6:])
    usage_sections = [s.strip() for s in usage.split('\n') if s[:1].isalpha()]
    for section in usage_sections:
        args = section.split()
        command = args[0]
        subcommand = None
        if len(args) > 1 and not (args[1].startswith('<') or
                                  args[1].startswith('-') or
                                  args[1].startswith('[') or
                                  args[1].startswith('(') or
                                  args[1].isupper()):
            subcommand = args[1]
        yield command, subcommand
