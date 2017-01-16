from setuptools import setup

setup(
    name='explicit_example',
    version='1.0.0',
    packages=['explicit_example'],
    install_requires=['rapcom'],
    entry_points={
        'console_scripts': [
            'say = rapcom.dispatcher:main'
        ],
        'rapcom': [
            'say:hello = explicit_example:hello',
            'say:hiya = explicit_example:hiya'
        ]
    }
)
