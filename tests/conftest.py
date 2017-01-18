# -*- coding: utf-8 -*-
"""Common fixtures for test suites.

Functions:
    create_project: A factory that creates a project structure and installs it.
    run: A wrapper around subprocess.check_output to handle common
        functionality.
    id_: A unique 24 character ID that can be used in a test.
"""

from __future__ import unicode_literals

import contextlib
import random
import string
import subprocess
import sys
import textwrap

import pytest


@pytest.fixture(scope='function')
def create_project(tmpdir, id_):
    """Function factory to create context managers that create python projects.

    Args:
        tmpdir: pytest fixture to create a temporary directory.

    Returns:
        A factory function that will create the folder structure, setup.py and
        the initial package code for a command program.
    """
    @contextlib.contextmanager
    def _install_project(code, setup_keys=None, autodetect=True):
        """Create a new Python project using rapcom.

        Generates a random name for the project and creates a setup.py file and
        a package with the same name as the project.

        After the control returns to the context manager, the project will be
        uninstalled.

        Args:
            code: The code for the __init__.py module. It will be dedented.
            setup_keys: A string that will be added to the setup call in
                setup.py.
            autodetect: Whether or not to run command autodetection on the
                newly created project at setup.

        Returns:
            A py.path.local object representing the newly created project
            folder.
        """
        project_name = id_
        project = tmpdir.mkdir(project_name)
        setup = project.join('setup.py')
        setup.write(
            textwrap.dedent(
                """
                from setuptools import setup, find_packages

                setup(
                    name='{name}',
                    version='1.0.0',
                    packages=find_packages(),
                    install_requires=['rapcom'],
                    setup_requires=['rapcom'],
                    autodetect_commands={autodetect},
                    {keys}
                )
                """.format(
                    name=project_name,
                    autodetect=autodetect,
                    keys=setup_keys or ''
                )
            )
        )
        project.mkdir(project_name).join('__init__.py').write(textwrap.dedent(
            code))
        subprocess.check_call(['pip', 'install', str(project)])
        try:
            yield project
        finally:
            subprocess.check_call(['pip', 'uninstall', id_, '-y'])
    return _install_project


@pytest.fixture(scope='session')
def run():
    """Function factory to create subprocess wrappers functions.

    Returns:
        A function that wraps subprocess.check_output, splits the input
        command, and decodes the output using the system encoding.
    """
    def _inner(command, stderr=False):
        """Run the given command and decode the output.

        Args:
            command: The command string to run on the system. It will be split
                and executed using the subprocess module.

        Returns:
            The output of the subprocess call decoded using the system
            encoding.

        Raises:
            CalledProcessError: Raised when the command returns a non-zero exit
                code.
        """
        try:
            output = subprocess.check_output(
                command.split(), stderr=subprocess.STDOUT if stderr else None)
        except subprocess.CalledProcessError as e:
            output = e.output
        return output.decode(sys.stdout.encoding)
    return _inner


@pytest.fixture(scope='function')
def id_():
    """Return a 24 character ID consisting of letters and digits."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(24))
