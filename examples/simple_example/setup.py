from setuptools import setup

setup(
    name='simple_example',
    version='0.0.1',
    packages=['simple_example'],
    install_requires=['docopt_sub'],
    setup_requires=['docopt_sub'],
    commands=['say']
)
