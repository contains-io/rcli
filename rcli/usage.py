# -*- coding: utf-8 -*-
"""Utilities for parsing and formatting docopt usage strings.

Functions:
    get_primary_command_usage: Gets the usage string for the primary command.
    get_help_usage: Gets the help message for the command.
    format_usage: Re-formats a usage string to handle wrapping and
        consolidating sections.
    parse_commands: Parses the commands and subcommands out of out of a usage
        string.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from typing import (  # noqa: F401 pylint: disable=unused-import
    Dict,
    Generator,
    List,
    Optional,
    Tuple
)
import collections
import inspect
import logging
import re
import textwrap

import docopt
import six

from .backports.get_terminal_size import get_terminal_size
from .config import settings

_LOGGER = logging.getLogger(__name__)

_DEFAULT_DOC = """
Usage:
  {command} [--help] [--version] [--log-level <level> | --debug | --verbose]
            <command> [<args>...]

Options:
  -h, --help           Display this help message and exit.
  -V, --version        Display the version and exit.
  -d, --debug          Set the log level to DEBUG.
  -v, --verbose        Set the log level to INFO.
  --log-level <level>  Set the log level to one of DEBUG, INFO, WARN, or ERROR.
{{message}}
'{command} help -a' lists all available subcommands.
See '{command} help <command>' for more information on a specific command.
""".format(command=settings.command)


def get_primary_command_usage(message=''):
    # type: (str) -> str
    """Return the usage string for the primary command."""
    if not settings.merge_primary_command and None in settings.subcommands:
        return format_usage(settings.subcommands[None].__doc__)
    if not message:
        message = '\n{}\n'.format(settings.message) if settings.message else ''
    doc = _DEFAULT_DOC.format(message=message)
    if None in settings.subcommands:
        return _merge_doc(doc, settings.subcommands[None].__doc__)
    return format_usage(doc)


def get_help_usage(command):
    # type: (str) -> None
    """Print out a help message and exit the program.

    Args:
        command: If a command value is supplied then print the help message for
            the command module if available. If the command is '-a' or '--all',
            then print the standard help message but with a full list of
            available commands.

    Raises:
        ValueError: Raised if the help message is requested for an invalid
            command or an unrecognized option is passed to help.
    """
    if not command:
        doc = get_primary_command_usage()
    elif command in ('-a', '--all'):
        subcommands = [k for k in settings.subcommands if k is not None]
        available_commands = subcommands + ['help']
        command_doc = '\nAvailable commands:\n{}\n'.format(
            '\n'.join('  {}'.format(c) for c in sorted(available_commands)))
        doc = get_primary_command_usage(command_doc)
    elif command.startswith('-'):
        raise ValueError("Unrecognized option '{}'.".format(command))
    elif command in settings.subcommands:
        subcommand = settings.subcommands[command]
        doc = format_usage(subcommand.__doc__)
    docopt.docopt(doc, argv=('--help',))


def format_usage(doc, width=None):
    # type: (str, Optional[int]) -> str
    """Format the docstring for display to the user.

    Args:
        doc: The docstring to reformat for display.

    Returns:
        The docstring formatted to parse and display to the user. This includes
        dedenting, rewrapping, and translating the docstring if necessary.
    """
    sections = doc.replace('\r', '').split('\n\n')
    width = width or get_terminal_size().columns or 80
    return '\n\n'.join(_wrap_section(s.strip(), width) for s in sections)


def parse_commands(docstring):
    # type: (str) -> Generator[Tuple[List[str], List[str]], None, None]
    """Parse a docopt-style string for commands and subcommands.

    Args:
        docstring: A docopt-style string to parse. If the string is not a valid
            docopt-style string, it will not yield and values.

    Yields:
        All tuples of commands and subcommands found in the docopt docstring.
    """
    try:
        docopt.docopt(docstring, argv=())
    except (TypeError, docopt.DocoptLanguageError):
        return
    except docopt.DocoptExit:
        pass
    for command in _parse_section('usage', docstring):
        args = command.split()
        commands = []
        i = 0
        for i, arg in enumerate(args):
            if arg[0].isalpha() and not arg[0].isupper():
                commands.append(arg)
            else:
                break
        yield commands, args[i:]


def _merge_doc(original, to_merge):
    # type: (str, str) -> str
    """Merge two usage strings together.

    Args:
        original: The source of headers and initial section lines.
        to_merge: The source for the additional section lines to append.

    Returns:
        A new usage string that contains information from both usage strings.
    """
    if not original:
        return to_merge or ''
    if not to_merge:
        return original or ''
    sections = []
    for name in ('usage', 'arguments', 'options'):
        sections.append(_merge_section(
            _get_section(name, original),
            _get_section(name, to_merge)
        ))
    return format_usage('\n\n'.join(s for s in sections).rstrip())


def _merge_section(original, to_merge):
    # type: (str, str) -> str
    """Merge two sections together.

    Args:
        original: The source of header and initial section lines.
        to_merge: The source for the additional section lines to append.

    Returns:
        A new section string that uses the header of the original argument and
        the section lines from both.
    """
    if not original:
        return to_merge or ''
    if not to_merge:
        return original or ''
    try:
        index = original.index(':') + 1
    except ValueError:
        index = original.index('\n')
    name = original[:index].strip()
    section = '\n  '.join(
        (original[index + 1:].lstrip(), to_merge[index + 1:].lstrip())
    ).rstrip()
    return '{name}\n  {section}'.format(name=name, section=section)


def _get_section(name, source):
    # type: (str, str) -> Optional[str]
    """Extract the named section from the source.

    Args:
        name: The name of the section to extract (e.g. "Usage").
        source: The usage string to parse.

    Returns:
        A string containing only the requested section. If the section appears
        multiple times, each instance will be merged into a single section.
    """
    pattern = re.compile(
        '^([^\n]*{name}[^\n]*\n?(?:[ \t].*?(?:\n|$))*)'.format(name=name),
        re.IGNORECASE | re.MULTILINE)
    usage = None
    for section in pattern.findall(source):
        usage = _merge_section(usage, section.strip())
    return usage


def _wrap_section(source, width):
    # type: (str, int) -> str
    """Wrap the given section string to the current terminal size.

    Intelligently wraps the section string to the given width. When wrapping
    section lines, it auto-adjusts the spacing between terms and definitions.
    It also adjusts commands the fit the correct length for the arguments.

    Args:
        source: The section string to wrap.

    Returns:
        The wrapped section string.
    """
    if _get_section('usage', source):
        return _wrap_usage_section(source, width)
    if _is_definition_section(source):
        return _wrap_definition_section(source, width)
    lines = inspect.cleandoc(source).splitlines()
    paragraphs = (textwrap.wrap(line, width, replace_whitespace=False)
                  for line in lines)
    return '\n'.join(line for paragraph in paragraphs for line in paragraph)


def _is_definition_section(source):
    """Determine if the source is a definition section.

    Args:
        source: The usage string source that may be a section.

    Returns:
        True if the source describes a definition section; otherwise, False.
    """
    try:
        definitions = textwrap.dedent(source).split('\n', 1)[1].splitlines()
        return all(
            re.match(r'\s\s+((?!\s\s).+)\s\s+.+', s) for s in definitions)
    except IndexError:
        return False


def _wrap_usage_section(source, width):
    # type: (str, int) -> str
    """Wrap the given usage section string to the current terminal size.

    Note:
        Commands arguments are wrapped to the column that the arguments began
        on the first line of the command.

    Args:
        source: The section string to wrap.

    Returns:
        The wrapped section string.
    """
    if not any(len(line) > width for line in source.splitlines()):
        return source
    section_header = source[:source.index(':') + 1].strip()
    lines = [section_header]
    for commands, args in parse_commands(source):
        command = '  {} '.format(' '.join(commands))
        max_len = width - len(command)
        sep = '\n' + ' ' * len(command)
        wrapped_args = sep.join(textwrap.wrap(' '.join(args), max_len))
        full_command = command + wrapped_args
        lines += full_command.splitlines()
    return '\n'.join(lines)


def _wrap_definition_section(source, width):
    # type: (str, int) -> str
    """Wrap the given definition section string to the current terminal size.

    Note:
        Auto-adjusts the spacing between terms and definitions.

    Args:
        source: The section string to wrap.

    Returns:
        The wrapped section string.
    """
    index = source.index('\n') + 1
    definitions, max_len = _get_definitions(source[index:])
    sep = '\n' + ' ' * (max_len + 4)
    lines = [source[:index].strip()]
    for arg, desc in six.iteritems(definitions):
        wrapped_desc = sep.join(textwrap.wrap(desc, width - max_len - 4))
        lines.append('  {arg:{size}}  {desc}'.format(
            arg=arg,
            size=str(max_len),
            desc=wrapped_desc
        ))
    return '\n'.join(lines)


def _get_definitions(source):
    # type: (str) -> Tuple[Dict[str, str], int]
    """Extract a dictionary of arguments and definitions.

    Args:
        source: The source for a section of a usage string that contains
            definitions.

    Returns:
        A two-tuple containing a dictionary of all arguments and definitions as
        well as the length of the longest argument.
    """
    max_len = 0
    descs = collections.OrderedDict()  # type: Dict[str, str]
    lines = (s.strip() for s in source.splitlines())
    non_empty_lines = (s for s in lines if s)
    for line in non_empty_lines:
        if line:
            arg, desc = re.split(r'\s\s+', line.strip())
            arg_len = len(arg)
            if arg_len > max_len:
                max_len = arg_len
            descs[arg] = desc
    return descs, max_len


def _parse_section(name, source):
    # type: (str, str) -> List[str]
    """Yield each section line.

    Note:
        Depending on how it is wrapped, a section line can take up more than
        one physical line.

    Args:
        name: The name of the section to extract (e.g. "Usage").
        source: The usage string to parse.

    Returns:
        A list containing each line, de-wrapped by whitespace from the source
        code.
        If the section is defined multiple times in the source code, all lines
        from all sections with that name will be returned.
    """
    section = textwrap.dedent(_get_section(name, source)[7:])
    commands = []  # type: List[str]
    for line in section.splitlines():
        if not commands or line[:1].isalpha() and line[:1].islower():
            commands.append(line)
        else:
            commands[-1] = '{} {}'.format(commands[-1].strip(), line.strip())
    return commands
