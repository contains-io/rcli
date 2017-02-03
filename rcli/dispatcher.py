# -*- coding: utf-8 -*-
"""An automatic command that handles subcommand dispatch.

Functions:
    main: The console script entry point set by autodetected CLI scripts.
"""

from __future__ import unicode_literals

import datetime
import inspect
import logging
import os.path
import re
import sys
import types

from docopt import docopt
import colorama
import pkg_resources
import six

from . import exceptions as exc


_LOGGER = logging.getLogger(__name__)


_COMMAND = os.path.basename(os.path.realpath(os.path.abspath(sys.argv[0])))
_SUBCOMMANDS = {}
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
""".format(command=_COMMAND)


def main():
    """Parse the command line options and launch the requested command.

    If the command is 'help' then print the help message for the subcommand; if
    no subcommand is given, print the standard help message.
    """
    colorama.init(wrap=six.PY3)
    _SUBCOMMANDS.update(_get_subcommands())
    dist_version = _get_dist_version()
    if None not in _SUBCOMMANDS:
        doc = _DEFAULT_DOC.format(message='')
    else:
        doc = _SUBCOMMANDS[None].__doc__
    doc = _get_usage(doc)
    allow_subcommands = '<command>' in doc
    args = docopt(doc, version=dist_version, options_first=allow_subcommands)
    log_level = _get_log_level(args)
    log_stream = six.StringIO()
    try:
        _enable_logging(log_level, log_stream)
        default_args = sys.argv[2 if args.get('<command>') else 1:]
        if args.get('<command>') == 'help':
            subcommand = next(iter(args.get('<args>', default_args)), None)
            return _help(subcommand)
        else:
            argv = [args.get('<command>')] + args.get('<args>', default_args)
            return _run_command(argv)
    except exc.InvalidCliValueError as e:
        return e
    except (KeyboardInterrupt, EOFError):
        return "Cancelling at the user's request."
    except Exception as e:  # pylint: disable=broad-except
        return _handle_unexpected_exception(e, log_stream)


def _handle_unexpected_exception(exc, log_stream):
    """Return an error message and write a log file if logging was not enabled.

    Args:
        exc: The unexpected exception.
        log_stream: The accumulated log data to write to a file if logging was
            not explicitly enabled.

    Returns:
        A message to display to the user concerning the unexpected exception.
    """
    _LOGGER.exception('An unexpected error has occurred.')
    msg = str(exc)
    if msg:
        msg += '\n'
    try:
        now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S.%f')
        filename = '{}-{}.log'.format(_COMMAND, now)
        with open(filename, 'w') as log_file:
            log_file.write(log_stream.getvalue())
        msg += 'Please see the log file for more information.'
    except IOError:
        msg += 'Unable to write log file.'
    return msg


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

    assert hasattr(func, '__call__'), (
        'Cannot normalize parameters of a non-callable.')
    is_func = isinstance(func, types.FunctionType)
    params = _get_signature(func if is_func else func.__call__)
    _LOGGER.debug('Found signature parameters: %s', params)
    args = {}
    multi_args = set()
    for k, v in six.iteritems(cli_args):
        nk = _norm(k)
        if nk in params:
            if nk not in args or args[nk] is None:
                args[nk] = v
            elif nk in multi_args and v is not None:
                args[nk].append(v)
            elif v is not None:
                multi_args.add(nk)
                args[nk] = [args[nk], v]
    _LOGGER.debug('Normalized "%s" to "%s".', cli_args, args)
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
    sig = inspect.getargspec(func).args  # pylint: disable=deprecated-method
    if six.PY2 and isinstance(func, types.MethodType):
        sig = sig[1:]
    return sig


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
    for ep in pkg_resources.iter_entry_points(group='rcli'):
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
    """Run the command with the given CLI options and exit.

    Command functions are expected to have a __doc__ string that is parseable
    by docopt.

    If the function object has a 'validate' attribute, the
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
        subcommands = [k for k in _SUBCOMMANDS.keys() if k is not None]
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
    """Format the docstring for display to the user.

    Args:
        doc: The docstring to reformat for display.

    Returns:
        The docstring formatted to parse and display to the user. This includes
        dedenting, rewrapping, and translating the docstring if necessary.
    """
    return inspect.cleandoc(doc)


def _enable_logging(log_level, log_stream):
    """Set the root logger to the given log level and add a color formatter.

    Args:
        log_level: The logging level to set the root logger. Must be None,
            "DEBUG", "INFO", "WARN", or "ERROR".
        log_stream: A stream object to write logs to in addition to stderr.
            This is to be used to save the logs in the case of an unexpected
            exception.

    Raises:
        ValueError: Raised if the given log level is not in the acceptable
            list of values.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(log_stream)
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(logging.Formatter(
        '%(levelname)s [%(asctime)s][%(name)s] %(message)s'))
    root_logger.addHandler(stream_handler)
    if log_level not in (None, 'DEBUG', 'INFO', 'WARN', 'ERROR'):
        raise exc.InvalidLogLevelError(log_level)
    if log_level:
        handler = logging.StreamHandler()
        handler.setFormatter(_LogColorFormatter())
        level = getattr(logging, log_level)
        root_logger.setLevel(level)
        root_logger.addHandler(handler)


def _get_log_level(args):
    """Get the log level from the CLI arguments.

    Removes logging arguments from sys.argv.

    Args:
        args: The parsed docopt arguments to be used to determine the logging
            level.

    Returns:
        The correct log level based on the three CLI arguments given.
    """
    index = -1
    log_level = None
    if '<command>' in args and args['<command>']:
        index = sys.argv.index(args['<command>'])
    if args.get('--debug'):
        log_level = 'DEBUG'
        if '--debug' in sys.argv and sys.argv.index('--debug') < index:
            sys.argv.remove('--debug')
        elif '-d' in sys.argv and sys.argv.index('-d') < index:
            sys.argv.remove('-d')
    elif args.get('--verbose'):
        log_level = 'INFO'
        if '--verbose' in sys.argv and sys.argv.index('--verbose') < index:
            sys.argv.remove('--verbose')
        elif '-v' in sys.argv and sys.argv.index('-v') < index:
            sys.argv.remove('-v')
    elif args.get('--log-level'):
        log_level = args['--log-level']
        sys.argv.remove('--log-level')
        sys.argv.remove(log_level)
    return log_level


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
        format_template = (
            '{}{}%(levelname)s{} [%(asctime)s][%(name)s]{} %(message)s')
        if sys.stdout.isatty():
            self._fmt = format_template.format(
                colorama.Style.BRIGHT,
                color,
                colorama.Fore.RESET,
                colorama.Style.RESET_ALL
            )
        else:
            self._fmt = format_template.format(*[''] * 4)
        if six.PY3:
            self._style._fmt = self._fmt  # pylint: disable=protected-access
        return super(_LogColorFormatter, self).format(record)
