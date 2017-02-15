# -*- coding: utf-8 -*-
"""A settings object for all information related to the command.

Functions:
    settings: An object that contains all information related to the current
        command and configuration of rcli.
"""

from __future__ import unicode_literals

import copy
import logging
import json
import os.path
import re
import sys

import pkg_resources
import six


_LOGGER = logging.getLogger(__name__)


class _Singleton(type):
    """A metaclass to turn a class into a singleton."""

    __instance__ = None

    def __call__(cls, *args, **kwargs):
        """Instantiate the class only once."""
        if not cls.__instance__:
            cls.__instance__ = super(_Singleton, cls).__call__(*args, **kwargs)
        return cls.__instance__


@six.add_metaclass(_Singleton)
class _RcliConfig(object):
    """A global settings object for the command and the configuration."""

    _EP_MOD_NAME = 'rcli.dispatcher'  # The console script entry point module.

    def __init__(self):
        self._command = None
        self._subcommands = {}
        self._version = None
        self._entry_point = None
        self._config = {}
        if (self.distribution and
                self.distribution.has_metadata('rcli-config.json')):
            data = self.distribution.get_metadata('rcli-config.json')
            self._config = json.loads(data)

    @property
    def command(self):
        """The name of the active command."""
        if not self._command:
            self._command = os.path.basename(
                os.path.realpath(os.path.abspath(sys.argv[0])))
        return self._command

    @property
    def subcommands(self):
        """A mapping of subcommand names to loaded entry point targets."""
        if not self._subcommands:
            regex = re.compile(r'{}:(?P<name>[^:]+)$'.format(self.command))
            for ep in pkg_resources.iter_entry_points(group='rcli'):
                try:
                    if ep.name == self.command:
                        self._subcommands[None] = ep.load()
                    else:
                        match = re.match(regex, ep.name)
                        if match:
                            self._subcommands[match.group('name')] = ep.load()
                except ImportError:
                    _LOGGER.exception('Unable to load command. Skipping.')
        return self._subcommands

    @property
    def version(self):
        """The version defined in the distribution."""
        if not self._version:
            if hasattr(self.distribution, 'version'):
                self._version = str(self.distribution)
        return self._version

    @property
    def entry_point(self):
        """The currently active entry point."""
        if not self._entry_point:
            for ep in pkg_resources.iter_entry_points(group='console_scripts'):
                if (ep.name == self.command and
                        ep.module_name == self._EP_MOD_NAME):
                    self._entry_point = ep
        return self._entry_point

    @property
    def distribution(self):
        """The distribution containing the currently active entry point."""
        if self.entry_point:
            return self.entry_point.dist

    def __getattr__(self, attr):
        """Return the rcli setting by name.

        Args:
            attr: The name of the setting attribute to retrieve.

        Returns:
            The value of the setting if it is set; otherwise, None.
        """
        return copy.deepcopy(self._config.get(attr))


settings = _RcliConfig()
