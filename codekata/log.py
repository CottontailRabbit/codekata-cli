"""이벤트 로깅: ~/.codekata/logs/YYYY-MM-DD.jsonl (+ --debug 시 debug.log)."""
import json
import logging
import threading
import time
from collections import deque
from datetime import date, datetime

from .store import HOME

LOG_DIR = HOME / "logs"


class EventLog:
    def __init__(self):
        self.sid = None
        self.debug = False
        self.recent = deque(maxlen=5)
        self._lock = threading.Lock()
        self.dbg = logging.getLogger("codekata")

    def setup(self, debug=False):
        self.debug = debug
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        if debug and not self.dbg.handlers:
            h = logging.FileHandler(HOME / "debug.log", encoding="utf-8")
            h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(threadName)s %(message)s"))
            self.dbg.addHandler(h)
            self.dbg.setLevel(logging.DEBUG)

    def ev(self, type, **data):
        rec = {"ts": round(time.time(), 3), "t": datetime.now().isoformat(timespec="milliseconds"),
               "sid": self.sid, "type": type, **data}
        line = json.dumps(rec, ensure_ascii=False, default=str)
        with self._lock:
            LOG_DIR.mkdir(parents=True, exist_ok=True)
            with open(LOG_DIR / f"{date.today().isoformat()}.jsonl", "a", encoding="utf-8") as f:
                f.write(line + "\n")
            self.recent.append(f"{type} {_brief(data)}")
        self.dbg.debug(line)
        return rec


def _brief(data):
    keys = ("ok", "kind", "title", "dmg", "combo", "ms", "error", "source")
    return " ".join(f"{k}={data[k]}" for k in keys if k in data)[:70]


def read_events(limit_days=None):
    files = sorted(LOG_DIR.glob("*.jsonl"))
    if limit_days:
        files = files[-limit_days:]
    for path in files:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


LOG = EventLog()
