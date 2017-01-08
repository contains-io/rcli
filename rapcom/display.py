# -*- coding: utf-8 -*-
"""Utility methods for working with the CLI."""

from __future__ import unicode_literals

import contextlib
import logging
import subprocess
import sys
import time

from colorama import Cursor
from colorama import Fore
from colorama import Style
from tqdm import tqdm


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
    _LOGGER.debug('Hiding cursor.')
    tqdm.write('\x1B[?25l', end='')
    sys.stdout.flush()
    try:
        yield
    finally:
        _LOGGER.debug('Showing cursor.')
        tqdm.write('\n\x1B[?25h', end='')
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
        tqdm.write('\r{}{}[{color}{msg}{}]{}'.format(
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
        tqdm.write('\r', end=Style.BRIGHT + Fore.BLUE)
        tqdm.write(' {} '.format(msg).center(_ncols(), '='),
                   end='\n{}'.format(Style.RESET_ALL)
                   if newline else Style.RESET_ALL)
        sys.stdout.flush()

    def print_message(msg):
        """Print a task title message.

        Args:
            msg: The message to display before running the task.
        """
        tqdm.write('\r{}'.format(msg), end='')
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
        with tqdm(tasks, file=sys.stdout, position=1, desc='Progress',
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

    It first attempts to use the Python 3 method for retrieving column size. If
    that fails, it looks for the Python 2 backport of the Python 3 method.
    Failing that, it attempts to call out to the operating system to retrive
    the current number of columns. If all else fails, it assumes a width of 80.

    Returns:
        The current number of columns in the terminal, or 80 if unable to
        detect the current number of columns.
    """
    try:
        import shutils
        return shutils.get_terminal_size().columns
    except ImportError:
        pass
    try:
        import backports.shutil_get_terminal_size
        return backports.shutil_get_terminal_size.get_terminal_size().columns
    except ImportError:
        pass
    try:
        return int(subprocess.check_output(['stty', 'size']).split()[1])
    except (subprocess.CalledProcessError, ValueError, IndexError):
        return 80
