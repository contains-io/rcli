# -*- coding: utf-8 -*-
"""An automatic command that handles subcommand dispatch."""


class RapcomError(Exception):
    """An error detected in the use of rapcom."""


class InvalidCliValueError(RapcomError, ValueError):
    """An error in a CLI error to a rapcom option."""

    def __init__(self, parameter, value, valid_values=None):
        """Instantiate the exception with a descriptive message."""
        msg = 'Invalid value "{value}" supplied to {parameter}.'.format(
            parameter=parameter, value=value)
        if valid_values:
            msg += ' Valid options are: {}'.format(', '.join(valid_values))
        super(InvalidCliValueError, self).__init__(msg)


class InvalidLogLevelError(InvalidCliValueError):
    """An invalid logging level passed on the CLI."""

    def __init__(self, log_level):
        """Instantiate the exception with a descriptive message."""
        super(InvalidLogLevelError, self).__init__(
            '--log-level', log_level, ('DEBUG', 'INFO', 'WARN', 'ERROR')
        )
