# -*- coding: utf-8 -*-
"""Utilities for handling global logging state.

Functions:
    write_logfile: Write the current contents of the DEBUG log to a file.
    handle_unexpected_exception: Log and append the exception message with a
        message indicating that logging occurred.
    enable_logging: Configures logging handlers and formatters.
    get_log_level: Parse a docopt dictionary of parsed values to retrieve the
        log level passed in by the user on the command line.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import logging
import os.path
import signal
import sys
import typing  # noqa: F401 pylint: disable=unused-import

import colorama
import six

from . import exceptions as exc


_LOGFILE_STREAM = six.StringIO()


def write_logfile():
    # type: () -> None
    """Write a DEBUG log file COMMAND-YYYYMMDD-HHMMSS.ffffff.log."""
    command = os.path.basename(os.path.realpath(os.path.abspath(sys.argv[0])))
    now = datetime.datetime.now().strftime('%Y%m%d-%H%M%S.%f')
    filename = '{}-{}.log'.format(command, now)
    with open(filename, 'w') as logfile:
        logfile.write(_LOGFILE_STREAM.getvalue())


def handle_unexpected_exception(exc):
    # type: (Exception) -> typing.Union[str, Exception]
    """Return an error message and write a log file if logging was not enabled.

    Args:
        exc: The unexpected exception.

    Returns:
        A message to display to the user concerning the unexpected exception.
    """
    try:
        write_logfile()
        addendum = 'Please see the log file for more information.'
    except IOError:
        addendum = 'Unable to write log file.'
    try:
        message = str(exc)
        return '{}{}{}'.format(message, '\n' if message else '', addendum)
    except Exception:  # pylint: disable=broad-except
        return exc


def enable_logging(log_level):
    # type: (typing.Union[None, int]) -> None
    """Configure the root logger and a logfile handler.

    Args:
        log_level: The logging level to set the logger handler.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    logfile_handler = logging.StreamHandler(_LOGFILE_STREAM)
    logfile_handler.setLevel(logging.DEBUG)
    logfile_handler.setFormatter(logging.Formatter(
        '%(levelname)s [%(asctime)s][%(name)s] %(message)s'))
    root_logger.addHandler(logfile_handler)
    if signal.getsignal(signal.SIGTERM) == signal.SIG_DFL:
        signal.signal(signal.SIGTERM, _logfile_sigterm_handler)
    if log_level:
        handler = logging.StreamHandler()
        handler.setFormatter(_LogColorFormatter())
        root_logger.setLevel(log_level)
        root_logger.addHandler(handler)


def get_log_level(args):
    # type: (typing.Dict[str, typing.Any]) -> int
    """Get the log level from the CLI arguments.

    Removes logging arguments from sys.argv.

    Args:
        args: The parsed docopt arguments to be used to determine the logging
            level.

    Returns:
        The correct log level based on the three CLI arguments given.

    Raises:
        ValueError: Raised if the given log level is not in the acceptable
            list of values.
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
    if log_level not in (None, 'DEBUG', 'INFO', 'WARN', 'ERROR'):
        raise exc.InvalidLogLevelError(log_level)
    return getattr(logging, log_level) if log_level else None


def _logfile_sigterm_handler(*_):
    # type: (...) -> None
    """Handle exit signals and write out a log file.

    Raises:
        SystemExit: Contains the signal as the return code.
    """
    logging.error('Received SIGTERM.')
    write_logfile()
    print('Received signal. Please see the log file for more information.',
          file=sys.stderr)
    sys.exit(signal)


class _LogColorFormatter(logging.Formatter):
    """A colored logging.Formatter implementation."""

    def format(self, record):
        # type: (logging.LogRecord) -> str
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
