"""AI 출제: ChatGPT 로그인(Codex CLI `codex exec`)으로 문제 생성 + 백그라운드 프리페치.

Claude 구독 로그인은 외부 앱에서 쓸 수 없어서, 이미 로그인된 Codex CLI를 통해 ChatGPT 계정으로 호출한다.
"""
import json
import random
import shutil
import subprocess
import tempfile
import threading
import time
from collections import deque
from pathlib import Path

from . import bank, exam, i18n, judge
from .log import LOG

PROBLEM_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["problems"],
    "properties": {
        "problems": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["title", "desc", "setup", "tests", "code", "question", "hint", "answer", "accept",
                             "options", "correct", "explain"],
                "properties": {
                    "title": {"type": "string"},
                    "desc": {"type": "string"},
                    "setup": {"type": "string"},
                    "tests": {"type": "array", "items": {"type": "string"}},
                    "code": {"type": "string"},
                    "question": {"type": "string"},
                    "hint": {"type": "string"},
                    "answer": {"type": "string"},
                    "accept": {"type": "array", "items": {"type": "string"}},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "correct": {"type": "integer"},
                    "explain": {"type": "string"},
                },
            },
        }
    },
}

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["correct", "reason"],
    "properties": {"correct": {"type": "boolean"}, "reason": {"type": "string"}},
}

STYLE = {
    "ko": ("explain 필드는 e스포츠 해설위원 톤의 한국어 1~2문장: 핵심 원리를 짧고 강하게, 코드 요소는 `백틱`으로. "
           "예: \"`[::-1]`은 역방향 슬라이스! 원본과 비교 한 방이면 회문 판정 끝!\""),
    "en": ("explain: 1-2 punchy English sentences in an esports-commentator voice, core idea only, code in `backticks`. "
           "Example: \"`[::-1]` is a reverse slice! One comparison and the palindrome check is done!\""),
}
TEXT_LANG = {"ko": "사용자에게 보이는 모든 텍스트(title, desc, question, options의 설명 문장, hint, explain)는 한국어로.",
             "en": "Write every user-facing text (title, desc, question, option sentences, hint, explain) in English."}

KIND_SPEC = {
    "rush": """타자 러시(코드 따라 치기)용 코드 조각.
- code: 실무에서 자주 쓰는 관용구 1~4줄, 한 줄 70자 이하, ASCII 문자만(한글 문자열 금지), 탭 금지(스페이스 4칸 들여쓰기), 주석 금지
- title: 무엇을 하는 코드인지 짧게
- desc/setup/question/hint/answer: 빈 문자열, tests/accept/options: 빈 배열, correct: 0""",
    "kata": """1~2줄로 푸는 코딩 카타.
- desc: 무엇을 만들지 구체적으로 (변수명 명시). 정답을 그대로 쓰지 말 것
- setup: 문제에 필요한 변수 정의 코드 (사용자에게 보여줌). answer에 필요한 import도 반드시 setup에 포함
- tests: setup과 같은 변수를 다른 값으로 정의한 숨은 테스트 setup 2개 (import 포함, 하드코딩 정답 방지)
- answer: 모범 답안. {expr_rule}
- accept: answer와 다르게 써도 정답인 대표 변형 2~4개 (공백 무관)
- hint: 핵심 함수/문법 키워드만
- code/question: 빈 문자열, options: 빈 배열, correct: 0""",
    "quiz": """5~15줄 코드를 읽고 푸는 4지선다 퀴즈.
- 유형을 섞을 것: 출력 예측 / 버그 찾기 / 에러 예측 / 시간복잡도 / 빈칸 채우기
- code: 그대로 실행 가능한 완전한 프로그램, 함정 1~2개 (스코프, 소유권, 형변환, 우선순위 등)
- question: 질문 한 문장
- options: 서로 다른 보기 4개, 출력 예측이면 보기는 실제 출력 그대로(줄바꿈은 공백으로)
- correct: 정답 보기 인덱스 0~3, 문제마다 위치를 섞을 것
- desc/setup/hint/answer: 빈 문자열, tests/accept: 빈 배열""",
}


EXAM_TOPICS = ("로봇소프트웨어개발기사 실기(작업형, 언어 Python/C/C++)는 'TXT 입력 파일을 읽어 로봇 공식으로 계산하고 "
               "요구한 형식 그대로 결과 파일에 쓰기'가 기본 틀이다. 출제 범위: 2링크 FK/IK/자코비안(MK), DH 파라미터, "
               "3차 다항식·LSPB·BBPB 궤적, Dijkstra/A*/Floyd 경로 탐색, PID 제어, CAN 프레임 파싱(리틀엔디언, 부호), "
               "TCP 모니터링, 파티클 필터, 점유 격자 지도, 파일 입출력과 인코딩(utf-8/cp949/utf-8-sig), 출력 형식 지정. "
               "자주 틀리는 함정: 도/라디안, atan2 인자 순서, arange 끝점, int 나눗셈, round 규칙, -0.000, signed 바이트, "
               "최소/최대 힙 방향, 격자 [행][열].")

EXAM_SPEC = {
    "quiz": """위 실기 범위의 공식·함수·형식 함정을 묻는 4지선다 퀴즈.
- code: 그대로 실행 가능한 완전한 프로그램 5~15줄 (Python은 math/numpy만, C++은 표준 라이브러리만, 파일 입출력 없이)
- question: 대부분 출력 예측("출력은?"), 가끔 공식/개념 선택
- options: 서로 다른 보기 4개, 출력 예측이면 실제 출력 그대로(줄바꿈은 공백으로)
- correct: 정답 인덱스 0~3, 문제마다 위치를 섞을 것
- desc/setup/hint/answer: 빈 문자열, tests/accept: 빈 배열""",
    "kata": """위 실기 범위의 공식 한 줄을 쓰는 카타.
- desc: 무엇을 계산할지 (변수명·단위 명시). 정답을 그대로 쓰지 말 것
- setup: {setup_rule}
- tests: setup과 같은 변수를 다른 값으로 정의한 숨은 테스트 setup 2개
- answer: {expr_rule}
- hint: 핵심 공식/함수만, accept: 빈 배열, code/question: 빈 문자열, options: 빈 배열, correct: 0""",
}


def _exam_rules(lang):
    if lang == "cpp":
        return ("main() 안에 들어갈 C++ 선언문들 (예: double L1 = 1.0, t1 = 30 * M_PI / 180;). #include 금지 — "
                "<bits/stdc++.h>와 using namespace std;가 이미 있음",
                "반드시 값을 내는 단일 C++ 표현식 (세미콜론·대입·cout 금지). 결과는 숫자 하나")
    return ("변수 정의 Python 코드, 필요한 import(math 등) 포함", "반드시 값을 돌려주는 단일 Python 표현식 (print·대입 금지)")


def _expr_rule(lang):
    if lang == "python":
        return "반드시 값을 돌려주는 단일 Python 표현식 (print 금지, 대입문 금지)"
    if lang == "js":
        return "반드시 값을 돌려주는 단일 JavaScript 표현식 (console.log 금지, 세미콜론 없이)"
    return "1~2줄 코드"


class CodexProvider:
    """`codex exec` — ChatGPT 계정 로그인으로 동작."""
    name = "codex"

    def __init__(self, model="", effort="low"):
        self.model = model
        self.effort = effort
        self.bin = shutil.which("codex")
        self._status = None

    def available(self):
        if not self.bin:
            return False
        if self._status is None:
            try:
                p = subprocess.run([self.bin, "login", "status"], capture_output=True, text=True, timeout=15)
                self._status = (p.stdout + p.stderr).strip()
            except (OSError, subprocess.TimeoutExpired) as e:
                self._status = f"error: {e}"
        return "Logged in" in self._status

    def status(self):
        if not self.bin:
            return i18n.tr("codex CLI 없음 (npm i -g @openai/codex)", "codex CLI not found (npm i -g @openai/codex)")
        self.available()
        return self._status

    def call(self, prompt, schema, timeout=180):
        with tempfile.TemporaryDirectory(prefix="codekata-ai-") as tmp:
            sp, op = Path(tmp) / "schema.json", Path(tmp) / "out.json"
            sp.write_text(json.dumps(schema))
            cmd = [self.bin, "exec", "--skip-git-repo-check", "--ephemeral", "--sandbox", "read-only",
                   "--color", "never", "-c", f"model_reasoning_effort={self.effort}",
                   "--output-schema", str(sp), "-o", str(op)]
            if self.model:
                cmd += ["-m", self.model]
            cmd.append(prompt)
            t0 = time.monotonic()
            p = subprocess.run(cmd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, cwd=tmp)
            ms = int((time.monotonic() - t0) * 1000)
            if p.returncode != 0 or not op.exists():
                tail = (p.stderr or p.stdout).strip().splitlines()[-3:]
                raise RuntimeError(f"codex exec rc={p.returncode}: {' | '.join(tail)}")
            text = op.read_text().strip()
            LOG.dbg.debug("codex raw (%dms): %s", ms, text[:4000])
            return json.loads(text), ms

    def generate(self, kind, lang, n, avoid, track="code"):
        label = bank.LANG_LABEL.get(lang, lang)
        if track == "exam":
            setup_rule, expr_rule = _exam_rules(lang)
            spec = EXAM_SPEC[kind].replace("{setup_rule}", setup_rule).replace("{expr_rule}", expr_rule)
            spec = f"{EXAM_TOPICS}\n{spec}"
        else:
            spec = KIND_SPEC[kind].replace("{expr_rule}", _expr_rule(lang))
        avoid_s = ", ".join(avoid[-40:]) or "(없음)"
        ui = i18n.UI
        who = f"로봇소프트웨어개발기사 실기 대비 {label}" if track == "exam" else f"{label} 코딩 카타"
        prompt = (f"너는 {who} 출제자다. 초급~중급 난이도로 서로 다른 주제의 문제 {n}개를 만들어라.\n"
                  f"[문제 형식]\n{spec}\n[해설 스타일]\n{STYLE[ui]}\n[언어]\n{TEXT_LANG[ui]}\n"
                  f"[중복 금지 제목]\n{avoid_s}\n"
                  "파일을 읽거나 명령을 실행하지 말고, 스키마에 맞는 JSON만 출력하라.")
        data, ms = self.call(prompt, PROBLEM_SCHEMA)
        return data.get("problems", []), ms

    def judge(self, problem, user):
        label = bank.LANG_LABEL.get(problem["lang"], problem["lang"])
        prompt = (f"{label} 카타 채점. 문제: {problem['title']} — {problem.get('desc', '')}\n"
                  f"setup:\n{problem.get('setup', '')}\n모범답안: {problem['answer']}\n제출: {user}\n"
                  "제출이 문제 요구를 정확히 만족하는지(컴파일/동작 기준, 스타일 무관) 판정하고 reason은 " +
                  ("English commentator-style single sentence" if i18n.UI == "en" else "한국어 해설위원 톤 한 문장") +
                  ". 명령 실행 금지, JSON만.")
        data, ms = self.call(prompt, JUDGE_SCHEMA, timeout=90)
        return bool(data.get("correct")), data.get("reason", ""), ms


def normalize(raw, kind, lang, track="code"):
    p = {"kind": kind, "lang": lang, "source": "ai", "track": track}
    if track == "exam" and kind == "kata" and lang == "cpp":
        p["cpp_exec"] = True
    for k in ("title", "desc", "setup", "code", "question", "hint", "answer", "explain"):
        p[k] = str(raw.get(k, "") or "")
    for k in ("tests", "accept", "options"):
        p[k] = [str(x) for x in raw.get(k, []) or []]
    p["correct"] = int(raw.get("correct", 0) or 0)
    p["id"] = bank.pid(p)
    return p


def validate(p):
    """AI 문제 품질 검사. (ok, reason). 퀴즈는 실행 결과로 정답 인덱스를 교정하기도 한다."""
    if not p["title"]:
        return False, "no title"
    if p["kind"] == "rush":
        p["code"] = p["code"].replace("\t", "    ").rstrip()
        lines = p["code"].splitlines()
        if not lines or len(lines) > 6 or max(len(x) for x in lines) > 90:
            return False, "rush shape"
        if not all(x.isascii() for x in lines):
            return False, "rush non-ascii"
        return True, ""
    if p["kind"] == "kata":
        if not p["answer"] or not p["desc"]:
            return False, "kata empty"
        return judge.validate_kata(p)
    if p["kind"] == "quiz":
        opts = p["options"]
        if len(opts) != 4 or len(set(opts)) != 4 or not (0 <= p["correct"] < 4) or not p["code"]:
            return False, "quiz shape"
        if p["lang"] in ("python", "js", "cpp") and ("출력" in p["question"] or "output" in p["question"].lower()
                                                      or "print" in p["question"].lower()):
            r = judge.program_output(p["lang"], p["code"])
            if r and r["ok"]:
                out = " ".join(r["out"].split())
                hits = [i for i, o in enumerate(opts) if " ".join(o.split()) == out]
                if len(hits) == 1 and hits[0] != p["correct"]:
                    LOG.ev("ai_quiz_fixed", title=p["title"], was=p["correct"], now=hits[0])
                    p["correct"] = hits[0]
                elif not hits:
                    return False, f"quiz output mismatch: {out[:60]}"
        return True, ""
    return False, "kind"


class ProblemSource:
    """출제기. AI 큐에 문제가 있으면 AI 문제, 없으면 문제은행에서 즉시 출제하고 뒤에서 AI 프리페치."""

    def __init__(self, provider, history, prefetch=3, batch=4):
        self.provider = provider
        self.history = history
        self.prefetch = prefetch
        self.batch = batch
        self.queues = {}
        self.wanted = set()
        self.inflight = set()
        self.cv = threading.Condition()
        self.stats = {"ai_calls": 0, "ai_fail": 0, "ai_ms": 0, "ai_dropped": 0, "served_ai": 0, "served_bank": 0}
        self.last_error = ""
        self.alive = provider is not None
        self._bank_used = set()
        self.task_pick = None             # codekata exam -t <id> 로 실전 문제 고정
        if self.alive:
            for i in range(2):
                threading.Thread(target=self._worker, name=f"prefetch-{i}", daemon=True).start()

    def warm(self, kinds, langs, track="code"):
        with self.cv:
            for k in kinds:
                if k == "task":                     # 실전 작업형은 문제은행 + 레퍼런스 풀이로만 출제
                    continue
                for lang in langs:
                    self.wanted.add((k, lang, track))
            self.cv.notify_all()

    def clear(self):
        """UI 언어가 바뀌면 이미 받아 둔 AI 문제를 버린다."""
        with self.cv:
            self.queues.clear()
            self.cv.notify_all()

    def qsize(self):
        return sum(len(q) for q in self.queues.values())

    def _seen(self, lang):
        return self.history["seen"].setdefault(lang, [])

    def next(self, kind, lang, track="code"):
        if kind == "task":
            p = self._exam_task(lang)
            self.stats["served_bank"] += 1
            return p
        key = (kind, lang, track)
        with self.cv:
            self.wanted.add(key)
            q = self.queues.get(key)
            p = None
            while q:
                cand = q.popleft()
                if cand["title"] not in self._seen(lang):
                    p = cand
                    break
            self.cv.notify_all()
        if p:
            self.stats["served_ai"] += 1
        else:
            p = bank.localize(self._from_bank(kind, lang, track))
            self.stats["served_bank"] += 1
        self._seen(lang).append(p.get("title_ko") or p["title"])
        return p

    def _exam_task(self, lang):
        tid = self.task_pick
        if not tid:
            seen = self.history["seen"].setdefault("exam-task", [])
            ids = [t["tid"] for t in exam.TASKS]
            fresh = [t for t in ids if t not in self._bank_used and t not in seen[-6:]] or \
                    [t for t in ids if t not in self._bank_used] or ids
            tid = random.choice(fresh)
            seen.append(tid)
        self._bank_used.add(tid)
        return exam.make_task(tid, lang, seed=random.randrange(1 << 30))

    def _from_bank(self, kind, lang, track="code"):
        import copy
        src = exam.QUIZ + exam.KATA if track == "exam" else bank.ALL
        pool = [p for p in src if p["kind"] == kind and p["lang"] == lang] or \
               [p for p in src if p["kind"] == kind]
        seen = set(self._seen(lang)[-25:])
        fresh = [p for p in pool if p["id"] not in self._bank_used and p.get("title_ko", p["title"]) not in seen] or \
                [p for p in pool if p["id"] not in self._bank_used] or pool
        p = copy.deepcopy(random.choice(fresh))
        self._bank_used.add(p["id"])
        return p

    def _pick_need(self):
        needs = [k for k in self.wanted if len(self.queues.get(k, ())) < self.prefetch and k not in self.inflight]
        if not needs:
            return None
        needs.sort(key=lambda k: len(self.queues.get(k, ())))
        return needs[0]

    def _worker(self):
        while True:
            with self.cv:
                key = self._pick_need()
                while key is None or not self.alive:
                    self.cv.wait(5)
                    key = self._pick_need()
                self.inflight.add(key)
            kind, lang, track = key
            try:
                avoid = list(self._seen(lang)) + [p["title"] for p in self.queues.get(key, ())]
                raws, ms = self.provider.generate(kind, lang, self.batch, avoid, track)
                self.stats["ai_calls"] += 1
                self.stats["ai_ms"] += ms
                good = []
                for raw in raws:
                    p = normalize(raw, kind, lang, track)
                    ok, why = validate(p)
                    if ok:
                        good.append(p)
                    else:
                        self.stats["ai_dropped"] += 1
                        LOG.ev("ai_drop", kind=kind, lang=lang, title=p["title"], why=why)
                LOG.ev("ai_batch", ok=True, kind=kind, lang=lang, ms=ms, got=len(raws), kept=len(good))
                with self.cv:
                    self.queues.setdefault(key, deque()).extend(good)
            except Exception as e:  # noqa: BLE001 — 프리페치는 절대 게임을 죽이면 안 됨
                self.stats["ai_fail"] += 1
                self.last_error = str(e)[:200]
                LOG.ev("ai_batch", ok=False, kind=kind, lang=lang, error=self.last_error)
                if self.stats["ai_fail"] >= 3 and self.stats["ai_calls"] == 0:
                    self.alive = False  # 로그인 안 됨 등: 조용히 오프라인 전환
                time.sleep(3)
            finally:
                with self.cv:
                    self.inflight.discard(key)
