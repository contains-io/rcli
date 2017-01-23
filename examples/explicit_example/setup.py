from setuptools import setup

setup(
    name='explicit_example',
    version='1.0.0',
    packages=['explicit_example'],
    install_requires=['rcli'],
    entry_points={
        'console_scripts': [
            'say = rcli.dispatcher:main'
        ],
        'rcli': [
            'say:hello = explicit_example:hello',
            'say:hiya = explicit_example:hiya'
        ]
    }
)
