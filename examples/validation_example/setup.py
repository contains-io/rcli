from setuptools import setup

setup(
    name='validation_example',
    version='1.0.0',
    packages=['validation_example'],
    install_requires=['rapcom'],
    setup_requires=['rapcom'],
    autodetect_commands=True
)
