import io
import sys

from . import terminal


class AppendIOBase(io.StringIO):
    def __init__(self, stdout=sys.stdout):
        self._stdout = stdout

    def flush(self):
        buffer = self.getvalue()
        lines = buffer.split("\n")
        nl = "\n".join(self.update_line(line) for line in lines if line)
        self._stdout.write(nl + ("\n" if buffer.endswith("\n") else ""))
        self.clear_buffer()
        self._stdout.flush()

    def update_line(self, line):
        return line

    def clear_buffer(self):
        self.truncate(0)
        self.seek(0)

    def close(self):
        self.flush()
        super().close()
