from setuptools import setup

setup(
    name='explicit_example',
    version='0.0.1',
    packages=['explicit_example'],
    install_requires=['docopt_sub'],
    entry_points={
        'console_scripts': [
            'say = docopt_sub.__main__:main'
        ],
        'docopt_sub': [
            'say:hello = explicit_example:hello',
            'say:hiya = explicit_example:hiya'
        ]
    }
)
