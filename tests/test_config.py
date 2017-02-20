# -*- coding: utf-8 -*-
"""Tests for the rcli configuration object."""

from __future__ import unicode_literals

import json
import os.path

from rcli.config import _RcliConfig as Config
from rcli.config import settings


def test_settings_singleton():
    """Assert that the settings object is a singleton."""
    assert Config() is Config() and Config() is settings


def test_settings(create_project, run):
    """Test that the settings object has all the expected attributes."""
    with create_project('''
        import json

        from rcli.config import settings

        def check_settings():
            """usage: say settings"""
            config = settings._config
            config['command'] = settings.command
            config['subcommands'] = list(settings.subcommands.keys())
            config['entry_point'] = settings.entry_point.name
            config['version'] = settings.version
            print(json.dumps(config))
    ''', '''
        [rcli]
        message = I'm a little teapot.
        not_true = False
        not_false = True
        some_list = ["a", "b", 3]
        seventeen = 17
        sevenstring = "7"
    ''') as project:
        settings = json.loads(run('say settings'))
        assert len(settings) == 10
        assert settings['command'] == 'say'
        assert 'settings' in settings['subcommands']
        assert settings['entry_point'] == 'say'
        assert settings['version'] == '{} 1.0.0'.format(
            os.path.basename(str(project)))
        assert settings['not_true'] is False
        assert settings['not_false'] is True
        assert settings['some_list'] == ['a', 'b', 3]
        assert settings['seventeen'] == 17
        assert settings['sevenstring'] == "7"


def test_message(create_project, run):
    """Test that a configured message is added to the help message."""
    with create_project('''
        from rcli.config import settings

        def check_settings():
            """usage: say settings"""
    ''', '''
        [rcli]
        message = I'm a little teapot.
    '''):
        assert "I'm a little teapot." in run('say -h')
