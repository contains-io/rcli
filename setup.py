#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Install rapcom."""

from __future__ import unicode_literals

from setuptools import setup
from setuptools import find_packages

import rapcom


setup(
    name='rapcom',
    version=rapcom.__version__,
    description='A library for rapidly creating command-line tools.',
    long_description=open('README.md').read(),
    author='Dangle Nuño',
    author_email='dangle@rooph.io',
    url='https://github.com/dangle/rapcom',
    keywords=['docopt', 'commands', 'subcommands'],
    license='MIT',
    packages=find_packages(exclude=['tests', 'docs']),
    install_requires=[
        'colorama >= 0.3.7, < 0.4',
        'tqdm >= 4.8.0, < 5',
        'docopt >= 0.6.2, < 1'
    ],
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Intended Audience :: Developers',
        'Topic :: Utilities'
    ]
)
