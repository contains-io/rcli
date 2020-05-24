import re

import colorama


_INVISIBLE_UNICODE = re.compile("\\[\u00BF-\uFFFF\\]")


def visible_len(s):
    return len(remove_invisible_characters(s))


def remove_invisible_characters(s):
    return remove_control_characters(remove_ansi_codes(s))


def remove_control_characters(s):
    return re.sub(_INVISIBLE_UNICODE, "", s)


def remove_ansi_codes(s):
    return re.sub(colorama.ansitowin32.AnsiToWin32.ANSI_CSI_RE, "", s)
