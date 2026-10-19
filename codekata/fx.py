"""터미널 렌더링 + 타격감 이펙트 (흔들림, 플래시, 빅 텍스트 슬램, 데미지 팝업)."""
import random
import re
import shutil
import sys
import time
import unicodedata


class Settings:
    color = True
    fx = True


S = Settings()

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
SGR_RE = re.compile(r"\x1b\[[0-9;]*m")
RESET = "\x1b[0m"
MARGIN = 3

# 256색 팔레트
RED, ORANGE, YELLOW, GOLD, GREEN, LIME = 196, 208, 226, 220, 46, 118
CYAN, SKY, BLUE, PURPLE, MAGENTA, PINK = 51, 117, 33, 129, 201, 213
WHITE, GREY, DIM, DARK, BLACK = 231, 248, 244, 238, 16
RAINBOW = [196, 208, 226, 46, 51, 33, 129, 201]


def c(text, color=None, bold=False, bg=None, ul=False, rev=False):
    codes = []
    if bold:
        codes.append("1")
    if ul:
        codes.append("4")
    if rev:
        codes.append("7")
    if color is not None:
        codes.append(f"38;5;{color}")
    if bg is not None:
        codes.append(f"48;5;{bg}")
    if not codes:
        return str(text)
    return f"\x1b[{';'.join(codes)}m{text}{RESET}"


def width(s):
    w = 0
    for ch in ANSI_RE.sub("", s):
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in "WF" else 1
    return w


def pad(s, n):
    return s + " " * max(0, n - width(s))


def rpad(s, n):
    return " " * max(0, n - width(s)) + s


def center(s, n):
    left = max(0, (n - width(s)) // 2)
    return " " * left + s


def truncate(s, maxw):
    """ANSI 코드를 보존하면서 표시 폭 기준으로 자른다."""
    if width(s) <= maxw:
        return s
    out, w, i = [], 0, 0
    while i < len(s):
        m = ANSI_RE.match(s, i)
        if m:
            out.append(m.group())
            i = m.end()
            continue
        ch = s[i]
        cw = 2 if unicodedata.east_asian_width(ch) in "WF" else 1
        if w + cw > maxw - 1:
            out.append("…")
            break
        out.append(ch)
        w += cw
        i += 1
    return "".join(out) + RESET


def size():
    ts = shutil.get_terminal_size((100, 32))
    return ts.columns, ts.lines


def write(s):
    if not S.color:
        s = SGR_RE.sub("", s)
    sys.stdout.write(s)
    sys.stdout.flush()


def sleep(sec):
    if S.fx:
        time.sleep(sec)


# ─── 화면 ─────────────────────────────────────────────────────

FRAME = []


def enter():
    write("\x1b[?1049h\x1b[?25l\x1b[2J\x1b[H")


def leave():
    write(RESET + "\x1b[?25h\x1b[?1049l")


def draw(lines, dx=0, dy=0):
    cols, rows = size()
    maxw = cols - MARGIN - 1
    buf = ["\x1b[H"]
    for _ in range(max(0, dy)):
        buf.append("\x1b[K\n")
    for line in lines[: max(1, rows - 1 - max(0, dy))]:
        buf.append(" " * max(0, MARGIN + dx) + truncate(line, maxw) + RESET + "\x1b[K\n")
    buf.append("\x1b[J")
    write("".join(buf))


def show(lines):
    FRAME[:] = lines
    draw(lines)


def redraw():
    draw(FRAME)


def shake(power=2, frames=6):
    if not S.fx:
        return
    for i in range(frames):
        p = max(1, power - i // 2)
        draw(FRAME, dx=random.randint(-p, p), dy=random.choice((0, 0, 1)) if power > 1 else 0)
        time.sleep(0.022)
    redraw()


def flash(color=WHITE, ms=45):
    if not S.fx:
        return
    cols, rows = size()
    if S.color:
        write("\x1b[H" + f"\x1b[48;5;{color}m" + ((" " * cols + "\n") * (rows - 1)) + " " * cols + RESET)
    else:
        write("\x1b[?5h")
    time.sleep(ms / 1000)
    if not S.color:
        write("\x1b[?5l")
    redraw()


def put(row, col, text):
    write(f"\x1b[{row};{col}H{text}{RESET}")


def overlay(block, row=None, colors=None, bg=None):
    """block(줄 리스트)을 화면 가운데에 덧그린다. FRAME은 건드리지 않음."""
    cols, rows = size()
    h = len(block)
    top = row if row is not None else max(1, (rows - h) // 2)
    bw = max(width(b) for b in block) if block else 0
    left = max(1, (cols - bw) // 2)
    for i, line in enumerate(block):
        col = colors[i % len(colors)] if colors else None
        put(top + i, left, c(pad(line, bw), col, bold=True, bg=bg))


def slam(text, color=YELLOW, hold=0.35, shake_power=3, sub=None, sub_color=None):
    """빅 텍스트가 위에서 떨어져 '쾅' 박히는 연출."""
    block = big(text)
    if sub:
        block = block + [""] + [center(sub, max(width(b) for b in block))]
    if not S.fx:
        return
    cols, rows = size()
    final = max(1, (rows - len(block)) // 2)
    colors = color if isinstance(color, list) else [color]
    for start in (max(1, final - 6), max(1, final - 3)):
        redraw()
        overlay(block, start, colors=[DARK])
        time.sleep(0.03)
    redraw()
    overlay(block, final, colors=colors)
    if sub:
        overlay([center(sub, max(width(b) for b in block))], final + len(block) - 1, colors=[sub_color or WHITE])
    for i in range(4):
        dx = (-1) ** i * max(1, shake_power - i)
        write("\x1b[H")
        draw(FRAME, dx=dx)
        overlay(block, final + (1 if i == 0 else 0), colors=colors)
        time.sleep(0.025)
    time.sleep(hold)
    redraw()


def popup(text, row, col, color=GOLD, rise=3):
    if not S.fx:
        return
    w = width(text)
    for i in range(rise + 1):
        r = max(1, row - i)
        put(r, col, c(text, color, bold=True))
        time.sleep(0.05)
        put(r, col, " " * w)
    redraw()


def typewriter_line(prefix, text, cps=180):
    """FRAME 맨 끝에 한 줄을 타자기처럼 출력하고 FRAME에 고정."""
    row = len(FRAME) + 1
    FRAME.append(prefix + text)
    if not S.fx:
        redraw()
        return
    put(row, MARGIN + 1, prefix)
    i = 0
    while i < len(text):
        m = ANSI_RE.match(text, i)
        if m:
            write(m.group())
            i = m.end()
            continue
        write(text[i])
        if text[i] != " ":
            time.sleep(1 / cps)
        i += 1
    write(RESET)


# ─── 빅 폰트 ─────────────────────────────────────────────────

_FONT_SRC = {
    "A": [" ### ", "#   #", "#####", "#   #", "#   #"],
    "B": ["#### ", "#   #", "#### ", "#   #", "#### "],
    "C": [" ####", "#    ", "#    ", "#    ", " ####"],
    "D": ["#### ", "#   #", "#   #", "#   #", "#### "],
    "E": ["#####", "#    ", "#### ", "#    ", "#####"],
    "F": ["#####", "#    ", "#### ", "#    ", "#    "],
    "G": [" ####", "#    ", "#  ##", "#   #", " ####"],
    "H": ["#   #", "#   #", "#####", "#   #", "#   #"],
    "I": ["###", " # ", " # ", " # ", "###"],
    "J": ["  ###", "   # ", "   # ", "#  # ", " ##  "],
    "K": ["#   #", "#  # ", "###  ", "#  # ", "#   #"],
    "L": ["#    ", "#    ", "#    ", "#    ", "#####"],
    "M": ["#   #", "## ##", "# # #", "#   #", "#   #"],
    "N": ["#   #", "##  #", "# # #", "#  ##", "#   #"],
    "O": [" ### ", "#   #", "#   #", "#   #", " ### "],
    "P": ["#### ", "#   #", "#### ", "#    ", "#    "],
    "Q": [" ### ", "#   #", "# # #", "#  # ", " ## #"],
    "R": ["#### ", "#   #", "#### ", "#  # ", "#   #"],
    "S": [" ####", "#    ", " ### ", "    #", "#### "],
    "T": ["#####", "  #  ", "  #  ", "  #  ", "  #  "],
    "U": ["#   #", "#   #", "#   #", "#   #", " ### "],
    "V": ["#   #", "#   #", "#   #", " # # ", "  #  "],
    "W": ["#   #", "#   #", "# # #", "## ##", "#   #"],
    "X": ["#   #", " # # ", "  #  ", " # # ", "#   #"],
    "Y": ["#   #", " # # ", "  #  ", "  #  ", "  #  "],
    "Z": ["#####", "   # ", "  #  ", " #   ", "#####"],
    "0": [" ### ", "#  ##", "# # #", "##  #", " ### "],
    "1": ["  #  ", " ##  ", "  #  ", "  #  ", " ### "],
    "2": [" ### ", "#   #", "  ## ", " #   ", "#####"],
    "3": ["#### ", "    #", " ### ", "    #", "#### "],
    "4": ["#   #", "#   #", "#####", "    #", "    #"],
    "5": ["#####", "#    ", "#### ", "    #", "#### "],
    "6": [" ### ", "#    ", "#### ", "#   #", " ### "],
    "7": ["#####", "    #", "   # ", "  #  ", "  #  "],
    "8": [" ### ", "#   #", " ### ", "#   #", " ### "],
    "9": [" ### ", "#   #", " ####", "    #", " ### "],
    "!": ["#", "#", "#", " ", "#"],
    ".": [" ", " ", " ", " ", "#"],
    "x": ["   ", "# #", " # ", "# #", "   "],
    "+": ["   ", " # ", "###", " # ", "   "],
    "-": ["   ", "   ", "###", "   ", "   "],
    " ": ["  ", "  ", "  ", "  ", "  "],
}
FONT = {k: [row.replace("#", "█") for row in v] for k, v in _FONT_SRC.items()}


def big(text):
    rows = ["", "", "", "", ""]
    for ch in text:
        g = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
        for i in range(5):
            rows[i] += g[i] + " "
    return [r.rstrip() for r in rows]


def bar(frac, n, full_color, empty_color=DARK, ch_full="█", ch_empty="░"):
    frac = max(0.0, min(1.0, frac))
    k = int(round(frac * n))
    return c(ch_full * k, full_color) + c(ch_empty * (n - k), empty_color)


def hp_color(frac):
    if frac > 0.6:
        return GREEN
    if frac > 0.3:
        return YELLOW
    return RED


def fmt(n):
    return f"{int(n):,}"
