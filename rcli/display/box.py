import contextlib
import functools

from . import terminal
from .io import AppendIOBase
from .util import remove_invisible_characters, visible_len
from .style import Alignment, Style


class _BoxIO(AppendIOBase):
    def __init__(self, box_):
        super().__init__()
        self._box = box_
        self._style = Style.current()
        self._sep = remove_invisible_characters(self._box._get_sep())

    def write(self, s):
        super().write(
            f"{self._style if self._is_sep(s) else Style.current()}{s}"
        )

    def update_line(self, s):
        stack = Box._stack
        current_style = Style.current()
        if self._is_sep(s):
            stack = Box._stack[:-1]
            current_style = self._style
        left = " ".join(f"{box[1]}{box[0]._vertical}" for box in stack)
        left += " " if left else ""
        return (
            functools.reduce(
                lambda r, b: self._get_right_append(r, b[0], *b[1]),
                zip(range(len(stack) - 1, -1, -1), reversed(stack)),
                f"{self._style}{left}{current_style}{s}{self._style}",
            )
            + Style.reset
        )

    def _is_sep(self, s):
        cleaned_s = remove_invisible_characters(s)
        return (
            cleaned_s[:2] == self._sep[:2] and cleaned_s[-2:] == self._sep[-2:]
        )

    def _get_right_append(self, current, i, box_, style):
        num_spaces = (
            (box_._size or terminal.cols())
            - visible_len(current)
            - visible_len(box_._vertical)
            - i * 2
        )
        return f"{current}{style}{' ' * num_spaces}{box_._vertical}"


class Box:
    _depth = 0
    _stack = []

    def __init__(
        self,
        upper_left="\u250C",
        upper_right="\u2510",
        lower_left="\u2514",
        lower_right="\u2518",
        horizontal="\u2500",
        vertical="\u2502",
        sep_left="\u251C",
        sep_horizontal="\u2500",
        sep_right="\u2524",
        size=None,
        header="",
        footer="",
        align=Alignment.LEFT,
        header_align=None,
        footer_align=None,
        sep_align=None,
        header_style=None,
        footer_style=None,
        sep_style=None,
    ):
        self._upper_left = upper_left
        self._upper_right = upper_right
        self._lower_left = lower_left
        self._lower_right = lower_right
        self._horizontal = horizontal
        self._vertical = vertical
        self._sep_left = sep_left
        self._sep_horizontal = sep_horizontal
        self._sep_right = sep_right
        self._size = size
        self._header = header
        self._footer = footer
        self._header_align = header_align or align
        self._footer_align = footer_align or align
        self._sep_align = sep_align or align
        self._header_style = header_style
        self._footer_style = footer_style
        self._sep_style = sep_style

    def top(self, text="", align=None):
        with Style.current():
            print(
                self._line(
                    self._horizontal,
                    self._upper_left,
                    f"{self._upper_right}{Style.reset}",
                    self._header_style(text) if self._header_style else text,
                    align,
                ),
                flush=True,
            )

    def sep(self, text="", align=None):
        print(
            self._get_sep(text, align or self._sep_align), sep="", flush=True
        )

    def bottom(self, text="", align=None):
        with Style.current():
            print(
                self._line(
                    self._horizontal,
                    self._lower_left,
                    f"{self._lower_right}{Style.reset}",
                    self._footer_style(text) if self._footer_style else text,
                    align,
                ),
                flush=True,
            )

    def _line(self, char, start, end, text="", align=None):
        size = self._size or terminal.cols()
        vislen = visible_len(text)
        if vislen:
            text = f" {text} "
            vislen += 2
        width = size - 4 * (Box._depth - 1) - vislen - 4
        if align == Alignment.CENTER:
            return f"{start}{char}{char * int(width / 2 + .5)}{text}{char * int(width / 2)}{char}{end}"
        if align == Alignment.RIGHT:
            return f"{start}{char}{char * width}{text}{char}{end}"
        return f"{start}{char}{text}{char * width}{char}{end}"

    def _create_buffer(self):
        return _BoxIO(self)

    def _get_sep(self, text="", align=None):
        return self._line(
            self._sep_horizontal,
            self._sep_left,
            self._sep_right,
            self._sep_style(text) if self._sep_style else text,
            align,
        )

    def __enter__(self):
        Box._depth += 1
        self.top(self._header, self._header_align)
        Box._stack.append((self, Style.current()))
        return self

    def __exit__(self, *args, **kwargs):
        Box._stack.pop()
        self.bottom(self._footer, self._footer_align)
        Box._depth -= 1

    @staticmethod
    def new_style(*args, **kwargs):
        @contextlib.contextmanager
        def inner(**kw):
            impl = Box(*args, **kwargs)
            if Box._stack:
                impl._size = Box._stack[-1][0]._size
            if "size" in kw:
                impl._size = kw["size"]
            impl._header = kw.get("header", "")
            impl._header_align = kw.get(
                "header_align", kw.get("align", impl._header_align)
            )
            impl._footer = kw.get("footer", "")
            impl._footer_align = kw.get(
                "footer_align", kw.get("align", impl._footer_align)
            )
            impl._sep_align = kw.get(
                "sep_align", kw.get("align", impl._sep_align)
            )
            with impl, contextlib.redirect_stdout(impl._create_buffer()):
                yield impl

        return inner


Box.simple = Box.new_style()
Box.thick = Box.new_style(
    "\u250F",
    "\u2513",
    "\u2517",
    "\u251B",
    "\u2501",
    "\u2503",
    "\u2523",
    "\u2501",
    "\u252B",
    header_style=Style.bold,
    footer_style=Style.bold,
    sep_style=Style.bold,
)
Box.info = Box.new_style(
    "\u250F",
    "\u2513",
    "\u2517",
    "\u251B",
    "\u2501",
    "\u2503",
    "\u2520",
    "\u2500",
    "\u2528",
)
Box.ascii = Box.new_style("+", "+", "+", "+", "=", "|", "+", "-", "+")
Box.star = Box.new_style("*", "*", "*", "*", "*", "*", "*", "*", "*")
Box.double = Box.new_style(
    "\u2554",
    "\u2557",
    "\u255A",
    "\u255D",
    "\u2550",
    "\u2551",
    "\u2560",
    "\u2550",
    "\u2563",
)
Box.fancy = Box.new_style("\u2552", "\u2555", "\u2558", "\u255B", "\u2550")
Box.round = Box.new_style("\u256D", "\u256E", "\u2570", "\u256F")

box = Box.simple
