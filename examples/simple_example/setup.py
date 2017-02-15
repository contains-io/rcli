from setuptools import setup

setup(
    name='simple_example',
    version='1.0.0',
    packages=['simple_example'],
    install_requires=['rcli'],
    setup_requires=['rcli'],
    autodetect_commands=True
)
