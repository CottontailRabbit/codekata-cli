"""채점기: Python/JS는 실제 실행해서 값 비교, C++ 실기 카타는 g++ 컴파일 후 실행, 나머지는 정규화 문자열/정규식/키워드 매칭."""
import json
import os
import re
import shutil
import subprocess
import tempfile

from .i18n import tr

PY_RUNNER = r'''
import sys, json, io, contextlib
def canon(v):
    if isinstance(v, bool) or v is None: return [type(v).__name__, v]
    if isinstance(v, (int, str)): return [type(v).__name__, v]
    if isinstance(v, float): return ["float", round(v, 9)]
    if isinstance(v, (set, frozenset)): return ["set", sorted((canon(x) for x in v), key=repr)]
    if isinstance(v, dict): return ["dict", sorted(([canon(k), canon(x)] for k, x in v.items()), key=repr)]
    if isinstance(v, (list, tuple)): return [type(v).__name__, [canon(x) for x in v]]
    return ["repr", repr(v)]
req = json.loads(sys.stdin.read())
results = []
for setup in req["setups"]:
    env = {"__name__": "__kata__"}
    out = io.StringIO()
    r = {"ok": True, "value": None, "shown": "", "stdout": "", "error": None}
    try:
        with contextlib.redirect_stdout(out):
            exec(compile(setup, "<setup>", "exec"), env)
            code = req["code"]
            try:
                expr = compile(code, "<answer>", "eval")
            except SyntaxError:
                expr = None
            if expr is not None:
                v = eval(expr, env)
                r["value"] = canon(v); r["shown"] = repr(v)[:160]
            else:
                exec(compile(code, "<answer>", "exec"), env)
    except BaseException as e:
        r["ok"] = False; r["error"] = f"{type(e).__name__}: {e}"[:200]
    r["stdout"] = out.getvalue()[-2000:]
    results.append(r)
print(json.dumps(results))
'''

JS_RUNNER = r'''
const vm = require("vm"); const util = require("util");
let input = "";
process.stdin.on("data", d => input += d).on("end", () => {
  const req = JSON.parse(input); const results = [];
  for (const setup of req.setups) {
    const out = [];
    const ctx = vm.createContext({ console: { log: (...a) => out.push(a.map(x => typeof x === "string" ? x : util.inspect(x)).join(" ")) } });
    const r = { ok: true, value: null, shown: "", stdout: "", error: null };
    try {
      vm.runInContext(`globalThis.__canon = function c(v) {
        if (v === null || v === undefined || typeof v !== "object") return [typeof v, typeof v === "number" ? +v.toFixed(9) : (v === undefined ? null : v)];
        if (v instanceof Set) return ["set", [...v].map(c).sort((a, b) => JSON.stringify(a) < JSON.stringify(b) ? -1 : 1)];
        if (v instanceof Map) return ["map", [...v].map(([k, x]) => [c(k), c(x)]).sort((a, b) => JSON.stringify(a) < JSON.stringify(b) ? -1 : 1)];
        if (Array.isArray(v)) return ["array", v.map(c)];
        return ["object", Object.keys(v).sort().map(k => [k, c(v[k])])];
      };`, ctx);
      vm.runInContext(setup, ctx, { timeout: 2000 });
      const v = vm.runInContext(req.code, ctx, { timeout: 2000 });
      ctx.__v = v;
      r.value = vm.runInContext("__canon(__v)", ctx);
      r.shown = util.inspect(v).slice(0, 160);
    } catch (e) { r.ok = false; r.error = String(e).slice(0, 200); }
    r.stdout = out.join("\n").slice(-2000);
    results.push(r);
  }
  console.log(JSON.stringify(results));
});
'''

EXEC_LANGS = {"python", "js"}
NP_PRELUDE = "try:\n    import numpy as np\nexcept ImportError:\n    pass\n"

CPP_HARNESS = """#include <bits/stdc++.h>
using namespace std;
int main() {{
{blocks}
}}
"""
CPP_BLOCK = """    {{
{setup}
        auto __v = ({expr});
        cout << setprecision(12) << "@@" << +__v << "\\n";
    }}"""


def run_cpp(expr, setups, timeout=60):
    """setup마다 C++ 표현식 값을 계산. 반환 (values | None, error)."""
    if not shutil.which("g++"):
        return None, "g++ not found"
    expr = expr.strip().rstrip(";").strip()
    blocks = "\n".join(CPP_BLOCK.format(setup="\n".join("        " + x for x in s.splitlines()), expr=expr)
                       for s in setups)
    with tempfile.TemporaryDirectory(prefix="codekata-cpp-") as tmp:
        src = os.path.join(tmp, "k.cpp")
        with open(src, "w") as f:
            f.write(CPP_HARNESS.format(blocks=blocks))
        c = subprocess.run(["g++", "-std=gnu++17", "-O0", "-w", "-o", os.path.join(tmp, "k"), src],
                           capture_output=True, text=True, timeout=timeout)
        if c.returncode != 0:
            errs = [x.split("error:", 1)[1].strip() for x in c.stderr.splitlines() if "error:" in x]
            return None, tr("컴파일 에러: ", "compile error: ") + (errs[0] if errs else c.stderr.strip()[-160:])[:160]
        try:
            r = subprocess.run([os.path.join(tmp, "k")], capture_output=True, text=True, timeout=5, cwd=tmp)
        except subprocess.TimeoutExpired:
            return None, "Timeout"
    vals = [x[2:] for x in r.stdout.splitlines() if x.startswith("@@")]
    if r.returncode != 0 or len(vals) != len(setups):
        return None, f"runtime error (exit {r.returncode})"
    return vals, ""


def warm_cpp(problem):
    """모범답안 기대값을 미리 컴파일·계산해 둔다 (백그라운드용)."""
    if problem.get("_expected") is None:
        vals, _ = run_cpp(problem["answer"], [problem.get("setup", "")] + list(problem.get("tests", [])))
        if vals is not None:
            problem["_expected"] = vals


def _same_num(a, b):
    try:
        x, y = float(a), float(b)
    except ValueError:
        return a == b
    if x != x or y != y:
        return False
    return abs(x - y) <= 1e-9 * max(1.0, abs(x), abs(y))


def judge_cpp(problem, user):
    setups = [problem.get("setup", "")] + list(problem.get("tests", []))
    exp = problem.get("_expected")
    if exp is None:
        exp, err = run_cpp(problem["answer"], setups)
        if exp is None:
            return Verdict(False, "exec", tr("(모범답안 오류) ", "(model answer error) ") + err)
        problem["_expected"] = exp
    got, err = run_cpp(user, setups)
    if got is None:
        return Verdict(False, "exec", err)
    for i, (e, g) in enumerate(zip(exp, got)):
        if not _same_num(e, g):
            return Verdict(False, "exec", tr("숨은 테스트 실패", "hidden test failed") if i else tr("결과: ", "result: ") + g, got[0])
    return Verdict(True, "exec", "", got[0])


def can_execute(lang):
    if lang == "python":
        return True
    if lang == "js":
        return shutil.which("node") is not None
    return False


def run(lang, code, setups, timeout=6):
    """setups마다 code를 실행. 결과 리스트 반환 (실패 시 error 채움)."""
    if lang == "python":
        cmd = ["python3", "-I", "-c", PY_RUNNER]
    else:
        cmd = ["node", "-e", JS_RUNNER]
    env = dict(os.environ, PYTHONHASHSEED="0")
    with tempfile.TemporaryDirectory(prefix="codekata-") as tmp:
        try:
            p = subprocess.run(cmd, input=json.dumps({"code": code, "setups": setups}), capture_output=True,
                               text=True, timeout=timeout, cwd=tmp, env=env)
        except subprocess.TimeoutExpired:
            return [{"ok": False, "error": tr("Timeout: 실행 시간 초과 (무한 루프?)", "Timeout (infinite loop?)"), "value": None, "shown": "",
                     "stdout": ""} for _ in setups]
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        err = (p.stderr or "runner error").strip().splitlines()[-1:] or ["runner error"]
        return [{"ok": False, "error": err[0][:200], "value": None, "shown": "", "stdout": ""} for _ in setups]


def norm(s):
    s = re.sub(r"\s+", "", s.strip())
    return s.rstrip(";")


def string_match(user, answer, accept):
    u = norm(user)
    if not u:
        return False
    if u == norm(answer):
        return True
    for a in accept:
        if a.startswith("re:"):
            try:
                if re.fullmatch(a[3:], u):
                    return True
            except re.error:
                continue
        elif a.startswith("kw:"):
            toks = a[3:].split()
            if toks and all(any(alt in u for alt in t.split("|")) for t in toks):
                return True
        elif norm(a) == u:
            return True
    return False


class Verdict:
    def __init__(self, ok, how, detail="", shown=""):
        self.ok, self.how, self.detail, self.shown = ok, how, detail, shown

    def __repr__(self):
        return f"Verdict({self.ok}, {self.how}, {self.detail!r})"


def judge(problem, user):
    """반환: Verdict. how = exec | string | need_ai"""
    lang = problem["lang"]
    if problem.get("cpp_exec") and shutil.which("g++"):
        return judge_cpp(problem, user)
    if lang in EXEC_LANGS and can_execute(lang):
        setups = [problem.get("setup", "")] + list(problem.get("tests", []))
        if problem.get("track") == "exam" and lang == "python":
            setups = [NP_PRELUDE + x for x in setups]
        exp = problem.get("_expected")
        if exp is None:
            exp = run(lang, problem["answer"], setups)
            problem["_expected"] = exp
        got = run(lang, user, setups)
        first = got[0]
        if not first["ok"]:
            return Verdict(False, "exec", first["error"])
        for e, g in zip(exp, got):
            if not g["ok"]:
                return Verdict(False, "exec", tr("숨은 테스트에서 ", "in a hidden test: ") + g["error"], first["shown"])
            same_val = e["value"] is not None and e["value"] == g["value"]
            same_out = e["value"] is None and e["stdout"] and e["stdout"] == g["stdout"]
            if not (same_val or same_out):
                hidden = e is not exp[0]
                shown = g["shown"] or g["stdout"].strip()[:160]
                return Verdict(False, "exec", tr("숨은 테스트 실패", "hidden test failed") if hidden else
                               tr("결과: ", "result: ") + (shown or tr("(값 없음)", "(no value)")), shown)
        return Verdict(True, "exec", "", first["shown"])
    if string_match(user, problem["answer"], problem.get("accept", [])):
        return Verdict(True, "string")
    return Verdict(False, "need_ai")


def validate_kata(problem):
    """AI가 만든 카타의 모범답안이 실제로 돌아가는지 확인. 실행 불가 언어는 True."""
    lang = problem["lang"]
    if problem.get("cpp_exec"):
        if not shutil.which("g++"):
            return True, ""
        vals, err = run_cpp(problem["answer"], [problem.get("setup", "")] + list(problem.get("tests", [])))
        if vals is None:
            return False, err
        problem["_expected"] = vals
        return True, ""
    if lang not in EXEC_LANGS or not can_execute(lang):
        return True, ""
    setups = [problem.get("setup", "")] + list(problem.get("tests", []))
    res = run(lang, problem["answer"], setups)
    bad = [r for r in res if not r["ok"]]
    if bad:
        return False, bad[0]["error"]
    if all(r["value"] is None and not r["stdout"] for r in res):
        return False, "answer produced nothing"
    problem["_expected"] = res
    return True, ""


def program_output(lang, code, timeout=5):
    """퀴즈 코드 실행 결과(stdout) — 퀴즈 정답 자동 검증용."""
    if lang == "python":
        cmd = ["python3", "-I", "-c", code]
    elif lang == "js" and shutil.which("node"):
        cmd = ["node", "-e", code]
    elif lang == "cpp" and shutil.which("g++"):
        cmd = None
    else:
        return None
    with tempfile.TemporaryDirectory(prefix="codekata-") as tmp:
        if cmd is None:
            src = os.path.join(tmp, "q.cpp")
            with open(src, "w") as f:
                f.write(code)
            c = subprocess.run(["g++", "-std=gnu++17", "-w", "-o", os.path.join(tmp, "q"), src], capture_output=True,
                               text=True, timeout=90)
            if c.returncode != 0:
                return {"ok": False, "out": "", "error": "compile error"}
            cmd = [os.path.join(tmp, "q")]
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=tmp,
                               env=dict(os.environ, PYTHONHASHSEED="0"))
        except subprocess.TimeoutExpired:
            return None
    if p.returncode != 0:
        last = (p.stderr.strip().splitlines() or [""])[-1]
        return {"ok": False, "out": p.stdout, "error": last}
    return {"ok": True, "out": p.stdout, "error": ""}
