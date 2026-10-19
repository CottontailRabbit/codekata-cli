"""온라인 랭킹.

백엔드
- github: 공용 GitHub 레포의 ranking/<login>.json 에 각자 기록 (gh CLI 인증 사용, 서버 불필요)
- http  : `codekata serve` 로 띄운 랭킹 서버
"""
import base64
import json
import shutil
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

from . import fx
from .i18n import tr
from .log import LOG

KEEP_RUNS = 300
FIELDS = ("id", "ts", "date", "player", "mode", "lang", "stages", "score", "grade", "max_combo", "acc", "wpm",
          "kos", "hearts", "flawless", "ver")


def entry(rec):
    return {k: rec.get(k) for k in FIELDS}


class RankError(Exception):
    pass


class GithubBackend:
    name = "github"

    def __init__(self, repo, path="ranking"):
        if not repo:
            raise RankError(tr("rank.repo 미설정 (codekata rank setup)", "rank.repo not set (codekata rank setup)"))
        if not shutil.which("gh"):
            raise RankError(tr("gh CLI가 없습니다", "gh CLI not found"))
        self.repo, self.path = repo, path.strip("/")
        self._login = None

    def _gh(self, *args, input=None):
        p = subprocess.run(["gh", "api", *args], input=input, capture_output=True, text=True, timeout=30)
        if p.returncode != 0:
            raise RankError((p.stderr or p.stdout).strip()[:200])
        return json.loads(p.stdout) if p.stdout.strip() else None

    def login(self):
        if not self._login:
            self._login = self._gh("user")["login"]
        return self._login

    def _get(self, name):
        try:
            data = self._gh(f"repos/{self.repo}/contents/{self.path}/{name}")
        except RankError as e:
            if "Not Found" in str(e) or "404" in str(e):
                return None, None
            raise
        return json.loads(base64.b64decode(data["content"]).decode()), data["sha"]

    def push(self, rec):
        me = self.login()
        name = f"{me}.json"
        for _ in range(3):
            doc, sha = self._get(name)
            doc = doc or {"login": me, "runs": []}
            doc["player"] = rec.get("player") or me
            doc["login"] = me
            if not any(r.get("id") == rec["id"] for r in doc["runs"]):
                doc["runs"].append(entry(rec))
            doc["runs"] = sorted(doc["runs"], key=lambda r: r.get("ts") or "")[-KEEP_RUNS:]
            body = {"message": f"codekata: {me} {rec['mode']} {rec['score']}",
                    "content": base64.b64encode(json.dumps(doc, ensure_ascii=False, indent=1).encode()).decode()}
            if sha:
                body["sha"] = sha
            try:
                self._gh("-X", "PUT", f"repos/{self.repo}/contents/{self.path}/{name}", "--input", "-",
                         input=json.dumps(body))
                return
            except RankError as e:
                if "sha" not in str(e) and "409" not in str(e):
                    raise
        raise RankError(tr("push 충돌 반복", "push kept conflicting"))

    def fetch(self):
        try:
            items = self._gh(f"repos/{self.repo}/contents/{self.path}")
        except RankError as e:
            if "Not Found" in str(e) or "404" in str(e):
                return []
            raise
        names = [it["name"] for it in items if it["name"].endswith(".json")]
        runs = []

        def one(n):
            doc, _ = self._get(n)
            if not doc:
                return []
            login = doc.get("login") or n[:-5]
            return [dict(r, player=doc.get("player") or login, login=login) for r in doc.get("runs", [])]
        with ThreadPoolExecutor(8) as ex:
            for rs in ex.map(one, names):
                runs += rs
        return runs

    def whoami(self):
        return self.login()


class HttpBackend:
    name = "http"

    def __init__(self, url, token=""):
        if not url:
            raise RankError(tr("rank.url 미설정 (codekata rank setup)", "rank.url not set (codekata rank setup)"))
        self.url, self.token = url.rstrip("/"), token

    def _req(self, method, path, body=None):
        req = urllib.request.Request(self.url + path, method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json", "X-Codekata-Token": self.token})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            raise RankError(f"HTTP {e.code}: {e.read()[:200].decode(errors='ignore')}")
        except (urllib.error.URLError, OSError) as e:
            raise RankError(tr("서버 연결 실패: ", "cannot reach server: ") + str(e))

    def push(self, rec):
        self._req("POST", "/api/runs", entry(rec))

    def fetch(self):
        return self._req("GET", "/api/runs")

    def whoami(self):
        return None


def backend(cfg):
    r = cfg["rank"]
    if r["backend"] == "github":
        return GithubBackend(r["repo"], r.get("path", "ranking"))
    if r["backend"] == "http":
        return HttpBackend(r["url"], r.get("token", ""))
    return None


def board(runs, mode="mix", period="all", lang=None):
    """플레이어별 최고 점수 런 → 점수순 정렬."""
    today = date.today()
    since = {"day": today, "week": today - timedelta(days=today.weekday()), "all": date.min}[period]
    best = {}
    for r in runs:
        if r.get("mode") != mode or (lang and r.get("lang") != lang):
            continue
        try:
            if date.fromisoformat(r.get("date", "1970-01-01")) < since:
                continue
        except ValueError:
            continue
        who = r.get("login") or r.get("player")
        if who not in best or r["score"] > best[who]["score"]:
            best[who] = r
    return sorted(best.values(), key=lambda r: -r["score"])


def render_board(rows, me=None, highlight_id=None, top=10, title=""):
    L = []
    if title:
        L.append(fx.c(title, fx.GOLD, bold=True))
    L.append(fx.c(f"{'#':>3}  {'PLAYER':<16}{'SCORE':>10}  {'G':<3}{'COMBO':>6}{'ACC':>6}{'WPM':>6}  DATE", fx.DIM))
    if not rows:
        L.append(fx.c(tr("   아직 기록이 없습니다. 첫 번째 주인공이 되세요!", "   No records yet. Be the first!"), fx.DIM))
        return L
    medal = {1: fx.GOLD, 2: 250, 3: 173}
    mine = [i for i, r in enumerate(rows) if (me and (r.get("login") == me or r.get("player") == me))
            or (highlight_id and r.get("id") == highlight_id)]
    show = set(range(min(top, len(rows))))
    for i in mine:
        show |= {i - 1, i, i + 1}
    prev = -1
    for i in sorted(x for x in show if 0 <= x < len(rows)):
        if i != prev + 1:
            L.append(fx.c("  ⋮", fx.DARK))
        prev = i
        r = rows[i]
        name = (r.get("player") or r.get("login") or "?")[:15]
        line = (f"{i + 1:>3}  {fx.pad(name, 16)}{fx.fmt(r['score']):>10}  {r.get('grade', ''):<3}"
                f"{r.get('max_combo', 0):>6}{(r.get('acc') or 0) * 100:>5.0f}%{(r.get('wpm') or 0):>6.0f}  "
                f"{(r.get('date') or '')[5:]}")
        if i in mine:
            L.append(fx.c("▶" + line[1:], fx.BLACK, bg=fx.GOLD, bold=True))
        else:
            L.append(fx.c(line, medal.get(i + 1, 253), bold=i < 3))
    return L


def rivalry(rows, me):
    """내 순위와 바로 위 라이벌과의 점수차 멘트."""
    for i, r in enumerate(rows):
        if r.get("login") == me or r.get("player") == me:
            if i == 0:
                gap = r["score"] - rows[1]["score"] if len(rows) > 1 else None
                if gap is None:
                    return tr("현재 1위! 독보적!", "You're #1! Untouchable!")
                return tr(f"현재 1위! 2위와 {fx.fmt(gap)}점 차이로 독주 중!", f"You're #1, {fx.fmt(gap)} points ahead of #2!")
            up = rows[i - 1]
            need = fx.fmt(up["score"] - r["score"] + 1)
            return tr(f"{i + 1}위 / {len(rows)}명 — {i}위 {up.get('player')}까지 {need}점 남았습니다!",
                      f"#{i + 1} of {len(rows)} — {need} more points to pass #{i} {up.get('player')}!")
    return None


def sync(cfg, history, rec=None):
    """랭크전 기록 push(실패분 재시도 포함) 후 전체 런을 반환."""
    be = backend(cfg)
    if be is None:
        return None, None, tr("랭킹 백엔드 미설정 — `codekata rank setup`", "no ranking backend — `codekata rank setup`")
    pending = history.setdefault("pending_push", [])
    if rec is not None and rec.get("ranked"):
        pending.append(rec)
    errors = []
    if cfg["rank"].get("auto_push", True) or rec is None:
        left = []
        for r in pending:
            try:
                be.push(r)
                LOG.ev("rank_push", ok=True, backend=be.name, score=r["score"], run=r["id"])
            except RankError as e:
                left.append(r)
                errors.append(str(e))
                LOG.ev("rank_push", ok=False, backend=be.name, error=str(e))
        history["pending_push"] = left
    try:
        runs = be.fetch()
    except RankError as e:
        LOG.ev("rank_fetch", ok=False, error=str(e))
        return None, be, tr("랭킹 조회 실패: ", "ranking fetch failed: ") + str(e)
    LOG.ev("rank_fetch", ok=True, n=len(runs))
    me = None
    try:
        me = be.whoami()
    except RankError:
        pass
    return runs, me, ("; ".join(errors[:1]) if errors else None)
