"""게임 엔진: 보스전 · 콤보 · 하트 · 스테이지(타자 러시 / 카타 / 퀴즈) · 결과 화면."""
import random
import re
import subprocess
import threading
import time
import uuid
from collections import deque
from datetime import date, datetime
from pathlib import Path

from . import VERSION, bank, caster, exam, fx, judge, tracer
from .i18n import pick, tr
from .log import LOG
from .store import RANKED_STAGES

BOSSES = [(("NullPointer 드래곤", "NullPointer Dragon"), fx.RED), (("Segfault 골렘", "Segfault Golem"), fx.ORANGE),
          (("무한루프 히드라", "Infinite-Loop Hydra"), fx.PURPLE), (("Off-by-one 고블린 킹", "Off-by-one Goblin King"), fx.GOLD),
          (("레이스컨디션 쌍둥이", "Race-Condition Twins"), fx.CYAN), (("메모리릭 슬라임", "Memory-Leak Slime"), fx.LIME),
          (("Heisenbug 유령", "Heisenbug Ghost"), fx.PINK), (("의존성 지옥견", "Dependency Hellhound"), 202),
          (("Merge Conflict 키메라", "Merge-Conflict Chimera"), 99)]
EXAM_BOSSES = [(("특이점 골렘", "Singularity Golem"), fx.RED), (("짐벌락 드래곤", "Gimbal-Lock Dragon"), fx.ORANGE),
               (("오버슈트 히드라", "Overshoot Hydra"), fx.PURPLE), (("atan 사분면 유령", "atan Quadrant Ghost"), fx.PINK),
               (("int 나눗셈 고블린", "Int-Division Goblin"), fx.GOLD), (("CP949 인코딩 슬라임", "CP949 Encoding Slime"), fx.LIME),
               (("적분 와인드업 키메라", "Integral-Windup Chimera"), fx.CYAN), (("-0.000 망령", "The -0.000 Wraith"), 202)]
MODES = {"mix": ("믹스", "Mix"), "rush": ("타자 러시", "Type Rush"), "kata": ("카타", "Kata"), "quiz": ("퀴즈", "Quiz"),
         "exam": ("실기 랭크전", "Exam ranked"), "exam-quiz": ("실기 퀴즈", "Exam quiz"),
         "exam-kata": ("실기 카타", "Exam kata"), "exam-task": ("실기 작업형", "Exam task"),
         "exam-clone": ("실기 클론코딩", "Exam clone coding")}
KIND_ICON = {"rush": (("⌨ 타자 러시", "⌨ TYPE RUSH"), fx.CYAN), "kata": (("✎ 카타", "✎ KATA"), fx.LIME),
             "quiz": (("? 퀴즈", "? QUIZ"), fx.PINK), "task": (("⚙ 실전 작업형", "⚙ EXAM TASK"), fx.ORANGE),
             "clone": (("⧉ 줄별 클론코딩", "⧉ LINE-BY-LINE CLONE"), fx.SKY)}


def mode_label(mode):
    return pick(MODES.get(mode, mode))


def kind_icon(kind):
    label, color = KIND_ICON[kind]
    return pick(label), color
QUIZ_LIMIT = 60

KEYWORDS = {
    "python": "def return if elif else for while in not and or is None True False class import from as with try "
              "except finally raise lambda yield async await global nonlocal pass break continue print len range",
    "js": "const let var function return if else for while of in new class this typeof instanceof async await "
          "true false null undefined export import from throw try catch console",
    "rust": "fn let mut if else match for while loop in return struct enum impl trait pub use mod Some None Ok Err "
            "self Self true false as ref move where dyn println vec",
    "cpp": "int double float char bool void auto const return if else for while class struct template typename "
           "std include namespace using new delete true false nullptr unsigned static sizeof",
    "go": "func var const if else for range return go chan make defer type struct interface map nil package import",
}
_TOKEN = re.compile(r'(?P<str>"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|`[^`]*`)|(?P<com>#(?!include)[^\n]*|//[^\n]*)'
                    r'|(?P<num>\b\d+(?:\.\d+)?\b)|(?P<word>[A-Za-z_]\w*)')


def highlight(line, lang):
    kws = set(KEYWORDS.get(lang, KEYWORDS["python"]).split())

    def sub(m):
        t = m.group()
        if m.group("str"):
            return fx.c(t, 150)
        if m.group("com"):
            return fx.c(t, fx.DIM)
        if m.group("num"):
            return fx.c(t, 141)
        if m.group("word") and len(t) >= 4 and set(t) == {"_"}:          # 퀴즈 빈칸
            return fx.c(t, fx.BLACK, bg=fx.YELLOW, bold=True)
        if m.group("word") and t in kws:
            return fx.c(t, 205, bold=True)
        return fx.c(t, 253)
    if lang == "python" and line.lstrip().startswith("#"):
        return fx.c(line, fx.DIM)
    return _TOKEN.sub(sub, line)


def ticks(text):
    return re.sub(r"`([^`]+)`", lambda m: fx.c(m.group(1), fx.CYAN, bold=True) + "\x1b[1;38;5;255m", text)


def wrap(text, w):
    out = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = f"{cur} {word}" if cur else word
            if fx.width(cand) > w and cur:
                out.append(cur)
                cur = word
            else:
                cur = cand
        out.append(cur)
    return out


def code_block(code, lang):
    return [fx.c(f"{i:>2} │ ", fx.DARK) + highlight(line, lang) for i, line in enumerate(code.split("\n"), 1)]


class Quit(Exception):
    pass


class Game:
    def __init__(self, cfg, source, provider, sound, keys, mode="mix", langs=("python",), stages=RANKED_STAGES,
                 debug=False, player="player"):
        self.cfg, self.src, self.provider, self.snd, self.keys = cfg, source, provider, sound, keys
        self.mode, self.langs, self.stages, self.debug, self.player = mode, list(langs), stages, debug, player
        self.track = "exam" if mode.startswith("exam") else "code"
        if self.track == "exam":
            self.ranked = mode == "exam" and stages == exam.EXAM_STAGES
        else:
            self.ranked = stages == RANKED_STAGES
        self.sid = uuid.uuid4().hex[:8]
        self.score = self.combo = self.max_combo = 0
        self.hearts = 3
        self.hits = self.misses = self.crits = self.kos = 0
        self.slips = 0  # 카타 오답 시도/힌트 — FLAWLESS 판정용
        self.keys_ok = self.keys_bad = 0
        self.rush_chars, self.rush_secs = 0, 0.0
        self.stage = 0
        self.cur_lang = self.langs[0]
        self.body, self.prompt = [], ""
        self.feed = deque(maxlen=6)
        self.results = []
        self.boss = None
        self.t0 = time.monotonic()
        self.new_boss()

    # ─── 상태 ──────────────────────────────────────────────

    @property
    def mult(self):
        return 1 + 0.25 * min(self.combo, 12)

    def new_boss(self):
        pool = EXAM_BOSSES if self.track == "exam" else BOSSES
        choices = [(pick(name), color) for name, color in pool if pick(name) != self.boss]
        self.boss, self.boss_color = random.choice(choices)
        self.boss_max = int(self.stages * 470 * (1 + 0.6 * self.kos))
        self.boss_hp = self.disp_hp = self.boss_max
        self.low_called = False

    # ─── 렌더링 ────────────────────────────────────────────

    def hud(self):
        cols, _ = fx.size()
        w = max(60, min(cols - 6, 100))
        lang = self.cur_lang
        left = (fx.c(" CODEKATA ", fx.BLACK, bold=True, bg=fx.GOLD) + " " +
                fx.c(bank.LANG_LABEL.get(lang, lang), bank.LANG_COLOR.get(lang, fx.WHITE), bold=True) +
                fx.c(f"  STAGE {self.stage}/{self.stages}", fx.WHITE, bold=True) +
                (fx.c("  RANKED", fx.RED, bold=True) if self.ranked else fx.c(tr("  연습", "  PRACTICE"), fx.DIM)) +
                (fx.c(tr("  로봇SW개발기사 실기", "  Robot SW exam"), fx.ORANGE, bold=True) if self.track == "exam" else ""))
        hearts = " ".join(fx.c("♥", fx.RED, bold=True) if i < self.hearts else fx.c("♡", fx.DARK) for i in range(3))
        right = hearts + "   " + fx.c("SCORE ", fx.DIM) + fx.c(fx.fmt(self.score), fx.GOLD, bold=True)
        l1 = fx.pad(left, w - fx.width(right)) + right
        frac = max(0.0, self.disp_hp) / self.boss_max
        barw = max(10, w - fx.width(self.boss) - 30)
        l2 = (fx.c("BOSS ", fx.DIM) + fx.c(self.boss, self.boss_color, bold=True) + "  " +
              fx.bar(frac, barw, fx.hp_color(frac)) + " " +
              fx.c(f"{fx.fmt(max(0, self.disp_hp))}/{fx.fmt(self.boss_max)}", fx.GREY))
        if self.combo:
            cc = caster.combo_color(self.combo)
            meter = fx.c("▰" * min(self.combo, 12), cc) + fx.c("▱" * (12 - min(self.combo, 12)), fx.DARK)
            l3 = fx.c(f"COMBO x{self.combo}", cc, bold=True) + "  " + meter + fx.c(f"  DMG x{self.mult:.2f}", cc)
        else:
            l3 = fx.c("COMBO -", fx.DARK)
        el = int(time.monotonic() - self.t0)
        l3 = fx.pad(l3, w - 6) + fx.c(f"{el // 60:02d}:{el % 60:02d}", fx.DIM)
        out = [l1, l2, l3]
        if self.debug:
            s = self.src.stats
            out.append(fx.c(f"[debug] sid={self.sid} q={self.src.qsize()} ai={s['ai_calls']}✓/{s['ai_fail']}✗ "
                            f"drop={s['ai_dropped']} served ai/bank={s['served_ai']}/{s['served_bank']} | "
                            f"{(LOG.recent[-1] if LOG.recent else '')}", fx.DIM))
        out.append(fx.c("─" * w, fx.DARK))
        return out

    def frame(self, with_prompt=True):
        _, rows = fx.size()
        hud = self.hud()
        feed = list(self.feed)
        tail = [""] + feed + ([""] + [self.prompt] if with_prompt and self.prompt else [])
        body = list(self.body)
        room = rows - 2 - len(hud) - 1 - len(tail)
        if len(body) > room and len(feed) > 2:
            tail = [""] + feed[-2:] + ([""] + [self.prompt] if with_prompt and self.prompt else [])
            room = rows - 2 - len(hud) - 1 - len(tail)
        if len(body) > room:
            body = body[:max(3, room)]
        return hud + [""] + body + tail

    def render(self):
        fx.show(self.frame())

    def say(self, who, text, tw=True):
        cols, _ = fx.size()
        w = max(40, min(cols - 6, 100) - 10)
        if who == "c":
            label = fx.c(tr("▶ 캐스터 ", "▶ CASTER "), fx.ORANGE, bold=True)
            parts = [fx.c(p, 255, bold=True) for p in wrap(text, w)]
        else:
            label = fx.c(tr("◆ 해설   ", "◆ ANALYST "), fx.CYAN, bold=True)
            parts = ["\x1b[1;38;5;255m" + ticks(p) + fx.RESET for p in wrap(text, w)]
        lines = [(label if i == 0 else " " * fx.width(label)) + p for i, p in enumerate(parts)]
        if not tw or not fx.S.fx:
            self.feed.extend(lines)
            self.render()
            return
        final = (list(self.feed) + lines)[-self.feed.maxlen:]
        new = lines[-len(final):]
        self.feed = deque(final[:len(final) - len(new)], maxlen=self.feed.maxlen)
        fx.show(self.frame(with_prompt=False))
        for ln in new:
            fx.typewriter_line("", ln, cps=220)
            self.feed.append(ln)
        self.render()

    # ─── 타격 연출 ────────────────────────────────────────

    def drain_hp(self, frames=12):
        start, end = self.disp_hp, max(0, self.boss_hp)
        for i in range(1, frames + 1):
            self.disp_hp = start + (end - start) * (i / frames) ** 0.6
            self.render()
            fx.sleep(0.016)
        self.disp_hp = end
        self.render()

    def deal(self, base, crit=False, label="HIT", event=None, **kw):
        dmg = int(base * self.mult * (1.5 if crit else 1.0))
        self.score += dmg
        self.boss_hp -= dmg
        self.hits += 1
        self.crits += int(crit)
        self.combo += 1
        self.max_combo = max(self.max_combo, self.combo)
        self.snd.play("crit" if crit else "hit")
        if crit:
            fx.flash(fx.WHITE, 40)
        fx.shake(4 if crit else 2, 8 if crit else 5)
        color = [fx.GOLD, fx.YELLOW, fx.ORANGE, fx.YELLOW, fx.GOLD] if crit else [fx.WHITE]
        fx.slam(label, color, hold=0.22 if not crit else 0.32, shake_power=3 if crit else 2,
                sub=f"-{fx.fmt(dmg)}", sub_color=fx.GOLD)
        self.drain_hp()
        LOG.ev("hit", dmg=dmg, crit=crit, label=label, combo=self.combo, boss_hp=self.boss_hp, **kw)
        self.say("c", caster.say(event or ("crit" if crit else "hit"), dmg=fx.fmt(dmg), boss=self.boss, **kw))
        ce = caster.combo_event(self.combo)
        if ce:
            cc = caster.combo_color(self.combo)
            self.snd.play("combo")
            fx.slam(f"{self.combo} COMBO", [cc] if self.combo < 15 else fx.RAINBOW, hold=0.3, shake_power=2)
            self.say("c", caster.say(ce, n=self.combo))
        if 0 < self.boss_hp < self.boss_max * 0.25 and not self.low_called:
            self.low_called = True
            self.say("c", caster.say("boss_low", boss=self.boss))
        if self.boss_hp <= 0:
            self.ko()
        return dmg

    def miss(self, lose_heart=True, reason="miss"):
        broken = self.combo
        self.combo = 0
        self.misses += 1
        self.snd.play("miss")
        fx.flash(fx.RED, 60)
        fx.shake(4, 9)
        fx.slam("MISS", [fx.RED], hold=0.2, shake_power=3)
        LOG.ev("miss", reason=reason, combo_broken=broken, lose_heart=lose_heart)
        if broken >= 3:
            self.say("c", caster.say("combo_break", n=broken))
        else:
            self.say("c", caster.say("miss", boss=self.boss))
        if lose_heart:
            self.hearts -= 1
            self.snd.play("heart")
            for i in range(3):
                saved = self.hearts
                self.hearts = saved + (1 if i % 2 == 0 else 0)
                self.render()
                fx.sleep(0.09)
                self.hearts = saved
            self.render()
            if self.hearts == 1:
                self.say("c", caster.say("last_heart"))
            elif self.hearts > 1:
                self.say("c", caster.say("heart", hearts=self.hearts, boss=self.boss))

    def ko(self):
        self.kos += 1
        bonus = 1500 + 500 * self.hearts
        self.score += bonus
        self.snd.play("ko")
        fx.flash(fx.WHITE, 80)
        fx.flash(self.boss_color, 60)
        fx.shake(6, 12)
        fx.slam("K.O.", fx.RAINBOW, hold=0.7, shake_power=5, sub=tr(f"{self.boss} 격파!  +{fx.fmt(bonus)}", f"{self.boss} defeated!  +{fx.fmt(bonus)}"),
                sub_color=fx.GOLD)
        LOG.ev("ko", boss=self.boss, bonus=bonus, kos=self.kos)
        self.say("c", caster.say("ko", boss=self.boss))
        if self.stage < self.stages:
            self.new_boss()
            self.render()
            self.say("c", caster.say("next_boss", boss=self.boss))

    # ─── 판정 (AI VAR) ────────────────────────────────────

    def var_judge(self, p, user):
        v = judge.judge(p, user)
        if v.how != "need_ai":
            return v
        if not (self.provider and self.cfg.get("ai_judge") and self.src.alive):
            return judge.Verdict(False, "string", tr("모범답안/허용 패턴과 불일치", "does not match the model answer"))
        self.snd.play("var")
        self.say("c", caster.say("var"))
        box = {}

        def work():
            try:
                box["r"] = self.provider.judge(p, user)
            except Exception as e:  # noqa: BLE001
                box["e"] = str(e)
        th = threading.Thread(target=work, daemon=True)
        th.start()
        spin = "◐◓◑◒"
        i = 0
        while th.is_alive():
            self.prompt = fx.c(f"{spin[i % 4]} " + tr("VAR 판독 중... (ChatGPT)", "VAR review in progress... (ChatGPT)"), fx.YELLOW, bold=True)
            self.render()
            i += 1
            th.join(0.12)
        if "e" in box:
            LOG.ev("var", ok=False, error=box["e"])
            return judge.Verdict(False, "string", tr("VAR 실패 → 모범답안과 불일치로 판정", "VAR failed → judged as a mismatch"))
        ok, reason, ms = box["r"]
        LOG.ev("var", ok=ok, ms=ms, reason=reason)
        self.say("c", caster.say("var_ok" if ok else "var_no"))
        if reason:
            self.say("a", reason)
        return judge.Verdict(ok, "ai", reason)

    # ─── 스테이지: 타자 러시 ──────────────────────────────

    def stage_rush(self, p):
        target = p["code"].replace("\t", "    ").rstrip()
        lines = target.split("\n")
        n = len(target)
        state = [0] * n
        err_at = set()
        pos, ok, bad, streak, best = 0, 0, 0, 0, 0
        t_start = None
        err_now = False

        def skip_ws():
            nonlocal pos
            while pos < n and target[pos] == " " and _at_indent(pos):
                state[pos] = 1
                pos += 1

        def _at_indent(i):
            ls = target.rfind("\n", 0, i) + 1
            return target[ls:i].strip(" ") == ""

        def body():
            icon, col = kind_icon("rush")
            out = [fx.c(icon, col, bold=True) + "  " + fx.c(p["title"], fx.WHITE, bold=True) +
                   fx.c(f"   [{p.get('source', 'bank')}]", fx.DARK)]
            if p.get("desc"):
                out.append(fx.c(tr("무슨 코드? ▸ ", "What it does ▸ "), fx.SKY, bold=True) + fx.c(p["desc"], fx.SKY))
            out += [fx.c(tr("보이는 코드를 그대로 치세요. 들여쓰기 자동 · 오타는 고쳐야 전진 · Tab=공백 4칸 · ESC 패스",
                           "Type the code exactly. Auto-indent · fix typos to advance · Tab = 4 spaces · ESC skip"),
                        fx.DIM), ""]
            idx = 0
            for li, line in enumerate(lines):
                s = fx.c(f"{li + 1:>2} │ ", fx.DARK)
                for ch in line:
                    s += cell(idx, ch)
                    idx += 1
                if li < len(lines) - 1:
                    if idx == pos:
                        s += fx.c("↵", fx.BLACK, bg=fx.RED if err_now else fx.YELLOW, bold=True)
                    idx += 1
                out.append(s)
            el = (time.monotonic() - t_start) if t_start else 0.0
            wpm = (ok / 5) / (el / 60) if el > 0.5 else 0
            acc = ok / max(1, ok + bad) * 100
            out += ["", fx.c("WPM ", fx.DIM) + fx.c(f"{wpm:5.0f}", fx.CYAN, bold=True) +
                    fx.c("   ACC ", fx.DIM) + fx.c(f"{acc:5.1f}%", fx.LIME if acc >= 95 else fx.YELLOW, bold=True) +
                    fx.c("   TIME ", fx.DIM) + fx.c(f"{el:5.1f}s", fx.WHITE) +
                    fx.c("   STREAK ", fx.DIM) + fx.c(f"{streak}", caster.combo_color(streak // 8), bold=True) +
                    fx.c("   " + fx.bar(pos / n, 20, fx.CYAN, ch_full="■", ch_empty="·"), fx.WHITE)]
            return out

        def cell(i, ch):
            if i < pos:
                return fx.c(ch, fx.LIME if state[i] == 1 else fx.ORANGE, bold=state[i] == 2)
            if i == pos:
                return fx.c(ch if ch != " " else "·", fx.BLACK, bg=fx.RED if err_now else fx.YELLOW, bold=True)
            return fx.c(ch, 240)

        self.prompt = ""
        skip_ws()
        while pos < n:
            self.body = body()
            self.render()
            k = self.keys.get(0.5 if t_start else None)
            if k is None:
                continue
            if k == "ESC":
                self.say("c", caster.say("skip"))
                self.miss(lose_heart=False, reason="rush_skip")
                self.after(p)
                return {"ok": False, "skipped": True}
            if t_start is None:
                t_start = time.monotonic()
            exp = target[pos]
            good = k == exp or (k == "ENTER" and exp == "\n") or (k == "TAB" and exp == " ")
            if good:
                err_now = False
                if k == "TAB":
                    for _ in range(4):
                        if pos < n and target[pos] == " ":
                            state[pos] = 2 if pos in err_at else 1
                            pos += 1
                else:
                    state[pos] = 2 if pos in err_at else 1
                    pos += 1
                if exp == "\n":
                    skip_ws()
                ok += 1
                streak += 1
                best = max(best, streak)
                self.keys_ok += 1
                chip = int(3 * (1 + min(streak, 100) / 50))
                self.boss_hp -= chip
                self.disp_hp = max(0, self.boss_hp)
                self.score += chip
                if streak in (25, 50) or (streak > 0 and streak % 100 == 0):
                    self.snd.play("streak")
                    self.body = body()
                    self.say("c", caster.say("streak", n=streak), tw=False)
                else:
                    self.snd.play("key")
            else:
                if k in ("BACKSPACE", "LEFT", "RIGHT", "UP", "DOWN"):
                    continue
                bad += 1
                self.keys_bad += 1
                err_at.add(pos)
                err_now = True
                if streak >= 20:
                    self.say("c", caster.say("streak_break", n=streak), tw=False)
                streak = 0
                self.snd.play("typo")
                self.body = body()
                self.render()
                fx.shake(1, 3)
        self.body = body()
        el = max(0.5, time.monotonic() - (t_start or time.monotonic()))
        wpm = (ok / 5) / (el / 60)
        acc = ok / max(1, ok + bad)
        self.rush_chars += ok
        self.rush_secs += el
        LOG.ev("rush_done", title=p["title"], chars=n, ok=ok, bad=bad, wpm=round(wpm, 1), acc=round(acc, 3),
               secs=round(el, 2), best_streak=best)
        speed = max(0.6, min(2.0, wpm / 40))
        if acc >= 0.9:
            perfect = bad == 0
            self.deal(n * 4.5 * speed * acc, crit=perfect, label="PERFECT" if perfect else "CLEAR",
                      event="perfect" if perfect else ("speed" if wpm >= 60 else "hit"), sec=f"{el:.1f}")
            self.after(p)
            return {"ok": True, "wpm": wpm, "acc": acc, "perfect": perfect}
        self.miss(lose_heart=acc < 0.75, reason="rush_acc")
        self.after(p)
        return {"ok": False, "wpm": wpm, "acc": acc}

    # ─── 스테이지: 카타 ──────────────────────────────────

    def stage_kata(self, p):
        if p.get("cpp_exec") and p.get("_expected") is None:      # 모범답안 컴파일을 미리 (제출 대기 단축)
            threading.Thread(target=judge.warm_cpp, args=(p,), daemon=True).start()
        buf, cur = "", 0
        attempts, hint = 0, False
        fb = []
        t0 = time.monotonic()
        cols, _ = fx.size()
        w = max(40, min(cols - 8, 96))

        def body():
            icon, col = kind_icon("kata")
            out = [fx.c(icon, col, bold=True) + "  " + fx.c(p["title"], fx.WHITE, bold=True) +
                   fx.c(f"   [{p.get('source', 'bank')}]", fx.DARK), ""]
            out += [fx.c(x, 253) for x in wrap(p["desc"], w)]
            if p.get("setup"):
                out += ["", fx.c(tr("주어진 코드", "Given"), fx.DIM)] + code_block(p["setup"], p["lang"])
            if hint and p.get("hint"):
                out += ["", fx.c(tr("힌트 ▸ ", "Hint ▸ "), fx.GOLD, bold=True) + fx.c(p["hint"], fx.GOLD)]
            out += [""] + fb
            el = int(time.monotonic() - t0)
            dots = "".join(fx.c("●", fx.RED) if i < attempts else fx.c("○", fx.GREY) for i in range(3))
            shown = buf[:cur] + fx.c(buf[cur] if cur < len(buf) else " ", fx.BLACK, bg=fx.LIME) + buf[cur + 1:]
            out += [fx.c("❯ ", fx.LIME, bold=True) + fx.c(shown, fx.WHITE, bold=True),
                    "", dots + fx.c(f"  {el}s", fx.DIM) +
                    (fx.c(tr("  ⚡스피드 보너스", "  ⚡speed bonus"), fx.YELLOW) if el < 20 else "")]
            return out

        kata_keys = tr("Enter 제출 · Tab 힌트(-40%) · ESC 패스", "Enter submit · Tab hint (-40%) · ESC skip")
        self.prompt = fx.c(kata_keys, fx.DIM)
        while True:
            self.body = body()
            self.render()
            k = self.keys.get(0.5)
            if k is None:
                continue
            if k == "ESC":
                self.say("c", caster.say("skip"))
                self.miss(lose_heart=False, reason="kata_skip")
                self.reveal(p)
                return {"ok": False, "skipped": True}
            if k == "TAB":
                if not hint:
                    hint = True
                    self.slips += 1
                    self.snd.play("select")
                    self.say("c", caster.say("hint", cost="40%"), tw=False)
                continue
            if k == "BACKSPACE":
                if cur:
                    buf = buf[:cur - 1] + buf[cur:]
                    cur -= 1
                continue
            if k == "DEL":
                buf = buf[:cur] + buf[cur + 1:]
                continue
            if k == "LEFT":
                cur = max(0, cur - 1)
                continue
            if k == "RIGHT":
                cur = min(len(buf), cur + 1)
                continue
            if k == "HOME":
                cur = 0
                continue
            if k == "END":
                cur = len(buf)
                continue
            if k == "CTRL_U":
                buf, cur = "", 0
                continue
            if k == "CTRL_W":
                left = buf[:cur].rstrip()
                left = left[:max(left.rfind(" "), left.rfind("("), left.rfind("."), -1) + 1]
                buf, cur = left + buf[cur:], len(left)
                continue
            if k in ("UP", "DOWN"):
                continue
            if k != "ENTER":
                if len(k) == 1:
                    buf = buf[:cur] + k + buf[cur:]
                    cur += 1
                    self.snd.play("key")
                continue
            if not buf.strip():
                continue
            attempts += 1
            self.prompt = fx.c(tr("채점 중...", "Judging..."), fx.YELLOW)
            self.body = body()
            self.render()
            v = self.var_judge(p, buf)
            self.prompt = fx.c(kata_keys, fx.DIM)
            sec = time.monotonic() - t0
            LOG.ev("kata_submit", title=p["title"], attempt=attempts, ok=v.ok, how=v.how, answer=buf,
                   detail=v.detail, secs=round(sec, 1))
            if v.ok:
                fb = [fx.c(tr("✔ 정답! ", "✔ Correct! "), fx.LIME, bold=True) + fx.c(v.shown or "", fx.GREY)]
                self.body = body()
                crit = attempts == 1 and not hint
                speed = 1.4 if sec < 12 else 1.2 if sec < 20 else 1.0
                base = 420 * speed * (0.6 if hint else 1.0) * (1.0 if attempts == 1 else 0.75)
                event = "speed" if speed > 1.2 and not crit else None
                self.deal(base, crit=crit, label="CRITICAL" if crit else "HIT", event=event, sec=f"{sec:.1f}")
                self.after(p, extra=[fx.c(tr("모범답안 ▸ ", "Model answer ▸ "), fx.DIM) + highlight(p["answer"], p["lang"])])
                return {"ok": True, "attempts": attempts, "secs": sec}
            detail = v.detail or tr("오답", "wrong answer")
            if v.shown == "None" or detail.endswith("None"):
                detail += tr("  (print 말고 값을 내는 표현식으로!)", "  (write an expression that returns a value, not print!)")
            fb = [fx.c(f"✖ {attempts}/3 ", fx.RED, bold=True) + fx.c(detail, fx.RED)]
            self.slips += 1
            if attempts >= 3:
                self.body = body()
                self.miss(lose_heart=True, reason="kata_fail")
                self.say("c", caster.say("reveal"))
                self.reveal(p)
                return {"ok": False, "attempts": attempts}
            self.snd.play("typo")
            self.body = body()
            self.render()
            fx.shake(2, 5)
            self.say("c", caster.say("miss", boss=self.boss), tw=False)

    def reveal(self, p):
        self.after(p, extra=[fx.c(tr("정답 ▸ ", "Answer ▸ "), fx.GOLD, bold=True) + highlight(p["answer"], p["lang"])])

    # ─── 스테이지: 퀴즈 ──────────────────────────────────

    def stage_quiz(self, p):
        order = list(range(4))
        random.shuffle(order)
        opts = [p["options"][i] for i in order]
        correct = order.index(p["correct"])
        chosen = None
        t0 = time.monotonic()
        cols, _ = fx.size()
        w = max(40, min(cols - 8, 96))

        def body(reveal=False):
            icon, col = kind_icon("quiz")
            out = [fx.c(icon, col, bold=True) + "  " + fx.c(p["title"], fx.WHITE, bold=True) +
                   fx.c(f"   [{p.get('source', 'bank')}]", fx.DARK), ""]
            out += code_block(p["code"], p["lang"])
            out += [""] + [fx.c(x, fx.WHITE, bold=True) for x in wrap(p["question"], w)] + [""]
            for i, o in enumerate(opts):
                key = fx.c(f" {i + 1} ", fx.BLACK, bg=fx.PINK, bold=True)
                text = highlight(o, p["lang"]) if p.get("opt_code") else fx.c(o, 253)
                if chosen is not None and i == chosen and not reveal:
                    key = fx.c(f" {i + 1} ", fx.BLACK, bg=fx.YELLOW, bold=True)
                    text = fx.c(o, fx.YELLOW, bold=True)
                if reveal:
                    if i == correct:
                        key = fx.c(" ✔ ", fx.BLACK, bg=fx.LIME, bold=True)
                        text = fx.c(o, fx.LIME, bold=True)
                    elif i == chosen:
                        key = fx.c(" ✖ ", fx.WHITE, bg=fx.RED, bold=True)
                        text = fx.c(o, fx.RED, bold=True)
                    else:
                        key = fx.c(f" {i + 1} ", fx.GREY, bg=fx.DARK)
                        text = fx.c(o, fx.DIM)
                out.append(key + " " + text)
            if not reveal:
                left = max(0.0, QUIZ_LIMIT - (time.monotonic() - t0))
                frac = left / QUIZ_LIMIT
                out += ["", fx.bar(frac, 40, fx.hp_color(frac), ch_full="━", ch_empty="─") +
                        fx.c(f" {left:4.1f}s", fx.hp_color(frac), bold=True) +
                        (fx.c(tr("  ⚡SPEED KILL 구간", "  ⚡SPEED KILL window"), fx.YELLOW, bold=True) if QUIZ_LIMIT - left < 8 else "")]
            return out

        self.prompt = fx.c(tr("1-4 선택 · ESC 패스", "1-4 choose · ESC skip"), fx.DIM)
        self.keys.flush()
        last_tick = -1
        while chosen is None:
            self.body = body()
            self.render()
            el = time.monotonic() - t0
            if el >= QUIZ_LIMIT:
                break
            if QUIZ_LIMIT - el <= 5 and int(el) != last_tick:
                last_tick = int(el)
                self.snd.play("tick")
            k = self.keys.get(0.2)
            if k is None:
                continue
            if k == "ESC":
                break
            m = {"1": 0, "2": 1, "3": 2, "4": 3, "a": 0, "b": 1, "c": 2, "d": 3}
            if k in m:
                chosen = m[k]
        sec = time.monotonic() - t0
        if chosen is not None:
            self.snd.play("select")
            self.body = body()
            self.render()
            fx.sleep(0.25)
        ok = chosen == correct
        LOG.ev("quiz_answer", title=p["title"], ok=ok, chosen=chosen, correct=correct, secs=round(sec, 1),
               timeout=chosen is None)
        self.body = body(reveal=True)
        self.render()
        if ok:
            speed = 1.6 if sec < 8 else 1.25 if sec < 15 else 1.0
            crit = sec < 8
            self.deal(380 * speed, crit=crit, label="SPEED KILL" if crit else "HIT",
                      event="speed" if crit else None, sec=f"{sec:.1f}")
        else:
            if chosen is None:
                self.say("c", caster.say("timeout" if sec >= QUIZ_LIMIT else "skip"))
            self.miss(lose_heart=True, reason="quiz_wrong" if chosen is not None else "quiz_timeout")
        self.after(p)
        return {"ok": ok, "secs": sec}

    # ─── 스테이지: 실기 작업형 ────────────────────────────

    def edit(self, path):
        cmd = exam.editor_cmd(path)
        if not cmd:
            return False
        fx.leave()
        self.keys.__exit__(None, None, None)
        try:
            subprocess.call(cmd)
        except OSError:
            cmd = None
        finally:
            self.keys.__enter__()
            fx.enter()
        LOG.ev("task_edit", editor=cmd[0] if cmd else None)
        return cmd is not None

    def stage_task(self, p):
        ws, src = exam.workspace(self.sid, p, scaffold=self.cfg.get("exam_scaffold", True))
        p["_ws"] = str(ws)
        t0 = time.monotonic()
        runs = fails = 0
        best, hint, last = 0.0, False, None
        cols, _ = fx.size()
        w = max(40, min(cols - 8, 96))
        lang_ext = "C++ (g++ -std=gnu++17)" if p["lang"] == "cpp" else "Python 3"

        def result_lines():
            if last is None:
                return [fx.c(tr("아직 실행 전 — e로 작성하고 r로 채점하세요.", "Not run yet — write with e, grade with r."), fx.DIM)]
            if not last["ok"]:
                head = {"compile": tr("✖ 컴파일 에러", "✖ COMPILE ERROR"), "run": tr("✖ 실행 실패", "✖ RUNTIME ERROR")}
                return [fx.c(head.get(last["stage"], "✖"), fx.RED, bold=True)] + \
                       [fx.c("  " + x[:w], fx.RED) for x in last["msg"].splitlines()[:4]]
            ratio, rows = last["ratio"], last["rows"]
            n_ok = sum(1 for r in rows if r[1] == "ok")
            out = [fx.c(tr(f"채점 ▸ {n_ok}/{len(rows)}줄 일치 ({ratio * 100:.0f}%)", f"Graded ▸ {n_ok}/{len(rows)} lines match ({ratio * 100:.0f}%)"),
                        fx.LIME if ratio == 1 else fx.YELLOW if ratio >= 0.5 else fx.RED, bold=True)]
            shown = 0
            for ln, st, e, g in rows:
                if st == "ok" or shown >= 4:
                    continue
                shown += 1
                tag = {"near": tr("≈ 형식", "≈ format"), "bad": tr("✖ 값  ", "✖ value"), "extra": tr("+ 초과", "+ extra")}[st]
                out.append(fx.c(f"  L{ln:<3}{tag} ", fx.YELLOW if st == "near" else fx.RED, bold=True) +
                           fx.c(tr("기대 ", "want ") + (e if e is not None else "∅"), fx.LIME) + fx.c("  │  ", fx.DARK) +
                           fx.c(tr("출력 ", "got  ") + (g if g is not None else tr("(없음)", "(missing)")), fx.ORANGE))
            return out

        def body(reveal=None):
            icon, col = kind_icon("task")
            out = [fx.c(icon, col, bold=True) + "  " + fx.c(p["title"], fx.WHITE, bold=True) +
                   fx.c(f"   [{p['topic']} · {lang_ext}]", fx.DARK), ""]
            out += [fx.c(x, 253) for x in wrap(p["desc"], w)]
            inp = p["input"].rstrip("\n").split("\n")
            out += ["", fx.c(tr(f"input.txt ({len(inp)}줄)", f"input.txt ({len(inp)} lines)"), fx.DIM)]
            out += [fx.c(f"{i:>2} │ ", fx.DARK) + fx.c(x, 250) for i, x in enumerate(inp[:6], 1)]
            if len(inp) > 6:
                out.append(fx.c("   ⋮", fx.DARK))
            out += [fx.c(tr("출력 형식 ▸ ", "Output ▸ "), fx.SKY, bold=True) + fx.c(p["fmt"], fx.SKY),
                    fx.c(tr("첫 줄 예시 ▸ ", "Line 1 example ▸ "), fx.DIM) + fx.c(p["expected"].split("\n")[0], fx.WHITE)]
            if hint:
                out.append(fx.c(tr("힌트 ▸ ", "Hint ▸ "), fx.GOLD, bold=True) + fx.c(p["hint"], fx.GOLD))
            out += [fx.c(tr("작업 파일 ▸ ", "Your file ▸ "), fx.DIM) + fx.c(str(src), fx.CYAN)]
            if reveal:
                out += ["", fx.c(tr("모범답안 ▸ ", "Model answer ▸ "), fx.GOLD, bold=True) + fx.c(str(reveal), fx.CYAN)]
                out += code_block("\n".join(exam.model_answer(p["tid"], p["lang"]).splitlines()[:14]), p["lang"])
            else:
                out += [""] + result_lines()
            el = int(time.monotonic() - t0)
            left = max(0, exam.TASK_LIMIT - el)
            out += ["", fx.c(f"⏱ {el // 60:02d}:{el % 60:02d}", fx.WHITE, bold=True) +
                    fx.c(tr(f" / 제한 {exam.TASK_LIMIT // 60}분 (남은 {left // 60}분)", f" / limit {exam.TASK_LIMIT // 60} min ({left // 60} min left)"), fx.DIM) +
                    fx.c(tr(f"   실행 {runs}회", f"   runs {runs}"), fx.DIM) +
                    (fx.c(tr(f"   최고 {best * 100:.0f}%", f"   best {best * 100:.0f}%"), fx.YELLOW) if runs else "")]
            return out

        keys_help = tr("e 에디터 · r 실행/채점 · h 힌트(-30%) · f 부분점수 제출 · ESC 포기(모범답안)",
                       "e editor · r run & grade · h hint (-30%) · f submit partial · ESC give up (model answer)")
        self.prompt = fx.c(keys_help, fx.DIM)
        LOG.ev("task_open", tid=p["tid"], lang=p["lang"], ws=str(ws))

        def give_up(why):
            model = ws / ("model_solution.cpp" if p["lang"] == "cpp" else "model_solution.py")
            model.write_text(exam.model_answer(p["tid"], p["lang"]), encoding="utf-8")
            self.body = body(reveal=model)
            self.render()
            if best >= 0.5:
                self.deal(1500 * best * 0.6, label="PARTIAL", event="hit")
                return {"ok": True, "partial": best, "runs": runs}
            self.miss(lose_heart=why != "skip", reason=f"task_{why}")
            self.after(p)
            return {"ok": False, "best": best, "runs": runs}

        while True:
            self.body = body()
            self.render()
            if time.monotonic() - t0 >= exam.TASK_LIMIT:
                self.say("c", caster.say("timeout"))
                return give_up("timeout")
            k = self.keys.get(0.5)
            if k is None:
                continue
            if k == "ESC":
                self.say("c", caster.say("skip"))
                return give_up("skip")
            if k in ("e", "E"):
                if not self.edit(src):
                    self.say("c", tr("에디터를 찾지 못했습니다. $EDITOR를 설정하거나 다른 창에서 파일을 편집하고 r을 누르세요.",
                                     "No editor found. Set $EDITOR, or edit the file in another window and press r."), tw=False)
                continue
            if k in ("h", "H") and not hint:
                hint = True
                self.slips += 1
                self.snd.play("select")
                self.say("c", caster.say("hint", cost="30%"), tw=False)
                continue
            if k in ("f", "F"):
                if not runs:
                    continue
                return give_up("partial")
            if k not in ("r", "R"):
                continue
            self.prompt = fx.c(tr("⚙ 컴파일/실행 중...", "⚙ compiling / running..."), fx.YELLOW, bold=True)
            self.render()
            last = exam.run_solution(ws, p["lang"])
            runs += 1
            self.prompt = fx.c(keys_help, fx.DIM)
            if last["ok"]:
                last["ratio"], last["rows"] = exam.grade(p["expected"], last["out"])
                best = max(best, last["ratio"])
            LOG.ev("task_run", tid=p["tid"], lang=p["lang"], run=runs, stage=last["stage"], ok=last["ok"],
                   ratio=round(last.get("ratio", 0), 3), msg=last["msg"][:200], secs=round(last["secs"], 2))
            self.body = body()
            if last["ok"] and last["ratio"] == 1.0:
                sec = time.monotonic() - t0
                speed = 1.3 if sec < 300 else 1.15 if sec < 600 else 1.0
                crit = fails == 0 and not hint
                base = 1500 * speed * (0.7 if hint else 1.0) * max(0.5, 1 - 0.15 * fails)
                self.deal(base, crit=crit, label="ACCEPTED", event="speed" if crit and sec < 300 else None,
                          sec=f"{sec:.0f}")
                self.after(p)
                return {"ok": True, "runs": runs, "secs": sec}
            fails += 1
            self.slips += 1
            self.snd.play("typo" if last["ok"] else "miss")
            fx.flash(fx.RED, 40)
            label = {"compile": "COMPILE ERROR", "run": "RUNTIME ERROR"}.get(last["stage"], "WRONG ANSWER")
            fx.slam(label, [fx.RED], hold=0.25, shake_power=2)
            self.render()
            self.say("c", caster.say("miss", boss=self.boss), tw=False)

    # ─── 스테이지: 줄별 클론코딩 ──────────────────────────

    def stage_clone(self, p):
        rows = exam.clone_lines(p["code"])
        todo = [i for i, r in enumerate(rows) if r[2] is not None]
        typed = {}
        cur_i, buf = 0, ""
        typos = wrong = streak = 0
        t0 = None
        cols, _ = fx.size()
        w = max(40, min(cols - 8, 100))

        def view():
            icon, col = kind_icon("clone")
            out = [fx.c(icon, col, bold=True) + "  " + fx.c(p["title"], fx.WHITE, bold=True) +
                   fx.c(f"   [{p['topic']}]", fx.DARK),
                   fx.c(tr("모범답안을 한 줄씩 따라 치세요. 들여쓰기·주석은 자동 · Enter 줄 제출 · ESC 포기",
                           "Retype the model answer line by line. Indent & comments are automatic · Enter submits a line · ESC quits"),
                        fx.DIM), ""]
            cur = todo[cur_i] if cur_i < len(todo) else len(rows)
            lo = max(0, min(cur - 6, len(rows) - 15))
            for i in range(lo, min(len(rows), lo + 15)):
                raw, indent, target = rows[i]
                num = fx.c(f"{i + 1:>3} ", fx.DARK)
                if target is None:
                    out.append(num + fx.c("  " + raw, 240))
                elif i in typed:
                    out.append(num + fx.c("✔ ", fx.LIME) + fx.c(indent + typed[i], fx.LIME))
                elif i == cur:
                    out.append(num + fx.c("▶ ", fx.YELLOW, bold=True) + fx.c(indent, fx.DARK) +
                               fx.c(target, fx.BLACK, bg=fx.YELLOW, bold=True))
                else:
                    out.append(num + "  " + highlight(raw, p["lang"]))
            if cur < len(rows):
                target = rows[cur][2]
                good = 0
                while good < len(buf) and good < len(target) and buf[good] == target[good]:
                    good += 1
                shown = fx.c(buf[:good], fx.LIME, bold=True) + fx.c(buf[good:], fx.WHITE, bg=fx.RED, bold=True)
                out += ["", fx.c("❯ ", fx.SKY, bold=True) + fx.c(rows[cur][1].replace(" ", "·"), fx.DARK) + shown +
                        fx.c("▏", fx.SKY)]
            el = (time.monotonic() - t0) if t0 else 0.0
            done = len(typed)
            out += ["", fx.bar(done / max(1, len(todo)), 30, fx.SKY, ch_full="■", ch_empty="·") +
                    fx.c(f"  {done}/{len(todo)} " + tr("줄", "lines"), fx.WHITE, bold=True) +
                    fx.c(f"   TIME {el:5.1f}s   " + tr("오타", "typos") + f" {typos}   " + tr("오답 줄", "wrong lines") +
                         f" {wrong}   STREAK {streak}", fx.DIM)]
            return out

        self.prompt = ""
        LOG.ev("clone_open", tid=p["tid"], lang=p["lang"], lines=len(todo))
        while cur_i < len(todo):
            self.body = view()
            self.render()
            k = self.keys.get(0.5 if t0 else None)
            if k is None:
                continue
            if t0 is None:
                t0 = time.monotonic()
            target = rows[todo[cur_i]][2]
            if k == "ESC":
                self.say("c", caster.say("skip"))
                self.miss(lose_heart=False, reason="clone_skip")
                return {"ok": False, "skipped": True, "lines": len(typed)}
            if k == "BACKSPACE":
                buf = buf[:-1]
                continue
            if k == "CTRL_U":
                buf = ""
                continue
            if k == "CTRL_W":
                buf = buf.rstrip()
                buf = buf[:max(buf.rfind(" "), buf.rfind("("), buf.rfind("."), -1) + 1]
                continue
            if k == "ENTER":
                if exam.same_line(buf, target):
                    typed[todo[cur_i]] = target
                    cur_i, buf = cur_i + 1, ""
                    streak += 1
                    chip = 4 * len(target) // 10 + 4
                    self.boss_hp -= chip
                    self.disp_hp = max(0, self.boss_hp)
                    self.score += chip
                    if streak in (5, 10, 20):
                        self.snd.play("streak")
                        self.body = view()
                        self.say("c", caster.say("streak", n=streak), tw=False)
                    else:
                        self.snd.play("select")
                else:
                    wrong += 1
                    self.slips += 1
                    if streak >= 5:
                        self.say("c", caster.say("streak_break", n=streak), tw=False)
                    streak = 0
                    self.snd.play("typo")
                    fx.shake(2, 5)
                continue
            if len(k) == 1:
                ok_before = target.startswith(buf)
                buf += k
                if ok_before and not target.startswith(buf):
                    typos += 1
                    self.snd.play("typo")
                else:
                    self.snd.play("key")
        sec = time.monotonic() - (t0 or time.monotonic())
        chars = sum(len(rows[i][2]) for i in todo)
        wpm = (chars / 5) / max(sec / 60, 1e-6)
        # 친 코드를 실제로 돌려 본다: 작업 폴더에 저장 → 실행 → 기대 출력과 비교
        src_text = "\n".join(r[1] + typed[i] if r[2] is not None else r[0] for i, r in enumerate(rows)) + "\n"
        ws, src = exam.workspace(self.sid, p)
        src.write_text(src_text, encoding="utf-8")
        p["_ws"] = str(ws)
        self.prompt = fx.c(tr("⚙ 친 코드를 실제로 실행 중...", "⚙ running the code you typed..."), fx.YELLOW, bold=True)
        self.render()
        res = exam.run_solution(ws, p["lang"])
        ratio = exam.grade(p["expected"], res["out"])[0] if res["ok"] else 0.0
        self.prompt = ""
        LOG.ev("clone_done", tid=p["tid"], lang=p["lang"], secs=round(sec, 1), wpm=round(wpm, 1), typos=typos,
               wrong=wrong, run_ok=res["ok"], ratio=round(ratio, 3))
        self.rush_chars += chars
        self.rush_secs += sec
        verdict = (tr(f"✔ 친 코드를 새 입력으로 실행 → {ratio * 100:.0f}% 일치", f"✔ your typed code ran on fresh input → {ratio * 100:.0f}% match")
                   if res["ok"] else tr("✖ 실행 실패: ", "✖ run failed: ") + res["msg"].splitlines()[0][:80])
        self.body = view() + ["", fx.c(verdict, fx.LIME if ratio == 1 else fx.RED, bold=True),
                              fx.c(tr("저장됨 ▸ ", "saved ▸ ") + str(src), fx.DIM)]
        self.render()
        perfect = typos == 0 and wrong == 0
        speed = max(0.7, min(1.6, wpm / 35))
        self.deal(chars * 2.2 * speed * (1.0 if ratio == 1 else 0.5), crit=perfect and ratio == 1,
                  label="CLONED" if ratio == 1 else "CLEAR", event="perfect" if perfect else None)
        self.after(p)
        return {"ok": ratio == 1, "wpm": wpm, "typos": typos, "wrong": wrong}

    # ─── 해설 + 디버거 ────────────────────────────────────

    def after(self, p, extra=()):
        if extra:
            self.body = self.body + [""] + list(extra)
            self.render()
        if p.get("explain"):
            self.say("a", p["explain"])

    def replay_code(self, p):
        if p["lang"] != "python":
            return None
        if p["kind"] in ("task", "clone"):
            path = Path(p["_ws"]) / "solution.py" if p.get("_ws") else None
            return path.read_text(encoding="utf-8") if path and path.exists() else None
        if p["kind"] == "quiz":
            return p["code"]
        if p["kind"] == "kata" and p.get("answer"):
            return (p.get("setup", "") + "\n" if p.get("setup") else "") + f"result = {p['answer']}\nprint(result)"
        return None

    def wait_next(self, p, last):
        code = self.replay_code(p)
        parts = [tr("Enter ▶ 다음 스테이지", "Enter ▶ next stage") if not last else tr("Enter ▶ 결과 보기", "Enter ▶ results")]
        if code:
            parts.append(tr("d 디버거 킬캠", "d debugger killcam"))
        parts.append(tr("q 그만두기", "q quit"))
        self.prompt = fx.c(" · ".join(parts), fx.GOLD, bold=True)
        self.render()
        self.keys.flush()
        while True:
            k = self.keys.get()
            if k in ("ENTER", " "):
                return
            if k == "q":
                raise Quit()
            if k == "d" and code:
                LOG.ev("killcam", title=p["title"])
                tracer.replay(code, self.keys, title=p["title"], sound=self.snd, cwd=p.get("_ws"))
                self.render()

    # ─── 메인 루프 ───────────────────────────────────────

    def pick_kind(self):
        if self.mode == "exam":
            return exam.EXAM_ORDER[(self.stage - 1) % len(exam.EXAM_ORDER)]
        if self.mode.startswith("exam-"):
            return self.mode[5:]
        if self.mode != "mix":
            return self.mode
        return random.choice(["rush", "kata", "quiz", "quiz", "kata"])

    def play(self):
        LOG.sid = self.sid
        LOG.ev("session_start", mode=self.mode, langs=self.langs, stages=self.stages, ranked=self.ranked,
               boss=self.boss, ver=VERSION)
        self.render()
        self.say("c", caster.say("start", boss=self.boss))
        reason = "clear"
        try:
            while self.stage < self.stages:
                self.stage += 1
                self.cur_lang = random.choice(self.langs)
                kind = self.pick_kind()
                p = self.src.next(kind, self.cur_lang, self.track)
                self.feed.clear()
                self.body = []
                LOG.ev("problem", stage=self.stage, kind=kind, lang=self.cur_lang, title=p["title"],
                       source=p.get("source"), pid=p.get("id"))
                fx.slam(f"STAGE {self.stage}", [fx.WHITE], hold=0.18, shake_power=1)
                res = getattr(self, f"stage_{kind}")(p)
                res.update(stage=self.stage, kind=kind, lang=self.cur_lang, title=p["title"])
                self.results.append(res)
                if self.hearts <= 0:
                    reason = "gameover"
                    break
                self.wait_next(p, self.stage == self.stages)
        except Quit:
            reason = "quit"
        return self.finish(reason)

    def finish(self, reason):
        done = len(self.results)
        acc = self.hits / max(1, self.hits + self.misses)
        flawless = reason == "clear" and self.misses == 0 and self.slips == 0 and self.hearts == 3
        if flawless:
            self.score += 3000
        if reason == "quit":
            grade = "-"
        elif flawless:
            grade = "SS"
        elif self.kos >= 1 and acc >= 0.85:
            grade = "S"
        elif self.kos >= 1 or acc >= 0.8:
            grade = "A"
        elif acc >= 0.6:
            grade = "B"
        elif acc >= 0.4:
            grade = "C"
        else:
            grade = "D"
        wpm = (self.rush_chars / 5) / (self.rush_secs / 60) if self.rush_secs > 1 else 0
        rec = {
            "id": self.sid, "ts": datetime.now().isoformat(timespec="seconds"), "date": date.today().isoformat(),
            "player": self.player, "mode": self.mode, "lang": self.langs[0] if len(self.langs) == 1 else "mix",
            "stages": self.stages, "done": done, "ranked": self.ranked and reason != "quit",
            "score": self.score, "grade": grade, "max_combo": self.max_combo, "acc": round(acc, 3),
            "wpm": round(wpm, 1), "kos": self.kos, "hearts": self.hearts, "hits": self.hits,
            "misses": self.misses, "crits": self.crits, "secs": int(time.monotonic() - self.t0), "reason": reason,
            "flawless": flawless, "ver": VERSION, "track": self.track,
            "results": [{"kind": r["kind"], "lang": r["lang"], "ok": r["ok"]} for r in self.results],
        }
        LOG.ev("session_end", **{k: v for k, v in rec.items() if k not in ("id", "ts", "results")})
        if reason == "gameover":
            self.snd.play("heart")
            fx.flash(fx.RED, 90)
            fx.slam("GAME OVER", [fx.RED, 160, 124, 88, 52], hold=0.8, shake_power=4)
            self.say("c", caster.say("game_over"))
        elif reason == "clear":
            if flawless:
                self.snd.play("fanfare")
                fx.slam("FLAWLESS", fx.RAINBOW, hold=0.8, shake_power=4, sub="+3,000", sub_color=fx.GOLD)
                self.say("c", caster.say("flawless"))
            elif self.boss_hp > 0:
                self.say("c", caster.say("escape", boss=self.boss))
        return rec


def summary_screen(rec, snd, keys, best_before=None, rank_info=None, rank_wait=None):
    """결과 화면: 점수 카운트업 → 등급 슬램 → 신기록 → 랭킹 비교."""
    grade_color = {"SS": fx.RAINBOW, "S": [fx.GOLD], "A": [fx.LIME], "B": [fx.CYAN], "C": [fx.YELLOW],
                   "D": [fx.GREY], "-": [fx.DARK]}

    def lines(score_shown, extra=()):
        L = [fx.c(" RESULT ", fx.BLACK, bg=fx.GOLD, bold=True) + "  " +
             fx.c(f"{mode_label(rec['mode'])} · {rec['lang']} · {rec['done']}/{rec['stages']} " + tr("스테이지", "stages"),
                  fx.WHITE, bold=True) + ("  " + fx.c("RANKED", fx.RED, bold=True) if rec["ranked"] else
                                          fx.c(tr("  연습(랭킹 미반영)", "  practice (not ranked)"), fx.DIM)), ""]
        L += [fx.c(x, fx.GOLD, bold=True) for x in fx.big(fx.fmt(score_shown).replace(",", " "))]
        L += ["", fx.c(tr("등급 ", "Grade "), fx.DIM) + fx.c(rec["grade"], grade_color.get(rec["grade"], [fx.WHITE])[0], bold=True) +
              fx.c(tr("   최대 콤보 ", "   Max combo "), fx.DIM) + fx.c(str(rec["max_combo"]), caster.combo_color(rec["max_combo"]), bold=True) +
              fx.c(tr("   정확도 ", "   Accuracy "), fx.DIM) + fx.c(f"{rec['acc'] * 100:.0f}%", fx.WHITE, bold=True) +
              fx.c(tr("   크리티컬 ", "   Crits "), fx.DIM) + fx.c(str(rec["crits"]), fx.ORANGE, bold=True) +
              fx.c("   K.O. ", fx.DIM) + fx.c(str(rec["kos"]), fx.RED, bold=True) +
              (fx.c("   WPM ", fx.DIM) + fx.c(f"{rec['wpm']:.0f}", fx.CYAN, bold=True) if rec["wpm"] else "") +
              fx.c(tr(f"   {rec['secs'] // 60}분 {rec['secs'] % 60}초", f"   {rec['secs'] // 60}m {rec['secs'] % 60}s"), fx.DIM)]
        return L + list(extra)

    target = rec["score"]
    steps = 24 if fx.S.fx else 1
    for i in range(1, steps + 1):
        fx.show(lines(int(target * (i / steps) ** 0.5)))
        if i % 2 == 0:
            snd.play("tick")
        fx.sleep(0.03)
    extra = []
    if rec["grade"] != "-":
        snd.play("crit")
        fx.slam(rec["grade"], grade_color.get(rec["grade"], [fx.WHITE]), hold=0.5, shake_power=4, sub="GRADE")
    if best_before is not None and rec["score"] > best_before and rec["grade"] != "-":
        snd.play("fanfare")
        fx.flash(fx.GOLD, 60)
        fx.slam("NEW RECORD", fx.RAINBOW, hold=0.6, shake_power=3, sub=tr(f"이전 최고 {fx.fmt(best_before)}", f"previous best {fx.fmt(best_before)}"))
        extra += ["", fx.c(tr("▶ 캐스터 ", "▶ CASTER "), fx.ORANGE, bold=True) +
                  fx.c(caster.say("record", score=fx.fmt(rec["score"])), 255, bold=True)]
    if rank_wait is not None:
        spin = "◐◓◑◒"
        i = 0
        while rank_wait.is_alive():
            fx.show(lines(target, extra + ["", fx.c(f"{spin[i % 4]} " + tr("온라인 랭킹 동기화 중...", "syncing online ranking..."), fx.YELLOW)]))
            i += 1
            rank_wait.join(0.12)
    if rank_info:
        extra += [""] + rank_info
    extra += ["", fx.c(tr("Enter ▶ 메뉴로", "Enter ▶ menu"), fx.GOLD, bold=True)]
    fx.show(lines(target, extra))
    keys.flush()
    while keys.get() not in ("ENTER", " ", "q", "ESC"):
        pass
