# -*- coding: utf-8 -*-
"""A settings object for all information related to the command.

Functions:
    settings: An object that contains all information related to the current
        command and configuration of rcli.

Classes:
    RcliEntryPoint: The allowed entry point types for subcommands.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

import copy
import logging
import json
import os.path
import re
import sys
import types
import typing

import pkg_resources
import setuptools  # noqa: F401 pylint: disable=unused-import
import six

from .typing import Singleton


_LOGGER = logging.getLogger(__name__)

RcliEntryPoint = typing.Union[types.FunctionType, type, types.ModuleType]


@six.add_metaclass(Singleton)
class _RcliConfig(object):
    """A global settings object for the command and the configuration."""

    _EP_MOD_NAME = 'rcli.dispatcher'  # The console script entry point module.

    def __init__(self):
        # type: () -> None
        """Initialize the data for the configuration."""
        self._command = None  # type: str
        self._subcommands = {}  # type: typing.Dict[str, RcliEntryPoint]
        self._version = None  # type: str
        self._entry_point = None  # type: pkg_resources.EntryPoint
        self._config = {}  # type: typing.Dict[str, typing.Any]
        if (self.distribution and
                self.distribution.has_metadata('rcli-config.json')):
            data = self.distribution.get_metadata('rcli-config.json')
            self._config = json.loads(data)

    @property
    def command(self):
        # type: () -> str
        """The name of the active command."""
        if not self._command:
            self._command = os.path.basename(
                os.path.realpath(os.path.abspath(sys.argv[0])))
        return self._command

    @property
    def subcommands(self):
        # type: () -> typing.Dict[str, RcliEntryPoint]
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
        # type: () -> str
        """The version defined in the distribution."""
        if not self._version:
            if hasattr(self.distribution, 'version'):
                self._version = str(self.distribution)
        return self._version

    @property
    def entry_point(self):
        # type: () -> pkg_resources.EntryPoint
        """The currently active entry point."""
        if not self._entry_point:
            for ep in pkg_resources.iter_entry_points(group='console_scripts'):
                if (ep.name == self.command and
                        ep.module_name == self._EP_MOD_NAME):
                    self._entry_point = ep
        return self._entry_point

    @property
    def distribution(self):
        # type: () -> typing.Optional[setuptools.dist.Distribution]
        """The distribution containing the currently active entry point."""
        if self.entry_point:
            return self.entry_point.dist

    def __getattr__(self, attr):
        # type: (str) -> typing.Any
        """Return the rcli setting by name.

        Args:
            attr: The name of the setting attribute to retrieve.

        Returns:
            The value of the setting if it is set; otherwise, None.
        """
        return copy.deepcopy(self._config.get(attr))


settings = _RcliConfig()
