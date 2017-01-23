# -*- coding: utf-8 -*-
"""Exceptions that can be raised by rcli.

Classes:
    RcliError: The base exception for all exceptions used by rcli.
    InvalidCliValueError: An exception that is used to tell the user of the
        CLI application that they have passed an invalid value to a parameter.
    InvalidLogLevelError: A subclass of InvalidCliValueError specifically for
        dealing with invalid log level values.
"""


class RcliError(Exception):
    """An error detected in the use of rcli."""


class InvalidCliValueError(RcliError, ValueError):
    """An error in a CLI error to a rcli option."""

    def __init__(self, parameter, value, valid_values=None):
        """Instantiate the exception with a descriptive message.

        Args:
            parameter: The CLI parameter with the invalid value.
            value: The invalid value passed to the CLI parameter.
            valid_values: The values that would have been accepted by the
                parameter.
        """
        msg = 'Invalid value "{value}" supplied to {parameter}.'.format(
            parameter=parameter, value=value)
        if valid_values:
            msg += ' Valid options are: {}'.format(', '.join(valid_values))
        super(InvalidCliValueError, self).__init__(msg)


class InvalidLogLevelError(InvalidCliValueError):
    """An invalid logging level passed on the CLI."""

    def __init__(self, log_level):
        """Instantiate the exception with a descriptive message.

        Args:
            log_level: The invalid value passed as the log level.
        """
        super(InvalidLogLevelError, self).__init__(
            '--log-level', log_level, ('DEBUG', 'INFO', 'WARN', 'ERROR')
        )
