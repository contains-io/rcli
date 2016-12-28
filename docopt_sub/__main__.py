#!/usr/bin/env python

"""An automatic command that handles subcommands in a git-like fashion."""

import inspect
import logging
import os.path
import re
import sys

from docopt import docopt
import pkg_resources


__all__ = ('main',)


_COMMAND = os.path.basename(os.path.realpath(os.path.abspath(sys.argv[0])))
_DEFAULT_DOC = """
Usage: {command} <command> [<args>...]
       {command} (-h | --help)
       {command} (-V | --version)

Options:
  -h, --help           Display this help message and exit.
  -V, --version        Display the version and exit.
{{message}}
'{command} help -a' lists all available subcommands.
See '{command} help <command>' for more information on a specific command.
""".format(command=_COMMAND)


_root_logger = logging.getLogger()
_root_logger.addHandler(logging.NullHandler())
_root_logger.setLevel(logging.INFO)
_logger = logging.getLogger(__name__)
_subcommands = {}


def main():
    """Parse the command line options and launch the requested command.

    If the command is 'help' then print the help message for the subcommand; if
    no subcommand is given, print the standard help message.
    """
    _subcommands.update(_get_subcommands())
    dist_version = _get_dist_version()
    doc = _DEFAULT_DOC.format(message='')
    args = docopt(doc, version=dist_version, options_first=True)
    try:
        if args['<command>'] == 'help':
            subcommand = next(iter(args['<args>']), None)
            _help(subcommand)
        else:
            argv = [args['<command>']] + args['<args>']
            _run_command(argv)
    except (KeyboardInterrupt, EOFError):
        return "Cancelling at the user's request."
    except Exception as e:
        _logger.exception(e)
        return e


def _normalize(cli_args, func):
    """Alter the docopt args to be valid python names for func."""
    def _norm(k):
        """Normalize a single key."""
        if k.startswith('--'):
            k = k[2:]
        if k.startswith('-'):
            k = k[1:]
        if k.startswith('<') and k.endswith('>'):
            k = k[1:-1]
        return k.lower().replace('-', '_')

    params = inspect.getargspec(func)[0]
    args = {}
    for k, v in cli_args.items():
        nk = _norm(k)
        if nk in params:
            args[nk] = v
    return args


def _get_entry_point():
    """Return the current entry point."""
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
    for ep in pkg_resources.iter_entry_points(group='docopt_sub'):
        if ep.name == _COMMAND:
            subcommands[None] = ep
        else:
            match = re.match(regex, ep.name)
            if match:
                subcommands[match.group('name')] = ep.load()
    return subcommands


def _get_subcommand(subcommand):
    """Return the function for the specified subcommand."""
    if subcommand not in _subcommands:
        raise ValueError(
            '"{subcommand}" is not a {command} command. \'{command} help -a\' '
            'lists all available subcommands.'.format(
                command=_COMMAND, subcommand=subcommand)
        )
    return _subcommands[subcommand]


def _run_command(argv):
    """Run the command with the the given CLI options and exit.

    Command functions are expected to have a __doc__ string that is parseable
    by docopt. If the the function object has a 'validate' attribute, the
    arguments passed to the command will be validated before the command is
    called.

    Args:
        argv: The list of command line arguments supplied for a command. The
            first argument is expected to be the name of the command to be run.
            Note that this is different than the full arguments parsed by
            docopt for the entire program.

    Raises:
        ValueError: Raised if the user attempted to run an invalid command.
    """
    command_name = argv[0]
    _logger.info('Running command "%s" with args: %s', command_name, argv[1:])
    subcommand = _get_subcommand(command_name)
    _logger.debug('Parsing docstring:%s\nwith arguments %s.',
                  subcommand.__doc__, argv)
    args = docopt(subcommand.__doc__, argv=argv)
    if hasattr(subcommand, 'validate'):
        _logger.debug('Validating command arguments with "%s".',
                      subcommand.validate)
        args.update(subcommand.validate(args))
    normalized_args = _normalize(args, subcommand)
    return subcommand(**normalized_args) or 0


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
        available_commands = (k for k in _subcommands.keys() if k)
        command_doc = '\nAvailable commands:\n{}\n'.format(
            '\n'.join('  {}'.format(c) for c in available_commands))
        doc = _DEFAULT_DOC.format(message=command_doc)
    elif command.startswith('-'):
        raise ValueError("Unrecognized option '{}'.".format(command))
    else:
        subcommand = _get_subcommand(command)
        doc = subcommand.__doc__
    docopt(doc, argv=('--help',))
