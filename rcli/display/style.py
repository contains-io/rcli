import copy
import types

import colorama


class Style:
    __stack = []

    def __init__(
        self,
        foreground: types.Option[Color, str, int] = None,
        background: types.Option[Color, str, int] = None,
        bold: bool = None,
        italic: bool = None,
        dim: bool = None,
        underlined: bool = None,
        blink: bool = None,
        reverse: bool = None,
        hidden: bool = None,
    ):
        if str(foreground).startswith("\033["):
            self.foreground = str(foreground).strip("\033[m")
        else:
            self.foreground = str(foreground)
        if str(background).startswith("\033["):
            self.background = str(background).strip("\033[m")
        elif isinstance(background, int):
            self.background = str(background)
        else:
            self.background = background.background()
        self.bold = bold
        self.dim = dim
        self.italic = italic
        self.underlined = underlined
        self.blink = blink
        self.reverse = reverse
        self.hidden = hidden

    def __str__(self):
        value = "{escape}{}{}{}{}{}{}{}{}{}".format(
            self._value(self.foreground, None, "foreground"),
            self._value(self.background, None, "background",),
            self._value(1, 21, "bold"),
            self._value(2, 22, "dim"),
            self._value(3, 23, "italic"),
            self._value(4, 24, "underlined"),
            self._value(5, 25, "blink"),
            self._value(7, 27, "reverse"),
            self._value(8, 28, "hidden"),
            escape=colorama.ansi.CSI,
        )
        return f"{value[:-1]}m"

    def _value(self, on, off, param):
        value = getattr(self, param, None)
        if value is False and off is not None:
            return f"{off};"
        if value is not None and on is not None:
            return f"{on};"
        return ""

    def __enter__(self):
        self.__stack.append(self.full_style(self))
        print(colorama.Style.RESET_ALL, end="")
        print(self.current(), end="")

    def __exit__(self, *args, **kwargs):
        self.__stack.pop()
        print(colorama.Style.RESET_ALL, end="")
        print(self.current(), end="")

    @classmethod
    def full_style(cls, style):
        full_style = copy.deepcopy(style)
        if cls.__stack:
            current = cls.current()
            if full_style.foreground == None:
                full_style.foreground = current.foreground
            if full_style.background == None:
                full_style.background = current.background
            if full_style.bold == None:
                full_style.bold = current.bold
            if full_style.italic == None:
                full_style.italic = current.italic
            if full_style.dim == None:
                full_style.dim = current.dim
            if full_style.underlined == None:
                full_style.underlined = current.underlined
            if full_style.blink == None:
                full_style.blink = current.blink
            if full_style.reverse == None:
                full_style.reverse = current.reverse
            if full_style.hidden == None:
                full_style.hidden = current.hidden
        return full_style

    @classmethod
    def current(cls):
        return cls.__stack[-1] if cls.__stack else colorama.Style.RESET_ALL


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


bold = bright = Style(bold=True)
dim = Style(dim=True)
italic = Style(italic=True)
underlined = Style(underlined=True)
blink = Style(blink=True)
reverse = Style(reverse=True)
hidden = Style(hidden=True)
