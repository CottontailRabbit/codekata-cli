"""실기 트랙 문제은행 검증: `python3 -m pytest tests` 또는 `python3 tests/test_exam.py`.

- 실전 작업형: Python 레퍼런스와 C++ 모범답안이 무작위 입력에서 같은 출력을 내는가
- 퀴즈: 빈칸형은 정답 보기만 기대 출력을 내는가, 버그 줄형은 그 줄을 고치면 기대 출력이 나오는가
- 카타: 모범답안은 통과하고 오답은 떨어지는가 (C++은 g++ 컴파일)
"""
import random
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codekata import exam, judge  # noqa: E402

HAS_GXX = shutil.which("g++") is not None
SEEDS = 10


def _plain(p):
    return {k: (v[0] if isinstance(v, tuple) else v) for k, v in p.items()}


def test_tasks_python_matches_cpp():
    if not HAS_GXX:
        return
    for t in exam.TASKS:
        tmp = Path(tempfile.mkdtemp())
        c = subprocess.run(["g++", "-std=gnu++17", "-O2", "-o", str(tmp / "sol"), str(exam.TASK_DIR / f"{t['tid']}.cpp")],
                           capture_output=True, text=True)
        assert c.returncode == 0, (t["tid"], c.stderr[-400:])
        for seed in range(SEEDS):
            inp = t["gen"](random.Random(seed))
            (tmp / "input.txt").write_text(inp)
            subprocess.run([str(tmp / "sol")], cwd=tmp, check=True, timeout=10)
            ratio, rows = exam.grade(exam.reference_output(t["tid"], inp), (tmp / "output.txt").read_text())
            assert ratio == 1.0, (t["tid"], seed, [r for r in rows if r[1] != "ok"][:3])


def test_grader_classifies_lines():
    assert exam.compare_line("15.002 49.972", "15.002 49.973") == "ok"      # 반올림 경계 ±1
    assert exam.compare_line("15.002 49.972", "15.00 49.97") == "near"      # 자리수만 다름
    assert exam.compare_line("15.002 49.972", "15.002 49.975") == "bad"
    assert exam.compare_line("0.000 1.5", "-0.000 1.5") == "ok"
    assert exam.compare_line("1,2.50", "1 2.50") == "near"


def test_quizzes_have_one_right_option():
    for q in exam.QUIZ:
        if q["lang"] == "cpp" and not HAS_GXX:
            continue
        ok, why = exam.check_quiz(q)
        assert ok, (q["title"], why)


def test_katas_accept_answer_and_reject_wrong():
    for k in exam.KATA:
        if k["lang"] == "cpp" and not HAS_GXX:
            continue
        p = _plain(k)
        assert judge.judge(p, p["answer"]).ok, p["title"]
        assert not judge.judge(p, "0").ok, p["title"]


def test_clone_lines_rebuild_runnable_code():
    for t in exam.TASKS:
        for lang in ("python", "cpp"):
            code = exam.model_answer(t["tid"], lang)
            rows = exam.clone_lines(code)
            assert any(r[2] for r in rows)
            for raw, indent, target in rows:
                if target is not None:
                    assert len(indent + target) <= 100, (t["tid"], lang, raw)


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
