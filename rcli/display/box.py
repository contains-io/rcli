from . import terminal
from .io import AppendIOBase


class BoxIO(AppendIOBase):
    def update_line(self, line):
        return f"\u2503 {line: <{terminal.cols() - 4}} \u2503"


def line(char="\u2501", start="\u2501", end="\u2501"):
    print(start, char * (terminal.cols() - 2), end, sep="")
