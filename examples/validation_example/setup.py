from setuptools import setup

setup(
    name='validation_example',
    version='0.0.1',
    packages=['validation_example'],
    install_requires=['docopt_sub'],
    setup_requires=['docopt_sub'],
    commands=['say']
)
