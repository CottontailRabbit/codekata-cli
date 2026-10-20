"""codekata CLI: 메뉴 / play / stats / log / rank / auth / debug / serve / config / doctor."""
import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from . import VERSION, ai, bank, exam, fx, i18n, rank, store, tracer
from .game import MODES, Game, mode_label, summary_screen
from .i18n import tr
from .keys import Keys
from .log import LOG, LOG_DIR, read_events
from .sound import Sound

SPARK = "▁▂▃▄▅▆▇█"
GLOBAL_FLAGS = {"--debug": "debug", "--no-fx": "no_fx", "--no-sound": "no_sound", "--no-color": "no_color",
                "--offline": "offline", "--en": "en", "--ko": "ko"}
_SOURCE = None
_PROVIDER = None


def emit(lines):
    text = "\n".join(lines)
    if not fx.S.color:
        text = fx.SGR_RE.sub("", text)
    print(text)


def spark(vals):
    if not vals:
        return ""
    lo, hi = min(vals), max(vals)
    return "".join(SPARK[int((v - lo) / (hi - lo) * 7) if hi > lo else 3] for v in vals)


def streak_days(runs):
    days = {r["date"] for r in runs}
    d, n = date.today(), 0
    if d.isoformat() not in days:
        d -= timedelta(days=1)
    while d.isoformat() in days:
        n += 1
        d -= timedelta(days=1)
    return n


def best_score(history, mode):
    scores = [r["score"] for r in history["runs"] if r.get("mode") == mode and r.get("ranked")]
    return max(scores) if scores else None


# ─── 출제기 / 프로바이더 ─────────────────────────────────

def get_source(cfg, history, offline=False):
    global _SOURCE, _PROVIDER
    if _SOURCE is None:
        prov = None
        if not offline and cfg["provider"] == "codex":
            cand = ai.CodexProvider(cfg.get("model", ""), cfg.get("effort", "low"))
            if cand.available():
                prov = cand
            LOG.ev("provider", name="codex", ok=prov is not None, status=cand.status())
        _PROVIDER = prov
        _SOURCE = ai.ProblemSource(prov, history, prefetch=cfg.get("prefetch", 3))
    else:
        _SOURCE.history = history
    return _SOURCE, _PROVIDER


# ─── 게임 실행 ──────────────────────────────────────────

def play(cfg, opts, mode, langs, stages, keys=None, task=None):
    history = store.load_history()
    src, prov = get_source(cfg, history, opts.offline)
    if mode.startswith("exam"):
        kinds = ["quiz", "kata"] if mode == "exam" else [mode[5:]]
        src.warm(kinds, langs, "exam")
        src.task_pick = task
    else:
        kinds = ["rush", "kata", "quiz"] if mode == "mix" else [mode]
        src.warm(kinds, langs)
    snd = Sound(cfg["sound"] and not opts.no_sound)
    own_keys = keys is None
    if own_keys:
        keys = Keys().__enter__()
        fx.enter()
    rec = None
    try:
        g = Game(cfg, src, prov, snd, keys, mode=mode, langs=langs, stages=stages, debug=opts.debug,
                 player=store.player_name(cfg))
        rec = g.play()
        before = best_score(history, mode)
        history["runs"].append(rec)
        store.save_history(history)
        box = {}
        th = None
        if rec["ranked"] and cfg["rank"]["backend"] != "none":
            def work():
                try:
                    box["r"] = rank.sync(cfg, history, rec)
                except Exception as e:  # noqa: BLE001
                    box["r"] = (None, None, str(e))
            th = threading.Thread(target=work, daemon=True)
            th.start()
        info = []
        summary_screen(rec, snd, keys, best_before=before, rank_info=None, rank_wait=th)
        if th is not None:
            th.join()
            runs, me, err = box.get("r", (None, None, "?"))
            store.save_history(history)
            if runs is not None:
                rows = rank.board(runs, mode=mode, period="week")
                me = me or store.player_name(cfg)
                info = rank.render_board(rows, me=me, highlight_id=rec["id"], top=5,
                                         title=tr("주간 랭킹 · ", "Weekly ranking · ") + mode_label(mode))
                riv = rank.rivalry(rows, me)
                if riv:
                    info += ["", fx.c(tr("▶ 캐스터 ", "▶ CASTER "), fx.ORANGE, bold=True) + fx.c(riv, 255, bold=True)]
            if err:
                info += ["", fx.c(f"⚠ {err}", fx.RED)]
            if info:
                fx.show(info + ["", fx.c(tr("Enter ▶ 메뉴로", "Enter ▶ menu"), fx.GOLD, bold=True)])
                keys.flush()
                while keys.get() not in ("ENTER", " ", "q", "ESC"):
                    pass
    except KeyboardInterrupt:
        pass
    finally:
        if own_keys:
            fx.leave()
            keys.__exit__(None, None, None)
    if rec and own_keys:
        print_summary(rec)
    return rec


def print_summary(rec):
    print(fx.c("codekata", fx.GOLD, bold=True) + " ▸ " +
          fx.c(tr(f"{fx.fmt(rec['score'])}점", f"{fx.fmt(rec['score'])} pts"), fx.WHITE, bold=True) +
          tr(f" · 등급 {rec['grade']} · 최대 {rec['max_combo']}콤보 · 정확도 {rec['acc'] * 100:.0f}% · K.O. {rec['kos']}",
             f" · grade {rec['grade']} · max combo {rec['max_combo']} · accuracy {rec['acc'] * 100:.0f}% · K.O. {rec['kos']}") +
          (f" · WPM {rec['wpm']:.0f}" if rec["wpm"] else "") +
          fx.c(f"   (log: codekata log {rec['id']})", fx.DIM))


# ─── 화면용 텍스트 생성기 (CLI 출력/메뉴 공용) ───────────

def stats_lines(history):
    runs = history["runs"]
    L = [fx.c(tr("── 통계 ──", "── stats ──"), fx.CYAN, bold=True), ""]
    if not runs:
        return L + [fx.c(tr("아직 기록이 없습니다. `codekata` 로 첫 판을 시작하세요!",
                            "No runs yet. Start your first one with `codekata`!"), fx.DIM)]
    today = date.today().isoformat()
    n_all, n_ranked = len(runs), sum(1 for r in runs if r.get("ranked"))
    n_today, streak = sum(1 for r in runs if r["date"] == today), streak_days(runs)
    L.append(tr(f"총 {n_all}판 · 랭크전 {n_ranked}판 · 오늘 {n_today}판 · ",
                f"{n_all} runs · {n_ranked} ranked · {n_today} today · ") +
             fx.c(tr(f"연속 {streak}일", f"{streak}-day streak"), fx.ORANGE, bold=True))
    L.append("")
    for mode in MODES:
        rs = [r for r in runs if r.get("mode") == mode]
        if rs:
            b = max(rs, key=lambda r: r["score"])
            L.append(f"{fx.pad(mode_label(mode), 10)} {tr('최고', 'best')} {fx.c(fx.fmt(b['score']), fx.GOLD, bold=True):>10}"
                     f"  {tr('등급', 'grade')} {b['grade']:<2}  {tr('최대콤보', 'max combo')} "
                     f"{max(r['max_combo'] for r in rs):>3}  {len(rs)}{tr('판', ' runs')}")
    L.append("")
    per = defaultdict(lambda: [0, 0])
    for r in runs:
        for x in r.get("results", []):
            per[x["lang"]][0] += int(bool(x["ok"]))
            per[x["lang"]][1] += 1
    for lang, (ok, n) in sorted(per.items(), key=lambda kv: -kv[1][1]):
        frac = ok / n if n else 0
        L.append(f"{fx.pad(bank.LANG_LABEL.get(lang, lang), 11)} {fx.bar(frac, 24, fx.hp_color(frac))} "
                 f"{frac * 100:5.1f}%  ({ok}/{n})")
    recent = runs[-20:]
    L += ["", tr("점수 추이  ", "score      ") + fx.c(spark([r["score"] for r in recent]), fx.GOLD)]
    w = [r["wpm"] for r in recent if r.get("wpm")]
    if w:
        L.append(tr("WPM 추이   ", "WPM        ") + fx.c(spark(w), fx.CYAN) +
                 tr(f"  최근 {w[-1]:.0f} / 최고 {max(w):.0f}", f"  last {w[-1]:.0f} / best {max(w):.0f}"))
    return L


def sessions_from_logs(days=None):
    ss = {}
    for e in read_events(days):
        sid = e.get("sid")
        if not sid:
            continue
        s = ss.setdefault(sid, {"sid": sid, "start": e["t"], "events": 0, "problems": 0, "ai": 0, "end": None,
                                "mode": "", "errors": 0})
        s["events"] += 1
        if e["type"] == "session_start":
            s["mode"] = e.get("mode", "")
            s["langs"] = e.get("langs", [])
        elif e["type"] == "problem":
            s["problems"] += 1
            s["ai"] += int(e.get("source") == "ai")
        elif e["type"] == "session_end":
            s["end"] = e
        if e.get("ok") is False and e["type"] in ("ai_batch", "rank_push", "rank_fetch", "var"):
            s["errors"] += 1
    return list(ss.values())


EV_COLOR = {"hit": fx.GOLD, "miss": fx.RED, "ko": fx.MAGENTA, "problem": fx.CYAN, "session_start": fx.LIME,
            "session_end": fx.LIME, "ai_batch": fx.PURPLE, "ai_drop": 240, "var": fx.YELLOW, "rank_push": fx.SKY,
            "rank_fetch": fx.SKY, "kata_submit": 253, "quiz_answer": 253, "rush_done": 253, "killcam": fx.ORANGE}


def event_line(e, t0=None):
    skip = {"ts", "t", "sid", "type"}
    rel = f"+{e['ts'] - t0:7.1f}s" if t0 else e["t"][11:23]
    data = " ".join(f"{k}={json.dumps(v, ensure_ascii=False) if not isinstance(v, str) else v}"
                    for k, v in e.items() if k not in skip)
    color = EV_COLOR.get(e["type"], fx.GREY)
    if e.get("ok") is False:
        color = fx.RED
    return fx.c(rel, fx.DIM) + " " + fx.c(f"{e['type']:<13}", color, bold=True) + " " + data


def log_lines(sid=None, errors=False, n=15):
    if sid:
        evs = [e for e in read_events() if (e.get("sid") or "").startswith(sid)]
        if not evs:
            return [fx.c(tr(f"세션 {sid} 로그 없음", f"no log for session {sid}"), fx.RED)]
        t0 = evs[0]["ts"]
        return [fx.c(tr(f"── 세션 {evs[0]['sid']} 타임라인 ({len(evs)} events) ──",
                        f"── session {evs[0]['sid']} timeline ({len(evs)} events) ──"), fx.CYAN, bold=True)] + \
               [event_line(e, t0) for e in evs]
    if errors:
        evs = [e for e in read_events(14) if e.get("ok") is False or e["type"] == "ai_drop"]
        return [fx.c(tr("── 최근 14일 오류/드롭 ──", "── errors / drops, last 14 days ──"), fx.CYAN, bold=True)] + \
            [event_line(e) for e in evs[-40:]]
    ss = sessions_from_logs()[-n:]
    L = [fx.c(tr("── 최근 세션 ──  (codekata log <sid> 로 상세 타임라인)",
                 "── recent sessions ──  (codekata log <sid> for the timeline)"), fx.CYAN, bold=True),
         fx.c(f"{'START':<20}{'SID':<10}{'MODE':<7}{'SCORE':>9}  {'G':<3}{'END':<9}{'PROB':>5}{'AI':>4}{'ERR':>5}",
              fx.DIM)]
    for s in ss:
        end = s["end"] or {}
        L.append(f"{s['start'][:19]:<20}{s['sid']:<10}{s['mode']:<7}{fx.fmt(end.get('score', 0)):>9}  "
                 f"{end.get('grade', '·'):<3}{end.get('reason', tr('진행중?', 'live?')):<9}{s['problems']:>5}{s['ai']:>4}"
                 + fx.c(f"{s['errors']:>5}", fx.RED if s["errors"] else fx.DIM))
    L += ["", fx.c(tr("로그 위치: ", "logs: ") + str(LOG_DIR), fx.DIM)]
    return L


def rank_lines(cfg, mode="mix", period="week", lang=None):
    history = store.load_history()
    try:
        runs, me, err = rank.sync(cfg, history, None)
        store.save_history(history)
    except rank.RankError as e:
        runs, me, err = None, None, str(e)
    names = {"day": tr("오늘", "Today's"), "week": tr("주간", "Weekly"), "all": tr("전체", "All-time")}
    if runs is None:
        local = [dict(r, login=r.get("player")) for r in history["runs"] if r.get("ranked")]
        L = [fx.c(f"⚠ {err}", fx.YELLOW), fx.c(tr("로컬 기록 기준 개인 랭킹을 보여줍니다.", "Showing your local personal ranking."), fx.DIM), ""]
        rows = sorted((r for r in local if r.get("mode") == mode), key=lambda r: -r["score"])[:10]
        for i, r in enumerate(rows, 1):
            L.append(f"{i:>3}. {fx.fmt(r['score']):>9}  {r['grade']:<3} {tr('콤보', 'combo')} {r['max_combo']:>3}  {r['date']}")
        return L
    me = me or store.player_name(cfg)
    rows = rank.board(runs, mode=mode, period=period, lang=lang)
    title = (f"🏆 {names[period]} " + tr("랭킹", "ranking") + f" · {mode_label(mode)}" + (f" · {lang}" if lang else "") +
             tr(f"  ({len(rows)}명)", f"  ({len(rows)} players)"))
    L = rank.render_board(rows, me=me, top=10, title=title)
    riv = rank.rivalry(rows, me)
    if riv:
        L += ["", fx.c("▶ ", fx.ORANGE, bold=True) + fx.c(riv, 255, bold=True)]
    if err:
        L += ["", fx.c(tr("⚠ push 실패(다음에 재시도): ", "⚠ push failed (will retry): ") + str(err), fx.RED)]
    pend = len(history.get("pending_push", []))
    if pend:
        L.append(fx.c(tr(f"대기 중인 업로드 {pend}건", f"{pend} uploads pending"), fx.DIM))
    return L


def auth_lines(cfg):
    p = ai.CodexProvider(cfg.get("model", ""), cfg.get("effort", "low"))
    ok = p.available()
    L = [fx.c(tr("── 인증 ──", "── auth ──"), fx.CYAN, bold=True), "",
         fx.c(tr("AI 출제 (ChatGPT via Codex CLI)", "AI problems (ChatGPT via Codex CLI)"), fx.WHITE, bold=True),
         f"  codex : {p.bin or tr('없음', 'missing')}",
         tr("  상태  : ", "  status: ") + (fx.c(p.status(), fx.LIME) if ok else fx.c(p.status() or tr("로그인 필요", "login required"), fx.RED)),
         tr("  모델  : ", "  model : ") + f"{cfg.get('model') or tr('(codex 기본값)', '(codex default)')} · effort={cfg.get('effort')}"]
    if not ok:
        L.append(fx.c(tr("  → `codekata auth login` (= codex login, 브라우저로 ChatGPT 로그인)",
                         "  → `codekata auth login` (= codex login, sign in to ChatGPT in the browser)"), fx.YELLOW))
    L.append(fx.c(tr("  ※ Claude 구독 로그인은 외부 앱 사용 불가 → ChatGPT 로그인 사용",
                     "  ※ Claude subscription logins can't be used by third-party apps → ChatGPT login is used"), fx.DIM))
    L += ["", fx.c(tr("온라인 랭킹", "Online ranking"), fx.WHITE, bold=True), f"  backend: {cfg['rank']['backend']}"]
    if cfg["rank"]["backend"] == "github":
        gh = shutil.which("gh")
        st = ""
        if gh:
            r = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
            st = tr("로그인됨", "logged in") if r.returncode == 0 else tr("로그인 필요 (gh auth login)", "login required (gh auth login)")
        L += [f"  repo   : {cfg['rank']['repo']}/{cfg['rank']['path']}", f"  gh     : {st or tr('없음', 'missing')}"]
    elif cfg["rank"]["backend"] == "http":
        L += [f"  url    : {cfg['rank']['url']}",
              f"  token  : {tr('설정됨', 'set') if cfg['rank']['token'] else tr('없음', 'none')}"]
    else:
        L.append(fx.c("  → `codekata rank setup`", fx.YELLOW))
    return L


def exam_list_lines():
    L = [fx.c(tr("── 로봇SW개발기사 실기 · 실전 작업형 ──", "── Robot SW engineer practical · real tasks ──"), fx.CYAN, bold=True),
         fx.c(tr("입력 TXT → 로봇 공식 계산 → 요구 형식 그대로 output.txt. Python/C++ 모범답안은 같은 출력으로 검증됨",
                 "input TXT → robot formulas → output.txt in the exact format. Python/C++ model answers verified to match"), fx.DIM), ""]
    for t in exam.TASKS:
        L.append(f"  {fx.c(fx.pad(t['tid'], 10), fx.GOLD, bold=True)}{fx.pad(i18n.pick(t['topic']), 18)}{i18n.pick(t['title'])}")
    L += ["", fx.c(tr("예: codekata exam task -t ik2 -l cpp", "e.g. codekata exam task -t ik2 -l cpp"), fx.DIM)]
    return L


def doctor_lines(cfg):
    def chk(ok, label, extra=""):
        return (fx.c("✔ ", fx.LIME) if ok else fx.c("✖ ", fx.RED)) + label + (fx.c(f"  {extra}", fx.DIM) if extra else "")
    cols, rows = fx.size()
    p = ai.CodexProvider()
    L = [fx.c("── doctor ──", fx.CYAN, bold=True),
         chk(sys.version_info >= (3, 9), f"Python {sys.version.split()[0]}"),
         chk(sys.stdin.isatty() and sys.stdout.isatty(), "TTY"),
         chk(cols >= 80 and rows >= 28, tr(f"터미널 크기 {cols}x{rows}", f"terminal size {cols}x{rows}"),
             tr("권장 90x32 이상", "90x32 or larger recommended")),
         chk("256" in os.environ.get("TERM", "") or os.environ.get("COLORTERM"), tr("256색", "256 colors") + f" ({os.environ.get('TERM')})"),
         chk(p.available(), tr("codex(ChatGPT) 로그인", "codex (ChatGPT) login"), p.status()),
         chk(bool(shutil.which("node")), tr("node (JS 실행 채점)", "node (JS judging)")),
         chk(bool(shutil.which("g++")), tr("g++ (C++ 실행 채점)", "g++ (C++ judging)")),
         chk(bool(shutil.which("aplay") or shutil.which("paplay") or shutil.which("afplay")), tr("효과음 플레이어", "sound player")),
         chk(bool(shutil.which("gh")), tr("gh (GitHub 랭킹)", "gh (GitHub ranking)")),
         chk(os.access(store.HOME, os.W_OK) if store.HOME.exists() else True, tr("저장소 ", "data dir ") + str(store.HOME))]
    return L


# ─── 인터랙티브 메뉴 ────────────────────────────────────

LANG_CHOICES = ["python", "js", "rust", "cpp", "go", "random"]


def menu(cfg, opts):
    history = store.load_history()
    src, prov = get_source(cfg, history, opts.offline)
    lang = cfg.get("lang", "python")
    src.warm(["rush", "kata", "quiz"], [lang] if lang != "random" else cfg["langs"])
    snd = Sound(cfg["sound"] and not opts.no_sound)
    with Keys() as keys:
        fx.enter()
        try:
            while True:
                history = store.load_history()
                best = best_score(history, "mix")
                ai_st = (fx.c(tr(f"ChatGPT ✓ (대기 {src.qsize()}문제)", f"ChatGPT ✓ ({src.qsize()} queued)"), fx.LIME)
                         if prov and src.alive else fx.c(tr("오프라인 문제은행", "offline bank"), fx.YELLOW))
                rk = cfg["rank"]
                rk_st = {"github": f"github {rk['repo']}", "http": f"http {rk['url']}"}.get(
                    rk["backend"], tr("미설정 ([R]에서 안내)", "not set (see [R])"))
                logo = fx.big("CODEKATA")
                L = [""] + [fx.c(x, fx.RAINBOW[(i + int(time.time())) % 8], bold=True) for i, x in enumerate(logo)]
                streak = streak_days(history["runs"])
                L += ["", fx.c(tr("하루 시작, 손가락 깨우기 — 타격감 코딩 카타", "Wake up your fingers — a coding kata that hits back"),
                               fx.WHITE, bold=True) + fx.c(f"  v{VERSION}", fx.DIM),
                      "",
                      f"{fx.c('player', fx.DIM)} {fx.c(store.player_name(cfg), fx.GOLD, bold=True)}   "
                      f"{fx.c('AI', fx.DIM)} {ai_st}   {fx.c(tr('랭킹', 'rank'), fx.DIM)} {rk_st}",
                      f"{fx.c(tr('연속', 'streak'), fx.DIM)} {fx.c(tr(f'{streak}일', f'{streak}d'), fx.ORANGE, bold=True)}   "
                      f"{fx.c(tr('랭크전 최고', 'ranked best'), fx.DIM)} {fx.c(fx.fmt(best) if best is not None else '-', fx.GOLD, bold=True)}"
                      + ("   " + fx.c("[debug]", fx.RED) if opts.debug else ""), ""]
                items = [("1", tr("⚔  랭크전", "⚔  Ranked"), tr("믹스 8스테이지 (러시+카타+퀴즈)", "8-stage mix (rush + kata + quiz)")),
                         ("2", tr("⌨  타자 러시", "⌨  Type Rush"), tr("코드 따라치기 · WPM", "type the code · WPM")),
                         ("3", tr("✎  카타", "✎  Kata"), tr("1~2줄 코드 작성 · 실행 채점", "write 1–2 lines · executed & judged")),
                         ("4", tr("?  퀴즈", "?  Quiz"), tr("코드 읽기 4지선다", "read code · 4 choices")),
                         ("5", tr("⚙  실기", "⚙  Exam"), tr("로봇SW개발기사 실기 · 퀴즈→카타→클론코딩→퀴즈→실전 (Python/C++)",
                                                          "Robot SW practical · quiz → kata → clone → quiz → task (Python/C++)"))]
                for k, name, desc in items:
                    L.append(fx.c(f" {k} ", fx.BLACK, bg=fx.GOLD, bold=True) + " " + fx.c(fx.pad(name, 14), fx.WHITE, bold=True)
                             + fx.c(desc, fx.GREY))
                langs_s = "  ".join(fx.c(x, fx.BLACK, bg=bank.LANG_COLOR.get(x, fx.WHITE), bold=True) if x == lang
                                    else fx.c(x, fx.DIM) for x in LANG_CHOICES)
                L += ["", fx.c(" ←→ ", fx.BLACK, bg=fx.SKY, bold=True) + tr(" 언어  ", " lang  ") + langs_s, "",
                      fx.c(tr("R 랭킹   S 통계   G 로그   A 인증   D 디버거 데모   L English   Q 종료",
                              "R ranking   S stats   G log   A auth   D debugger demo   L 한국어   Q quit"), fx.GREY)]
                fx.show(L)
                k = keys.get(1.0)
                if k is None:
                    continue
                if k in ("q", "Q", "ESC"):
                    break
                if k in ("l", "L"):
                    cfg["ui"] = "en" if i18n.UI == "ko" else "ko"
                    i18n.set_ui(cfg["ui"])
                    store.save_config(cfg)
                    src.clear()
                    snd.play("select")
                    continue
                if k in ("LEFT", "RIGHT"):
                    i = LANG_CHOICES.index(lang) if lang in LANG_CHOICES else 0
                    lang = LANG_CHOICES[(i + (1 if k == "RIGHT" else -1)) % len(LANG_CHOICES)]
                    cfg["lang"] = lang
                    store.save_config(cfg)
                    snd.play("select")
                    src.warm(["rush", "kata", "quiz"], [lang] if lang != "random" else cfg["langs"])
                    continue
                langs = cfg["langs"] if lang == "random" else [lang]
                if k == "5":
                    snd.play("select")
                    play(cfg, opts, "exam", [lang if lang in exam.EXAM_LANGS else "python"], exam.EXAM_STAGES, keys=keys)
                    continue
                mode = {"1": "mix", "2": "rush", "3": "kata", "4": "quiz"}.get(k)
                if mode:
                    snd.play("select")
                    play(cfg, opts, mode, langs, cfg.get("stages", store.RANKED_STAGES), keys=keys)
                    continue
                pages = {"s": lambda: stats_lines(store.load_history()), "g": lambda: log_lines(),
                         "a": lambda: auth_lines(cfg), "r": lambda: rank_lines(cfg)}
                if k.lower() in pages:
                    if k.lower() == "r":
                        fx.show([fx.c(tr("◐ 온라인 랭킹 불러오는 중...", "◐ loading online ranking..."), fx.YELLOW)])
                    fx.show(pages[k.lower()]() + ["", fx.c(tr("아무 키나 ▶ 메뉴", "any key ▶ menu"), fx.DIM)])
                    keys.get()
                elif k.lower() == "d":
                    p = bank.localize(bank.QUIZ[0])
                    tracer.replay(p["code"], keys, title=p["title"], sound=snd)
        except KeyboardInterrupt:
            pass
        finally:
            fx.leave()
    print(fx.c(tr("내일도 손가락 깨우러 오세요! 🔥", "Come back tomorrow and wake those fingers again! 🔥"), fx.GOLD, bold=True))


# ─── 서브커맨드 ─────────────────────────────────────────

def rank_setup(cfg):
    print(fx.c(tr("── 온라인 랭킹 설정 ──", "── online ranking setup ──"), fx.CYAN, bold=True))
    print(tr("1) github  — 공용 GitHub 레포에 각자 ranking/<login>.json 기록 (서버 불필요, 친구는 collaborator)",
             "1) github  — each player writes ranking/<login>.json in a shared GitHub repo (no server; friends are collaborators)"))
    print(tr("2) http    — `codekata serve` 랭킹 서버 주소", "2) http    — URL of a `codekata serve` ranking server"))
    print(tr("3) none    — 끄기", "3) none    — off"))
    ch = input(tr("선택 [1/2/3]: ", "choose [1/2/3]: ")).strip()
    if ch == "1":
        login = ""
        try:
            login = json.loads(subprocess.run(["gh", "api", "user"], capture_output=True, text=True).stdout)["login"]
        except Exception:  # noqa: BLE001
            pass
        default = f"{login}/codekata-ranking" if login else ""
        repo = input(tr("레포 owner/name", "repo owner/name") + f" [{default}]: ").strip() or default
        r = subprocess.run(["gh", "repo", "view", repo], capture_output=True, text=True)
        if r.returncode != 0:
            yn = input(tr(f"{repo} 레포가 없습니다. 공개 레포로 만들까요? [y/N]: ",
                          f"{repo} does not exist. Create it as a public repo? [y/N]: ")).strip().lower()
            if yn == "y":
                subprocess.run(["gh", "repo", "create", repo, "--public", "--description", "codekata online ranking"])
        cfg["rank"].update(backend="github", repo=repo)
    elif ch == "2":
        cfg["rank"].update(backend="http", url=input(tr("서버 URL (예: http://host:8787): ", "server URL (e.g. http://host:8787): ")).strip(),
                           token=input(tr("토큰 (없으면 Enter): ", "token (Enter for none): ")).strip())
    else:
        cfg["rank"]["backend"] = "none"
    name = input(tr("표시 이름", "display name") + f" [{store.player_name(cfg)}]: ").strip()
    if name:
        cfg["player"] = name
    store.save_config(cfg)
    print(fx.c(tr("저장 완료 →", "saved →"), fx.LIME), store.CONFIG_FILE)


def config_cmd(cfg, args):
    if not args.key:
        print(json.dumps(cfg, ensure_ascii=False, indent=2))
        return
    if args.value is None:
        cur = cfg
        for part in args.key.split("."):
            cur = cur[part]
        print(json.dumps(cur, ensure_ascii=False))
        return
    try:
        val = json.loads(args.value)
    except json.JSONDecodeError:
        val = args.value
    cur = cfg
    parts = args.key.split(".")
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = val
    store.save_config(cfg)
    print(f"{args.key} = {json.dumps(val, ensure_ascii=False)}")


def follow_log():
    path = LOG_DIR / f"{date.today().isoformat()}.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()
    print(fx.c(f"tail -f {path}  " + tr("(Ctrl-C 종료)", "(Ctrl-C to stop)"), fx.DIM))
    with open(path, encoding="utf-8") as f:
        f.seek(0, 2)
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue
                try:
                    print(event_line(json.loads(line)))
                except json.JSONDecodeError:
                    pass
        except KeyboardInterrupt:
            pass


def debug_cmd(cfg, opts, args):
    code = Path(args.file).read_text() if args.file else args.code
    if not code:
        print(tr("사용법: ", "usage: ") + "codekata debug FILE.py | codekata debug -c 'code'")
        return
    snd = Sound(cfg["sound"] and not opts.no_sound)
    with Keys() as keys:
        fx.enter()
        try:
            tracer.replay(code, keys, title=args.file or "<code>", sound=snd)
        except KeyboardInterrupt:
            pass
        finally:
            fx.leave()


def build_parser():
    ap = argparse.ArgumentParser(prog="codekata", description=tr("타격감 있는 터미널 코딩 카타 (ChatGPT 출제 + 디버거 + 온라인 랭킹)",
                                                                 "A terminal coding kata that hits back (ChatGPT problems + debugger + online ranking)"),
                                 epilog=tr("전역 옵션: --debug --no-fx --no-sound --no-color --offline --en --ko (어디에 써도 됨)",
                                           "global flags: --debug --no-fx --no-sound --no-color --offline --en --ko (anywhere)"))
    ap.add_argument("-V", "--version", action="version", version=f"codekata {VERSION}")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("play", help=tr("바로 게임 시작", "start a game"))
    p.add_argument("-m", "--mode", choices=list(MODES), default="mix")
    p.add_argument("-l", "--lang", default=None, help=tr("python|js|rust|cpp|go|... 또는 random", "python|js|rust|cpp|go|... or random"))
    p.add_argument("-n", "--stages", type=int, default=None,
                   help=tr(f"스테이지 수 (랭크전={store.RANKED_STAGES})", f"number of stages (ranked = {store.RANKED_STAGES})"))
    for m in ("rush", "kata", "quiz"):
        q = sub.add_parser(m, help=tr(f"{mode_label(m)} 모드로 바로 시작", f"start {mode_label(m)} mode"))
        q.add_argument("-l", "--lang", default=None)
        q.add_argument("-n", "--stages", type=int, default=None)
    ex = sub.add_parser("exam", help=tr("로봇SW개발기사 실기 대비 (Python/C++)", "Robot SW engineer practical exam prep (Python/C++)"))
    ex.add_argument("kind", nargs="?", choices=["mix", "quiz", "kata", "clone", "task", "list"], default="mix",
                    help=tr(f"mix = 랭크전({exam.EXAM_STAGES}스테이지), list = 실전 문제 목록",
                            f"mix = ranked ({exam.EXAM_STAGES} stages), list = list the real tasks"))
    ex.add_argument("-l", "--lang", choices=list(exam.EXAM_LANGS), default=None)
    ex.add_argument("-n", "--stages", type=int, default=None)
    ex.add_argument("-t", "--task", choices=[t["tid"] for t in exam.TASKS], default=None,
                    help=tr("실전 작업형 문제 고정", "pin one real task"))
    sub.add_parser("stats", help=tr("통계", "stats"))
    lg = sub.add_parser("log", help=tr("세션 로그 / 타임라인", "session log / timeline"))
    lg.add_argument("sid", nargs="?")
    lg.add_argument("--errors", action="store_true", help=tr("AI/랭킹 오류만", "AI / ranking errors only"))
    lg.add_argument("--raw", action="store_true", help=tr("JSONL 원본", "raw JSONL"))
    lg.add_argument("-f", "--follow", action="store_true", help=tr("실시간 tail", "follow live"))
    lg.add_argument("-n", type=int, default=15)
    rk = sub.add_parser("rank", help=tr("온라인 랭킹 (setup | push)", "online ranking (setup | push)"))
    rk.add_argument("action", nargs="?", choices=["show", "setup", "push"], default="show")
    rk.add_argument("-m", "--mode", choices=list(MODES), default="mix")
    rk.add_argument("-p", "--period", choices=["day", "week", "all"], default="week")
    rk.add_argument("-l", "--lang", default=None)
    au = sub.add_parser("auth", help=tr("ChatGPT(Codex) 로그인 상태 / 로그인", "ChatGPT (Codex) login status / login"))
    au.add_argument("action", nargs="?", choices=["status", "login"], default="status")
    db = sub.add_parser("debug", help=tr("디버거 킬캠: Python 코드 한 줄씩 리플레이", "debugger killcam: replay Python line by line"))
    db.add_argument("file", nargs="?")
    db.add_argument("-c", "--code")
    sv = sub.add_parser("serve", help=tr("랭킹 서버 실행", "run a ranking server"))
    sv.add_argument("--host", default="0.0.0.0")
    sv.add_argument("--port", type=int, default=8787)
    sv.add_argument("--db", default=str(store.HOME / "server.db"))
    sv.add_argument("--token", default=os.environ.get("CODEKATA_TOKEN", ""))
    cf = sub.add_parser("config", help=tr("설정 보기/변경 (예: config set rank.auto_push false)", "show / change settings (e.g. config set ui en)"))
    cf.add_argument("key", nargs="?")
    cf.add_argument("value", nargs="?")
    sub.add_parser("doctor", help=tr("환경 점검", "check the environment"))
    return ap


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    opts = argparse.Namespace(**{v: False for v in GLOBAL_FLAGS.values()})
    for flag, name in GLOBAL_FLAGS.items():
        if flag in argv:
            setattr(opts, name, True)
            argv = [a for a in argv if a != flag]
    if argv[:1] == ["config"] and argv[1:2] == ["set"]:
        argv = ["config"] + argv[2:]
    cfg = store.load_config()
    i18n.set_ui("en" if opts.en else "ko" if opts.ko else cfg.get("ui", "auto"))
    args = build_parser().parse_args(argv)
    fx.S.color = cfg["color"] and not opts.no_color and not os.environ.get("NO_COLOR")
    fx.S.fx = cfg["fx"] and not opts.no_fx
    if not sys.stdout.isatty():
        fx.S.color = False
    LOG.setup(debug=opts.debug)
    if os.environ.get("CODEKATA_SEED"):
        import random
        random.seed(int(os.environ["CODEKATA_SEED"]))
    interactive = args.cmd in (None, "play", "rush", "kata", "quiz", "debug") or (args.cmd == "exam" and args.kind != "list")
    if interactive and not (sys.stdin.isatty() and sys.stdout.isatty()):
        sys.exit(tr("codekata: 터미널(TTY)에서 실행해 주세요.", "codekata: please run this in a terminal (TTY)."))

    if args.cmd is None:
        menu(cfg, opts)
    elif args.cmd in ("play", "rush", "kata", "quiz"):
        mode = args.mode if args.cmd == "play" else args.cmd
        lang = args.lang or cfg.get("lang", "python")
        langs = cfg["langs"] if lang == "random" else [lang]
        play(cfg, opts, mode, langs, args.stages or cfg.get("stages", store.RANKED_STAGES))
    elif args.cmd == "exam":
        if args.kind == "list":
            emit(exam_list_lines())
            return
        lang = args.lang or (cfg.get("lang") if cfg.get("lang") in exam.EXAM_LANGS else "python")
        mode = "exam" if args.kind == "mix" else f"exam-{args.kind}"
        default_n = {"exam": exam.EXAM_STAGES, "exam-task": 1 if args.task else 2,
                     "exam-clone": 1 if args.task else 2}.get(mode, store.RANKED_STAGES)
        play(cfg, opts, mode, [lang], args.stages or default_n, task=args.task)
    elif args.cmd == "stats":
        emit(stats_lines(store.load_history()))
    elif args.cmd == "log":
        if args.follow:
            follow_log()
        elif args.raw:
            for e in read_events():
                if not args.sid or (e.get("sid") or "").startswith(args.sid):
                    print(json.dumps(e, ensure_ascii=False))
        else:
            emit(log_lines(args.sid, args.errors, args.n))
    elif args.cmd == "rank":
        if args.action == "setup":
            rank_setup(cfg)
        else:
            emit(rank_lines(cfg, args.mode, args.period, args.lang))
    elif args.cmd == "auth":
        if args.action == "login":
            sys.exit(subprocess.call(["codex", "login"]))
        emit(auth_lines(cfg))
    elif args.cmd == "debug":
        debug_cmd(cfg, opts, args)
    elif args.cmd == "serve":
        from .server import serve
        Path(args.db).parent.mkdir(parents=True, exist_ok=True)
        serve(args.host, args.port, args.db, args.token)
    elif args.cmd == "config":
        config_cmd(cfg, args)
    elif args.cmd == "doctor":
        emit(doctor_lines(cfg))
