from setuptools import setup

setup(
    name='simple_example',
    version='1.0.0',
    packages=['simple_example'],
    install_requires=['rapcom'],
    setup_requires=['rapcom'],
    autodetect_commands=True
)
