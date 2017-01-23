#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Install rcli."""

from __future__ import unicode_literals

from setuptools import setup
from setuptools import find_packages

import rcli


setup(
    name='rcli',
    version=rcli.__version__,
    description='A library for rapidly creating command-line tools.',
    long_description=open('README.rst').read(),
    author='Dangle Nuño',
    author_email='dangle@rooph.io',
    url='https://github.com/containenv/rcli',
    keywords=['docopt', 'commands', 'subcommands', 'tooling', 'cli'],
    license='MIT',
    packages=find_packages(exclude=['tests', 'docs']),
    install_requires=[
        'colorama >= 0.3.6, < 1',
        'tqdm >= 4.9.0, < 5',
        'docopt >= 0.6.2, < 1',
        'six >= 1, < 2',
        'backports.shutil_get_terminal_size'
    ],
    setup_requires=['pytest-runner'],
    tests_require=['pytest >= 2.9'],
    entry_points={
        'distutils.setup_keywords': [
            'autodetect_commands = rcli.autodetect:setup_keyword'
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Intended Audience :: Developers',
        'Topic :: Utilities'
    ]
)
