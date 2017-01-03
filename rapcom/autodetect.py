import ast
import collections
import os.path
import re
import setuptools

import docopt


Command = collections.namedtuple(
    'Command', ('command', 'subcommand', 'module', 'callable'))


_USAGE_PATTERN = re.compile(r'^([^\n]*usage\:[^\n]*\n?(?:[ \t].*?(?:\n|$))*)',
                            re.IGNORECASE | re.MULTILINE)


def setup_keyword(dist, keyword, value):
    """Add autodetected commands as entry points."""
    if value is not True or keyword != 'autodetect_commands':
        return
    if dist.entry_points is None:
        dist.entry_points = {}
    for command, subcommands in _get_commands(dist).items():
        dist.entry_points.setdefault('console_scripts', []).append(
            '{command} = rapcom.__main__:main'.format(command=command)
        )
        dist.entry_points.setdefault('rapcom', []).extend(subcommands)


def _get_commands(dist):
    py_files = (f for f in setuptools.findall()
                if os.path.splitext(f)[1].lower() == '.py')
    pkg_files = (f for f in py_files if _get_package_name(f) in dist.packages)
    commands = {}
    for fn in pkg_files:
        with open(fn) as f:
            module = ast.parse(f.read())
        module.__name__ = _get_module_name(fn)
        _append_commands(commands, _get_module_commands(module))
        _append_commands(commands, _get_class_commands(module))
        _append_commands(commands, _get_function_commands(module))
    return commands


def _append_commands(dct, commands):
    for command in commands:
        entry_point = '{command}{subcommand} = {module}{callable}'.format(
            command=command.command,
            subcommand=(':{}'.format(command.subcommand)
                        if command.subcommand else ''),
            module=command.module,
            callable=(':{}'.format(command.callable)
                      if command.callable else ''),
        )
        dct.setdefault(command.command, []).append(entry_point)


def _get_package_name(fn):
    return _get_module_name(fn).rsplit('.', 1)[0]


def _get_module_name(fn):
    return fn[:-3].replace('/', '.')


def _get_module_commands(module):
    cls = next((n for n in module.body
                if isinstance(n, ast.ClassDef) and n.name == 'Command'), None)
    if not cls:
        return
    methods = (n.name for n in cls.body if isinstance(n, ast.FunctionDef))
    if '__call__' not in methods:
        return
    docstring = ast.get_docstring(module)
    for command, subcommand in _parse_commands(docstring):
        yield Command(command, subcommand, module.__name__, None)


def _get_class_commands(module):
    nodes = (n for n in module.body if isinstance(n, ast.ClassDef))
    for cls in nodes:
        methods = (n.name for n in cls.body if isinstance(n, ast.FunctionDef))
        if '__call__' in methods:
            docstring = ast.get_docstring(cls)
            for command, subcommand in _parse_commands(docstring):
                yield Command(command, subcommand, module.__name__, cls.name)


def _get_function_commands(module):
    nodes = (n for n in module.body if isinstance(n, ast.FunctionDef))
    for func in nodes:
        docstring = ast.get_docstring(func)
        for command, subcommand in _parse_commands(docstring):
            yield Command(command, subcommand, module.__name__, func.name)


def _parse_commands(docstring):
    try:
        docopt.docopt(docstring, argv=())
    except (TypeError, docopt.DocoptLanguageError):
        return
    except docopt.DocoptExit:
        pass
    match = _USAGE_PATTERN.findall(docstring)[0]
    usage = match.strip()[6:]
    usage_sections = [s.strip() for s in usage.split('\n')]
    for section in usage_sections:
        args = section.split()
        command = args[0]
        subcommand = None
        if len(args) > 1 and not (args[1].startswith('<') or
                                  args[1].startswith('-') or
                                  args[1].isupper()):
            subcommand = args[1]
        yield command, subcommand
