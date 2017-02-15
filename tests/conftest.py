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
import inspect
import os
import random
import shlex
import string
import subprocess
import sys
import textwrap

import pytest


@pytest.fixture(scope='function')
def create_project(tmpdir):
    """Function factory to create context managers that create python projects.

    Args:
        tmpdir: pytest fixture to create a temporary directory.

    Returns:
        A factory function that will create the folder structure, setup.py and
        the initial package code for a command program.
    """
    @contextlib.contextmanager
    def _install_project(code, setupcfg=None):
        """Create a new Python project using rcli.

        Generates a random name for the project and creates a setup.py file and
        a package with the same name as the project.

        After the control returns to the context manager, the project will be
        uninstalled.

        Args:
            code: The code for the __init__.py module. It will be dedented.

        Returns:
            A py.path.local object representing the newly created project
            folder.
        """
        project_name = id_()
        project = tmpdir.mkdir(project_name)
        if setupcfg:
            project.join('setup.cfg').write(inspect.cleandoc(setupcfg))
        setup = project.join('setup.py')
        setup.write(
            textwrap.dedent(
                """
                from setuptools import setup, find_packages

                setup(
                    name='{name}',
                    version='1.0.0',
                    packages=find_packages(),
                    install_requires=['rcli'],
                    setup_requires=['rcli'],
                    autodetect_commands=True
                )
                """.format(name=project_name)
            )
        )
        project.mkdir(project_name).join('__init__.py').write(textwrap.dedent(
            code))
        prevdir = os.getcwd()
        os.chdir(os.path.expanduser(str(project)))
        subprocess.check_call(['pip', 'install', '.'])
        try:
            yield project
        finally:
            subprocess.call(['pip', 'uninstall', project_name, '-y'])
            os.chdir(prevdir)
    return _install_project


@pytest.fixture(scope='session')
def run():
    """Function factory to create subprocess wrapper functions.

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
        """
        try:
            output = subprocess.check_output(
                shlex.split(command),
                stderr=subprocess.STDOUT if stderr else None)
        except subprocess.CalledProcessError as e:
            output = e.output
        return output.decode(sys.stdout.encoding)
    return _inner


@pytest.fixture(scope='function')
def id_():
    """Return a 24 character ID consisting of letters and digits."""
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(24))
