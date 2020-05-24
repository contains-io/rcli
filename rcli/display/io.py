import io
import sys

from .util import remove_invisible_characters


class AppendIOBase(io.StringIO):
    def __init__(self, stdout=sys.stdout):
        super().__init__("", None)
        self._stdout = stdout

    def flush(self):
        buffer = self.getvalue()
        lines = buffer.split("\n")
        nl = "\n".join(
            self.update_line(line)
            if remove_invisible_characters(line)
            else line
            for line in lines
        )
        self._stdout.write(nl)
        self.clear_buffer()
        self._stdout.flush()

    def update_line(self, s):
        return s

    def clear_buffer(self):
        self.truncate(0)
        self.seek(0)

    def close(self):
        self.flush()
        super().close()
