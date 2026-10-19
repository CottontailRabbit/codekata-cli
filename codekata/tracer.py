"""디버거: Python 코드를 sys.settrace로 한 줄씩 기록하고 '킬캠 리플레이'로 재생한다."""
import json
import os
import subprocess
import tempfile

from . import fx
from .i18n import tr

TRACER = r'''
import sys, json, io, types
src = sys.stdin.read()
steps, out = [], io.StringIO()
MAX = 400
class Stop(Exception): pass
def snap(frame):
    loc = {}
    for k, v in list(frame.f_locals.items()):
        if k.startswith("__") or isinstance(v, (types.ModuleType, types.FunctionType, type)) or callable(v) and not isinstance(v, (list, dict, set, tuple)):
            continue
        try: r = repr(v)
        except Exception: r = "<?>"
        loc[k] = r if len(r) <= 60 else r[:57] + "..."
    return loc
def tr(frame, event, arg):
    if frame.f_code.co_filename != "<kata>":
        return None
    if event in ("line", "return", "exception"):
        st = {"ln": frame.f_lineno, "ev": event, "fn": frame.f_code.co_name, "depth": depth(frame),
              "vars": snap(frame), "out": out.getvalue()[-400:]}
        if event == "return":
            st["ret"] = repr(arg)[:60]
        if event == "exception":
            st["exc"] = f"{arg[0].__name__}: {arg[1]}"[:120]
        steps.append(st)
        if len(steps) >= MAX:
            raise Stop()
    return tr
def depth(frame):
    d = 0
    while frame is not None and frame.f_code.co_filename == "<kata>":
        d += 1; frame = frame.f_back
    return d - 1
err = None
real = sys.stdout
sys.stdout = out
try:
    code = compile(src, "<kata>", "exec")
    sys.settrace(tr)
    exec(code, {"__name__": "__main__"})
except Stop:
    err = f"(stopped after {MAX} steps)"
except BaseException as e:
    err = f"{type(e).__name__}: {e}"[:200]
finally:
    sys.settrace(None)
    sys.stdout = real
print(json.dumps({"steps": steps, "error": err, "out": out.getvalue()[-2000:]}))
'''


def trace(code, timeout=5):
    with tempfile.TemporaryDirectory(prefix="codekata-dbg-") as tmp:
        try:
            p = subprocess.run(["python3", "-I", "-c", TRACER], input=code, capture_output=True, text=True,
                               timeout=timeout, cwd=tmp, env=dict(os.environ, PYTHONHASHSEED="0"))
        except subprocess.TimeoutExpired:
            return {"steps": [], "error": "Timeout", "out": ""}
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return {"steps": [], "error": (p.stderr.strip().splitlines() or ["tracer failed"])[-1], "out": ""}


def _frame(code_lines, data, i, title, auto):
    steps = data["steps"]
    st = steps[i]
    prev = steps[i - 1]["vars"] if i > 0 and steps[i - 1]["fn"] == st["fn"] else {}
    cols, rows = fx.size()
    L = []
    head = fx.c(" KILLCAM REPLAY ", fx.BLACK, bold=True, bg=fx.RED) + " " + fx.c(title, fx.WHITE, bold=True)
    L.append(head + "   " + fx.c(f"STEP {i + 1}/{len(steps)}", fx.GOLD, bold=True) +
             ("  " + fx.c("▶ AUTO", fx.LIME, bold=True) if auto else ""))
    L.append(fx.bar((i + 1) / len(steps), min(60, cols - 10), fx.RED, ch_full="━", ch_empty="─"))
    L.append("")
    for n, line in enumerate(code_lines, 1):
        if n == st["ln"]:
            mark = {"line": "▶", "return": "↩", "exception": "✖"}[st["ev"]]
            color = {"line": fx.YELLOW, "return": fx.CYAN, "exception": fx.RED}[st["ev"]]
            L.append(fx.c(f"{mark}{n:>3} ", color, bold=True) + fx.c(line or " ", fx.BLACK, bg=color))
        else:
            L.append(fx.c(f" {n:>3} ", fx.DIM) + fx.c(line, fx.GREY))
    L.append("")
    where = "<module>" if st["fn"] == "<module>" else f"{st['fn']}()"
    L.append(fx.c(tr("─ 변수 ", "─ vars "), fx.CYAN, bold=True) + fx.c(f"@ {where}" + ("  " + "·" * st["depth"] if st["depth"] else ""),
                                                        fx.DIM))
    if not st["vars"]:
        L.append(fx.c(tr("  (없음)", "  (none)"), fx.DIM))
    for k, v in st["vars"].items():
        changed = prev.get(k) != v
        tag = fx.c(" ◀ NEW" if k not in prev else " ◀ CHANGED", fx.ORANGE, bold=True) if changed and i > 0 else ""
        L.append(f"  {fx.c(k, fx.SKY, bold=True)} = {fx.c(v, fx.YELLOW if changed else fx.WHITE)}{tag}")
    if st.get("ret") is not None:
        L.append(f"  {fx.c('return', fx.CYAN, bold=True)} → {fx.c(st['ret'], fx.LIME, bold=True)}")
    if st.get("exc"):
        L.append(f"  {fx.c('raise', fx.RED, bold=True)} → {fx.c(st['exc'], fx.RED)}")
    L.append("")
    L.append(fx.c(tr("─ 출력 ", "─ output "), fx.CYAN, bold=True))
    out_lines = (st["out"] or "").rstrip("\n").splitlines()[-4:]
    L.extend("  " + fx.c(o, fx.WHITE) for o in out_lines) if out_lines else L.append(fx.c(tr("  (아직 없음)", "  (nothing yet)"), fx.DIM))
    if i == len(steps) - 1 and data.get("error"):
        L.append("")
        L.append(fx.c(f"  ✖ {data['error']}", fx.RED, bold=True))
    L.append("")
    L.append(fx.c(tr("→/space 다음  ← 이전  a 자동재생  g 처음  G 끝  q 닫기",
                   "→/space next  ← prev  a autoplay  g start  G end  q close"), fx.DIM))
    return L


def replay(code, keys, title="", sound=None):
    """keys: 이미 cbreak 상태인 Keys 인스턴스."""
    data = trace(code)
    code_lines = code.rstrip("\n").splitlines()
    if not data["steps"]:
        fx.show([fx.c(" KILLCAM ", fx.BLACK, bg=fx.RED, bold=True), "",
                 fx.c(tr("  트레이스 실패: ", "  trace failed: ") + str(data.get("error")), fx.RED), "",
                 fx.c(tr("  아무 키나 누르세요", "  press any key"), fx.DIM)])
        keys.get()
        return
    i, auto = 0, False
    while True:
        fx.show(_frame(code_lines, data, i, title, auto))
        k = keys.get(0.45 if auto else None)
        if k is None and auto:
            if i < len(data["steps"]) - 1:
                i += 1
                if sound:
                    sound.play("tick")
            else:
                auto = False
            continue
        if k in ("q", "ESC", "ENTER") and not (k == "ENTER" and i < len(data["steps"]) - 1):
            return
        if k in ("RIGHT", " ", "l", "n", "ENTER", "DOWN"):
            i = min(len(data["steps"]) - 1, i + 1)
            if sound:
                sound.play("tick")
        elif k in ("LEFT", "h", "b", "UP"):
            i = max(0, i - 1)
        elif k == "a":
            auto = not auto
        elif k == "g":
            i = 0
        elif k == "G":
            i = len(data["steps"]) - 1
