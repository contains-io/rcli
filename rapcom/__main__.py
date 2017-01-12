#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""An automatic command that handles subcommand dispatch."""

from __future__ import unicode_literals

import inspect
import logging
import os.path
import re
import sys
import textwrap
import types

from docopt import docopt
import colorama
import pkg_resources
import six


_LOGGER = logging.getLogger(__name__)


_COMMAND = os.path.basename(os.path.realpath(os.path.abspath(sys.argv[0])))
_SUBCOMMANDS = {}
_DEFAULT_DOC = """
Usage:
  {command} [--help] [--version] [--log-level <level>] <command> [<args>...]

Options:
  --help               Display this help message and exit.
  --version            Display the version and exit.
  --log-level <level>  Set the log level to one of DEBUG, INFO, WARN, or ERROR.
{{message}}
'{command} help -a' lists all available subcommands.
See '{command} help <command>' for more information on a specific command.
""".format(command=_COMMAND)


def main():
    """Parse the command line options and launch the requested command.

    If the command is 'help' then print the help message for the subcommand; if
    no subcommand is given, print the standard help message.
    """
    _SUBCOMMANDS.update(_get_subcommands())
    dist_version = _get_dist_version()
    if None not in _SUBCOMMANDS:
        doc = _DEFAULT_DOC.format(message='')
    else:
        doc = _SUBCOMMANDS[None].__doc__
    allow_subcommands = '<command>' in doc
    args = docopt(doc, version=dist_version, options_first=allow_subcommands)
    _enable_logging(args.get('--log-level'))
    try:
        if args.get('<command>') == 'help':
            subcommand = next(iter(args['<args>']), None)
            return _help(subcommand)
        else:
            argv = [args.get('<command>')] + args.get('<args>', sys.argv[1:])
            return _run_command(argv)
    except (KeyboardInterrupt, EOFError):
        return "Cancelling at the user's request."
    except Exception as e:  # pylint: disable=broad-except
        _LOGGER.exception('An unexpected error has occurred.')
        return e


def _normalize(func, cli_args):
    """Alter the docopt args to be valid python names for func.

    Returns a dictionary based on cli_args that uses normalized keys. Keys are
    normalized to valid python names.

    Args:
        func: The function being called to run the command.
        cli_args: The parsed results of docopt for the given command.

    Returns:
        A dictionary containing normalized keys from the CLI arguments. If the
        CLI arguments contains values that the function will not accept, those
        keys will not be returned.
    """
    def _norm(k):
        """Normalize a single key."""
        if k.startswith('--'):
            k = k[2:]
        if k.startswith('-'):
            k = k[1:]
        if k.startswith('<') and k.endswith('>'):
            k = k[1:-1]
        return k.lower().replace('-', '_')

    if isinstance(func, types.FunctionType) or not hasattr(func, '__call__'):
        params = _get_signature(func)
    else:
        params = _get_signature(func.__call__)[1:]
    args = {}
    for k, v in six.iteritems(cli_args):
        nk = _norm(k)
        if nk in params:
            args[nk] = v
    return args


def _get_signature(func):
    """Return the signature of the given function.

    inspect.getargspec() no longer exists as of Python 3.6, so detect the
    correct method of accessing the signature for each language and return the
    list of argument names.

    Args:
        func: The function from which to retrieve parameter names.

    Returns:
        A list of valid parameter names for the given function.
    """
    if six.PY3:
        return [p.name for p in inspect.signature(func).parameters.values()
                if p.kind == p.POSITIONAL_OR_KEYWORD]
    return inspect.getargspec(func).args  # pylint: disable=deprecated-method


def _get_entry_point():
    """Return the currently active entry point."""
    mod_name = sys.modules[__name__].__name__
    for ep in pkg_resources.iter_entry_points(group='console_scripts'):
        if ep.name == _COMMAND and ep.module_name == mod_name:
            return ep


def _get_dist_version():
    """Return the version of the distribution that created this entry point."""
    entry_point = _get_entry_point()
    if entry_point and hasattr(entry_point.dist, 'version'):
        return str(entry_point.dist)


def _get_subcommands():
    """Return all subcommands for the current command."""
    regex = re.compile(r'{}:(?P<name>[^:]+)$'.format(_COMMAND))
    subcommands = {}
    for ep in pkg_resources.iter_entry_points(group='rapcom'):
        try:
            if ep.name == _COMMAND:
                subcommands[None] = ep.load()
            else:
                match = re.match(regex, ep.name)
                if match:
                    subcommands[match.group('name')] = ep.load()
        except ImportError:
            _LOGGER.exception('Unable to load command. Skipping.')
    return subcommands


def _get_subcommand(name):
    """Return the function for the specified subcommand.

    Args:
        name: The name of a subcommand.

    Returns:
        The loadable object from the entry point represented by the subcommand.
    """
    _LOGGER.debug('Accessing subcommand "%s".', name)
    if name not in _SUBCOMMANDS:
        raise ValueError(
            '"{subcommand}" is not a {command} command. \'{command} help -a\' '
            'lists all available subcommands.'.format(
                command=_COMMAND, subcommand=name)
        )
    return _SUBCOMMANDS[name]


def _get_callable(subcommand, args):
    """Return a callable object from the subcommand.

    Args:
        subcommand: A object loaded from an entry point. May be a module,
            class, or function.
        args: The list of arguments parsed by docopt, before normalization.
            These are passed to the init method of any class-based callable
            objects being returned.

    Returns:
        The callable entry point for the subcommand. If the subcommand is a
        function, it will be returned unchanged. If the subcommand is a module
        or a class, an instance of the command class will be returned.

    Raises:
        AssertionError: Raised when a module entry point does not have a
            callable class named Command.
    """
    _LOGGER.debug(
        'Creating callable from subcommand "%s" with command line arguments: '
        '%s', subcommand.__name__, args)
    if isinstance(subcommand, types.ModuleType):
        _LOGGER.debug('Subcommand is a module.')
        assert hasattr(subcommand, 'Command'), (
            'Module subcommand must have callable "Command" class definition.')
        subcommand = subcommand.Command
    if any(isinstance(subcommand, t) for t in six.class_types):
        try:
            return subcommand(**args)
        except TypeError:
            _LOGGER.debug('Subcommand does not take arguments.')
            return subcommand()
    return subcommand


def _run_command(argv):
    """Run the command with the the given CLI options and exit.

    Command functions are expected to have a __doc__ string that is parseable
    by docopt.

    If the the function object has a 'validate' attribute, the
    arguments passed to the command will be validated before the command is
    called.

    If the function object has a 'schema' attribute, but not a 'validate'
    attribute, and the 'schema' attribute has a 'validate' attribute, the
    schema validate method will be called for validation.

    Args:
        argv: The list of command line arguments supplied for a command. The
            first argument is expected to be the name of the command to be run.
            Note that this is different than the full arguments parsed by
            docopt for the entire program.

    Raises:
        ValueError: Raised if the user attempted to run an invalid command.
    """
    command_name, argv = _get_command_and_argv(argv)
    _LOGGER.info('Running command "%s %s" with args: %s', _COMMAND,
                 command_name, argv)
    subcommand = _get_subcommand(command_name)
    doc = _get_usage(subcommand.__doc__)
    args = _get_parsed_args(command_name, doc, argv)
    call = _get_callable(subcommand, args)
    args = _validate(call, args)
    return call(**_normalize(call, args)) or 0


def _get_command_and_argv(argv):
    """Extract the command name and arguments to pass to docopt.

    Args:
        argv: The argument list being used to run the command.

    Returns:
        A tuple containing the name of the command and the arguments to pass
        to docopt.
    """
    command_name = argv[0]
    if not command_name:
        argv = argv[1:]
    elif command_name == _COMMAND:
        argv.remove(command_name)
    return command_name, argv


def _get_parsed_args(command_name, doc, argv):
    """Parse the docstring with docopt.

    Args:
        command_name: The name of the subcommand to parse.
        doc: A docopt-parseable string.
        argv: The list of arguments to pass to docopt during parsing.

    Returns:
        The docopt results dictionary. If the subcommand has the same name as
        the primary command, the subcommand value will be added to the
        dictionary.
    """
    _LOGGER.debug('Parsing docstring: """%s""" with arguments %s.', doc, argv)
    args = docopt(doc, argv=argv)
    if command_name == _COMMAND:
        args[command_name] = True
    return args


def _validate(call, args):
    """Validate the arguments against the callable.

    Args:
        call: The subcommand callable object that may have a validate or schema
            attribute.
        args:
            The resulting dictionary from the prior docopt parse.

    Returns:
        An updated version of the args dictionary that has been validated and
        cast using the validate methods available on the callable.
    """
    has_schema = hasattr(call, 'schema') and hasattr(call.schema, 'validate')
    if not hasattr(call, 'validate') and has_schema:
        call.validate = call.schema.validate
    if hasattr(call, 'validate'):
        _LOGGER.debug('Validating command arguments with "%s".', call.validate)
        args.update(call.validate(args))
    return args


def _help(command):
    """Print out a help message and exit the program.

    Args:
        command: If a command value is supplied then print the help message for
            the command module if available. If the command is '-a' or '--all',
            then print the standard help message but with a full list of
            available commands.

    Raises:
        ValueError: Raised if the help message is requested for an invalid
            command or an unrecognized option is passed to help.
    """
    if not command:
        doc = _DEFAULT_DOC.format(message='')
    elif command in ('-a', '--all'):
        available_commands = [k for k in _SUBCOMMANDS.keys() if k] + ['help']
        command_doc = '\nAvailable commands:\n{}\n'.format(
            '\n'.join('  {}'.format(c) for c in sorted(available_commands)))
        doc = _DEFAULT_DOC.format(message=command_doc)
    elif command.startswith('-'):
        raise ValueError("Unrecognized option '{}'.".format(command))
    else:
        subcommand = _get_subcommand(command)
        doc = _get_usage(subcommand.__doc__)
    docopt(doc, argv=('--help',))


def _get_usage(doc):
    """Format the docstring for display to the user.

    Args:
        doc: The docstring to reformat for display.

    Returns:
        The docstring formatted to parse and display to the user. This includes
        dedenting, rewrapping, and translating the docstring if necessary.
    """
    return textwrap.dedent(doc)


def _enable_logging(log_level):
    """Set the root logger to the given log level and add a color formatter.

    Args:
        log_level: The logging level to set the root logger. Must be None,
            "DEBUG", "INFO", "WARN", or "ERROR".

    Raises:
        ValueError: Raised if the given log level is not in the acceptable
            list of values.
    """
    if log_level not in (None, 'DEBUG', 'INFO', 'WARN', 'ERROR'):
        raise ValueError('Invalid log level "{}".'.format(log_level))
    root_logger = logging.getLogger()
    if log_level:
        handler = logging.StreamHandler()
        handler.setFormatter(_LogColorFormatter())
        root_logger.addHandler(handler)
        root_logger.setLevel(getattr(logging, log_level))
    else:
        root_logger.addHandler(logging.NullHandler())


class _LogColorFormatter(logging.Formatter):
    """A colored logging.Formatter implementation."""

    def format(self, record):
        """Format the log record with timestamps and level based colors.

        Args:
            record: The log record to format.

        Returns:
            The formatted log record.
        """
        if record.levelno >= logging.ERROR:
            color = colorama.Fore.RED
        elif record.levelno >= logging.WARNING:
            color = colorama.Fore.YELLOW
        elif record.levelno >= logging.INFO:
            color = colorama.Fore.RESET
        else:
            color = colorama.Fore.CYAN
        self._fmt = (
            '{}{}%(levelname)s{} [%(asctime)s][%(name)s]{} %(message)s'.format(
                colorama.Style.BRIGHT,
                color,
                colorama.Fore.RESET,
                colorama.Style.RESET_ALL
            ))
        if six.PY3:
            self._style._fmt = self._fmt  # pylint: disable=protected-access
        return super(_LogColorFormatter, self).format(record)
