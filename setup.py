#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Install rcli and rcli distutils extensions."""

from __future__ import unicode_literals

import os.path
import shutil

from setuptools import setup
from setuptools import find_packages


if os.path.isdir('rcli.egg-info'):
    try:
        shutil.rmtree('rcli.egg-info')
    except IOError:
        pass

with open('README.rst') as readme_fp:
    readme = readme_fp.read()

common_requires = ['docopt >= 0.6.2, < 1',
                   'six >= 1.10.0']
setup(
    name='rcli',
    use_scm_version=True,
    description='A library for rapidly creating command-line tools.',
    long_description=readme,
    author='Melissa Nuno',
    author_email='melissa@contains.io',
    url='https://github.com/contains-io/rcli',
    keywords=['docopt', 'commands', 'subcommands', 'tooling', 'cli'],
    license='MIT',
    packages=find_packages(exclude=['tests', 'docs']),
    install_requires=[
        'typet >= 0.4, < 0.5',
        'backports.shutil_get_terminal_size',
        'colorama >= 0.3.6, < 1',
        'tqdm >= 4.9.0, < 5'
    ] + common_requires,
    setup_requires=[
        'packaging',
        'appdirs',
        'pytest-runner',
        'setuptools_scm'
    ] + common_requires,
    tests_require=[
        'pytest >= 3.0'
    ],
    entry_points={
        'distutils.setup_keywords': [
            'autodetect_commands = rcli.autodetect:setup_keyword'
        ],
        'egg_info.writers': [
            'rcli-config.json = rcli.autodetect:egg_info_writer'
        ]
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Intended Audience :: Developers',
        'Topic :: Utilities'
    ]
)
