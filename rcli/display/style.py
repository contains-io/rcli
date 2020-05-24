import copy
import typing

import colorama


class Alignment:
    LEFT = 0
    CENTER = 1
    RIGHT = 2


class Color:
    def __init__(self, color):
        if color < 0 or color > 256:
            raise AttributeError("color must be between 0 and 256 inclusive")
        self._color = color

    def __str__(self):
        return self.foreground()

    def foreground(self):
        return f"38;5;{self._color}"

    def background(self):
        return f"48;5;{self._color}"


class _Reset:
    def __str__(self):
        return str(colorama.Style.RESET_ALL)

    def __enter__(self):
        pass

    def __exit__(self, *args, **kwargs):
        pass

    def __add__(self, s):
        return str(self) + s

    def __radd__(self, s):
        return s + str(self)


class Style:
    reset = _Reset()
    __stack = []

    def __init__(
        self,
        foreground: typing.Union[Color, str, int] = None,
        background: typing.Union[Color, str, int] = None,
        bold: bool = None,
        italic: bool = None,
        dim: bool = None,
        underlined: bool = None,
        blink: bool = None,
        reverse: bool = None,
        hidden: bool = None,
        reset: bool = True,
    ):
        self.foreground = str(foreground) if foreground else None
        self.background = str(background) if background else None
        if hasattr(background, "background"):
            self.background = background.background()
        if str(foreground).startswith("\033["):
            self.foreground = str(foreground).strip("\033[m")
        if str(background).startswith("\033["):
            self.background = str(background).strip("\033[m")
        self.bold = bold
        self.dim = dim
        self.italic = italic
        self.underlined = underlined
        self.blink = blink
        self.reverse = reverse
        self.hidden = hidden
        self._reset = reset

    def __str__(self):
        value = "{}{}{}{}{}{}{}{}{}{}{}".format(
            colorama.Style.RESET_ALL if self._reset else "",
            colorama.ansi.CSI,
            self._value(self.foreground, None, "foreground"),
            self._value(self.background, None, "background",),
            self._value(1, 21, "bold"),
            self._value(2, 22, "dim"),
            self._value(3, 23, "italic"),
            self._value(4, 24, "underlined"),
            self._value(5, 25, "blink"),
            self._value(7, 27, "reverse"),
            self._value(8, 28, "hidden"),
        )
        return f"{value[:-1]}m"

    def __repr__(self):
        return str(list(str(self)))

    def _value(self, on, off, param):
        value = getattr(self, param, None)
        if value is False and off is not None:
            return f"{off};"
        if value is not None and on is not None:
            return f"{on};"
        return ""

    def __add__(self, s):
        return str(self) + s

    def __radd__(self, s):
        return s + str(self)

    def __call__(self, s):
        return f"{self.reset}{self.full_style(self)}{s}{self.current()}"

    def __enter__(self):
        self.__stack.append(self.full_style(self))
        print(self.current(), end="")

    def __exit__(self, *args, **kwargs):
        self.__stack.pop()
        print(self.current(), end="")

    @classmethod
    def full_style(cls, style):
        full_style = copy.deepcopy(style)
        if cls.__stack:
            current = cls.current()
            for attr in vars(full_style):
                if getattr(full_style, attr, None) is None:
                    setattr(full_style, attr, getattr(current, attr, None))
        return full_style

    @classmethod
    def current(cls):
        return cls.__stack[-1] if cls.__stack else cls.reset


Style.default = Style.reset
Style.bold = bright = Style(bold=True)
Style.dim = Style(dim=True)
Style.italic = Style(italic=True)
Style.underlined = Style(underlined=True)
Style.blink = Style(blink=True)
Style.reverse = Style(reverse=True)
Style.hidden = Style(hidden=True)


def styled(text, *args, **kwargs):
    return Style(*args, **kwargs)(text)
