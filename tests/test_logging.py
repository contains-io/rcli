# -*- coding: utf-8 -*-
"""Tests that verify that logging works as expected."""

from __future__ import unicode_literals

import glob
import re
import subprocess
import time


_CTRL_CHAR = re.compile(r'(\x9B|\x1B\[)[0-?]*[ -/]*[@-~]')
_LOG = re.compile(
    r'(?P<level>[^\s]+)\s+\[.+\]\[(?P<logger>.+?)\]\s+(?P<log>.+)')


def test_log_levels(create_project, run):
    """Test that an invalid log level does not show an exception."""
    def _get_logs(command):
        output = _CTRL_CHAR.sub('', run(command, stderr=True))
        return [(m[0], m[2]) for m in _LOG.findall(output) if m[1] == 'root']

    with create_project('''
        import logging
        def log():
            """usage: say log"""
            logging.debug('DEBUG')
            logging.info('INFO')
            logging.warn('WARN')
            logging.error('ERROR')
    '''):
        expected_logs = [
            ('DEBUG', 'DEBUG'),
            ('INFO', 'INFO'),
            ('WARNING', 'WARN'),
            ('ERROR', 'ERROR'),
        ]
        assert _get_logs('say -d log') == expected_logs
        assert _get_logs('say --debug log') == expected_logs
        assert _get_logs('say --log-level DEBUG log') == expected_logs
        assert _get_logs('say -v log') == expected_logs[1:]
        assert _get_logs('say --verbose log') == expected_logs[1:]
        assert _get_logs('say --log-level INFO log') == expected_logs[1:]
        assert _get_logs('say --log-level WARN log') == expected_logs[2:]
        assert _get_logs('say --log-level ERROR log') == expected_logs[3:]


def test_invalid_log_level(create_project, run):
    """Test that an invalid log level does not show an exception."""
    with create_project('''
        def log():
            """usage: say log"""
    '''):
        assert run('say --log-level INVALID log', stderr=True) == (
            'Invalid value "INVALID" supplied to --log-level. Valid '
            'options are: DEBUG, INFO, WARN, ERROR\n'
        )


def test_exception_log(create_project, run):
    """Verify that a log file is written out in the case of an exception."""
    with create_project('''
        import logging

        def nothing():
            """usage: say nothing"""
            logging.debug('DEBUG')
            raise RuntimeError

        def error():
            """usage: say error"""
            logging.debug('DEBUG')
            raise RuntimeError('Error')
    ''') as project:
        assert run('say nothing', stderr=True) == (
            'Please see the log file for more information.\n'
        )
        assert run('say error', stderr=True) == (
            'Error\n'
            'Please see the log file for more information.\n'
        )
        logs = glob.glob(str(project / r'say*.log'))
        assert logs
        for log in logs:
            with open(log) as log_file:
                contents = log_file.read()
                assert 'DEBUG' in contents
                assert 'ERROR' in contents


def test_sigterm_log(create_project):
    """Test that a log file is generated when a SIGTERM is received."""
    with create_project('''
        import sys
        import time

        def nothing():
            """usage: say nothing"""
            print('ready')
            sys.stdout.flush()
            while 1:
                time.sleep(1)
    ''') as project:
        process = subprocess.Popen(
            ['say', 'nothing'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)
        end = time.time() + 30
        try:
            while 'ready' not in process.stdout.read(5) and time.time() < end:
                pass
            process.terminate()
            assert process.wait()
        finally:
            process.stdout.close()
            process.stderr.close()
        logs = glob.glob(str(project / r'say*.log'))
        assert logs
        for log in logs:
            with open(log) as log_file:
                contents = log_file.read()
                assert 'DEBUG' in contents
                assert 'ERROR' in contents


def test_sigterm_no_log(create_project):
    """Test that a log file is not generated when a SIGTERM handler exists."""
    with create_project('''
        import signal
        import sys
        import time

        signal.signal(signal.SIGTERM, lambda *_: sys.exit(signal.SIGTERM))

        def nothing():
            """usage: say nothing"""
            print('ready')
            sys.stdout.flush()
            while 1:
                time.sleep(1)
    ''') as project:
        process = subprocess.Popen(
            ['say', 'nothing'], stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, universal_newlines=True)
        end = time.time() + 30
        try:
            while 'ready' not in process.stdout.read(5) and time.time() < end:
                pass
            process.terminate()
            assert process.wait()
        finally:
            process.stdout.close()
            process.stderr.close()
        logs = glob.glob(str(project / r'say*.log'))
        assert not logs
