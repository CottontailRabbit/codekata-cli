"""raw(cbreak) 키 입력. 화살표/ESC/Enter/Backspace/UTF-8 처리."""
import os
import select
import sys
import termios
import tty

SEQ = {"[A": "UP", "[B": "DOWN", "[C": "RIGHT", "[D": "LEFT", "[H": "HOME", "[F": "END",
       "OA": "UP", "OB": "DOWN", "OC": "RIGHT", "OD": "LEFT", "[1~": "HOME", "[4~": "END", "[3~": "DEL"}


class Keys:
    def __init__(self):
        self.fd = sys.stdin.fileno()
        self.old = None

    def __enter__(self):
        if os.isatty(self.fd):
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *exc):
        if self.old is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def flush(self):
        if os.isatty(self.fd):
            termios.tcflush(self.fd, termios.TCIFLUSH)

    def _ready(self, timeout):
        return bool(select.select([self.fd], [], [], timeout)[0])

    def get(self, timeout=None):
        """키 하나를 읽는다. timeout 초과 시 None."""
        if not self._ready(timeout):
            return None
        b = os.read(self.fd, 1)
        if not b:
            raise EOFError
        if b == b"\x1b":
            seq = b""
            while len(seq) < 4 and self._ready(0.008):
                seq += os.read(self.fd, 1)
                if seq[-1:].isalpha() or seq[-1:] == b"~":
                    break
            return SEQ.get(seq.decode(errors="ignore"), "ESC")
        if b in (b"\r", b"\n"):
            return "ENTER"
        if b in (b"\x7f", b"\x08"):
            return "BACKSPACE"
        if b == b"\t":
            return "TAB"
        if b == b"\x15":
            return "CTRL_U"
        if b == b"\x17":
            return "CTRL_W"
        if b == b"\x03":
            raise KeyboardInterrupt
        if b == b"\x04":
            raise EOFError
        lead = b[0]
        n = 0
        if lead >= 0xF0:
            n = 3
        elif lead >= 0xE0:
            n = 2
        elif lead >= 0xC0:
            n = 1
        for _ in range(n):
            b += os.read(self.fd, 1)
        ch = b.decode("utf-8", errors="replace")
        return ch if ch.isprintable() else None
