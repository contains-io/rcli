from ..backports.get_terminal_size import get_terminal_size


def cols():
    """Get the current number of columns on the terminal.

    Returns:
        The current number of columns in the terminal or 80 if there is no tty.
    """
    return get_terminal_size().columns or 80
