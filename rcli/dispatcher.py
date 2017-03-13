# -*- coding: utf-8 -*-
"""An automatic command that handles subcommand dispatch.

Functions:
    main: The console script entry point set by autodetected CLI scripts.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import inspect
import logging
import sys
import types  # noqa: F401 pylint: disable=unused-import
import typing  # noqa: F401 pylint: disable=unused-import

from docopt import docopt
import colorama
import six

from . import (  # noqa: F401 pylint: disable=unused-import
    exceptions as exc,
    log,
    call,
    config
)
from .config import settings


_LOGGER = logging.getLogger(__name__)


_DEFAULT_DOC = """
Usage:
  {command} [--help] [--version] [--log-level <level> | --debug | --verbose]
            <command> [<args>...]

Options:
  -h, --help           Display this help message and exit.
  -V, --version        Display the version and exit.
  -d, --debug          Set the log level to DEBUG.
  -v, --verbose        Set the log level to INFO.
  --log-level <level>  Set the log level to one of DEBUG, INFO, WARN, or ERROR.
{{message}}
'{command} help -a' lists all available subcommands.
See '{command} help <command>' for more information on a specific command.
""".format(command=settings.command)


def main():
    # type: () -> typing.Any
    """Parse the command line options and launch the requested command.

    If the command is 'help' then print the help message for the subcommand; if
    no subcommand is given, print the standard help message.
    """
    colorama.init(wrap=six.PY3)
    if None not in settings.subcommands:
        msg = '\n{}\n'.format(settings.message) if settings.message else ''
        doc = _DEFAULT_DOC.format(message=msg)
    else:
        doc = settings.subcommands[None].__doc__
    doc = _get_usage(doc)
    allow_subcommands = '<command>' in doc
    args = docopt(doc, version=settings.version,
                  options_first=allow_subcommands)
    try:
        log.enable_logging(log.get_log_level(args))
        default_args = sys.argv[2 if args.get('<command>') else 1:]
        if (args.get('<command>') == 'help' and
                None not in settings.subcommands):
            subcommand = next(iter(args.get('<args>', default_args)), None)
            return _help(subcommand)
        else:
            argv = [args.get('<command>')] + args.get('<args>', default_args)
            return _run_command(argv)
    except exc.InvalidCliValueError as e:
        return str(e)
    except (KeyboardInterrupt, EOFError):
        return "Cancelling at the user's request."
    except Exception as e:  # pylint: disable=broad-except
        _LOGGER.exception('An unexpected error has occurred.')
        return log.handle_unexpected_exception(e)


def _get_subcommand(name):
    # type: (str) -> config.RcliEntryPoint
    """Return the function for the specified subcommand.

    Args:
        name: The name of a subcommand.

    Returns:
        The loadable object from the entry point represented by the subcommand.
    """
    _LOGGER.debug('Accessing subcommand "%s".', name)
    if name not in settings.subcommands:
        raise ValueError(
            '"{subcommand}" is not a {command} command. \'{command} help -a\' '
            'lists all available subcommands.'.format(
                command=settings.command, subcommand=name)
        )
    return settings.subcommands[name]


def _run_command(argv):
    # type: (typing.List[str]) -> typing.Any
    """Run the command with the given CLI options and exit.

    Command functions are expected to have a __doc__ string that is parseable
    by docopt.

    Args:
        argv: The list of command line arguments supplied for a command. The
            first argument is expected to be the name of the command to be run.
            Note that this is different than the full arguments parsed by
            docopt for the entire program.

    Raises:
        ValueError: Raised if the user attempted to run an invalid command.
    """
    command_name, argv = _get_command_and_argv(argv)
    _LOGGER.info('Running command "%s %s" with args: %s', settings.command,
                 command_name, argv)
    subcommand = _get_subcommand(command_name)
    func = call.get_callable(subcommand)
    doc = _get_usage(subcommand.__doc__)
    args = _get_parsed_args(command_name, doc, argv)
    return call.call(func, args) or 0


def _get_command_and_argv(argv):
    # type: (typing.List[str]) -> typing.Tuple[str, typing.List[str]]
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
    elif command_name == settings.command:
        argv.remove(command_name)
    return command_name, argv


def _get_parsed_args(command_name, doc, argv):
    # type: (str, str, typing.List[str]) -> typing.Dict[str, typing.Any]
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
    if command_name == settings.command:
        args[command_name] = True
    return args


def _help(command):
    # type: (str) -> None
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
        subcommands = [k for k in settings.subcommands.keys() if k is not None]
        available_commands = subcommands + ['help']
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
    # type: (str) -> str
    """Format the docstring for display to the user.

    Args:
        doc: The docstring to reformat for display.

    Returns:
        The docstring formatted to parse and display to the user. This includes
        dedenting, rewrapping, and translating the docstring if necessary.
    """
    return inspect.cleandoc(doc)
