# -*- coding: utf-8 -*-
"""Utility methods for working with the CLI.

Classes:
    Status: A special exception that will set a status message.

Functions:
    hidden_cursor: A context manager that will hide the terminal cursor and
        show it once the context is over.
    display_status: A context manager that will watch for exceptions and print
        a six character status message of either [  OK  ], [FAILED], or a
        custom status.
    timed_display: A context manager that prints a header line, a group of
        status messages, and finally, a footer line with the length of time
        taken to complete the block.
    run_tasks: A function that takes a list of callables as tasks and prints
        a header, status messages for each task, and creates a progress bar
        to show how much remains to be done.
"""

from __future__ import print_function
from __future__ import unicode_literals

import contextlib
import logging
import sys
import time

from colorama import (
    Cursor,
    Fore,
    Style
)
from tqdm import tqdm

try:
    from shutil import get_terminal_size  # type: ignore
except ImportError:
    from backports.shutil_get_terminal_size import (  # type: ignore
        get_terminal_size
    )


_LOGGER = logging.getLogger(__name__)


class Status(Exception):
    """A special exception that will alter the default task display."""

    def __init__(self, message, color, exc=None):
        """Initialize the exception.

        Args:
            message: A six character status message to display on the terminal.
            color: An ANSI color code value to use while displaying the
                message.
            exc: An exception that caused the non-standard status message. If
                exc is supplied, it will be raised after the status message is
                displayed.
        """
        super(Status, self).__init__()
        self.msg = message
        self.color = color
        self.exc = exc


@contextlib.contextmanager
def hidden_cursor():
    """Temporarily hide the terminal cursor."""
    if sys.stdout.isatty():
        _LOGGER.debug('Hiding cursor.')
        print('\x1B[?25l', end='')
        sys.stdout.flush()
    try:
        yield
    finally:
        if sys.stdout.isatty():
            _LOGGER.debug('Showing cursor.')
            print('\n\x1B[?25h', end='')
            sys.stdout.flush()


@contextlib.contextmanager
def display_status():
    """Display an OK or FAILED message for the context block."""
    def print_status(msg, color):
        """Print the status message.

        Args:
            msg: The message to display (e.g. OK or FAILED).
            color: The ANSI color code to use in displaying the message.
        """
        print('\r' if sys.stdout.isatty() else '\t', end='')
        print('{}{}[{color}{msg}{}]{}'.format(
            Cursor.FORWARD(_ncols() - 8),
            Style.BRIGHT,
            Fore.RESET,
            Style.RESET_ALL,
            color=color,
            msg=msg[:6].upper().center(6)
        ))
        sys.stdout.flush()

    try:
        yield
    except Status as e:
        _LOGGER.debug(e)
        print_status(e.msg, e.color)
        if e.exc:
            raise e.exc  # pylint: disable=raising-bad-type
    except (KeyboardInterrupt, EOFError):
        raise
    except:
        print_status('FAILED', Fore.RED)
        raise
    else:
        print_status('OK', Fore.GREEN)


@contextlib.contextmanager
def timed_display(msg):
    """A timed block to run tasks with titles and success/failure messages.

    Args:
        msg: The header message to print at the beginning of the timed block.
    """
    def print_header(msg, newline=True):
        """Print a header line.

        Args:
            msg: A message to be printed in the center of the header line.
            newline: Whether or not to print a newline at the end of the
                header. This can be convenient for allowing the line to
                overwrite another.
        """
        if sys.stdout.isatty():
            print('\r', end=Style.BRIGHT + Fore.BLUE)
        print(' {} '.format(msg).center(_ncols(), '='),
              end='\n{}'.format(Style.RESET_ALL)
              if newline else Style.RESET_ALL)
        sys.stdout.flush()

    def print_message(msg):
        """Print a task title message.

        Args:
            msg: The message to display before running the task.
        """
        if sys.stdout.isatty():
            print('\r', end='')
            msg = msg.ljust(_ncols())
        print(msg, end='')
        sys.stdout.flush()

    start = time.time()
    print_header(msg)
    with hidden_cursor():
        try:
            yield print_message
        finally:
            delta = time.time() - start
            print_header('completed in {:.2f}s'.format(delta), False)


def run_tasks(header, tasks):
    """Run a group of tasks with a header, footer and success/failure messages.

    Args:
        header: A message to print in the header bar before the tasks are run.
        tasks: A list of tuples containing a task title, a task, and a weight.
            If the tuple only contains two values, the weight is assumed to be
            one.
    """
    tasks = list(tasks)
    with timed_display(header) as print_message:
        with tqdm(tasks, position=1, desc='Progress', disable=None,
                  bar_format='{desc}{percentage:3.0f}% |{bar}|',
                  total=sum(t[2] if len(t) > 2 else 1 for t in tasks),
                  dynamic_ncols=True) as pbar:
            for task in tasks:
                print_message(task[0])
                with display_status():
                    try:
                        task[1]()
                    finally:
                        pbar.update(task[2] if len(task) > 2 else 1)


def _ncols():
    """Get the current number of columns on the terminal.

    Returns:
        The current number of columns in the terminal or 80 if there is no tty.
    """
    return get_terminal_size().columns or 80
