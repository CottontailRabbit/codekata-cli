"""초경량 랭킹 서버 (표준 라이브러리 + SQLite).  `codekata serve --port 8787 --token SECRET`"""
import json
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .i18n import tr
from .rank import FIELDS

MAX_BODY = 8192


def serve(host, port, db_path, token=""):
    db = sqlite3.connect(db_path, check_same_thread=False)
    db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, player TEXT, data TEXT, score INTEGER, "
               "created TEXT DEFAULT CURRENT_TIMESTAMP)")
    db.commit()
    lock = threading.Lock()

    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _authed(self):
            return not token or self.headers.get("X-Codekata-Token") == token

        def do_GET(self):
            if self.path.split("?")[0] != "/api/runs":
                return self._send(404, {"error": "not found"})
            if not self._authed():
                return self._send(401, {"error": "bad token"})
            with lock:
                rows = db.execute("SELECT data FROM runs ORDER BY score DESC LIMIT 5000").fetchall()
            self._send(200, [json.loads(r[0]) for r in rows])

        def do_POST(self):
            if self.path != "/api/runs":
                return self._send(404, {"error": "not found"})
            if not self._authed():
                return self._send(401, {"error": "bad token"})
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_BODY:
                return self._send(413, {"error": "body size"})
            try:
                rec = json.loads(self.rfile.read(n))
                rec = {k: rec.get(k) for k in FIELDS}
                assert isinstance(rec["id"], str) and isinstance(rec["player"], str) and rec["player"]
                assert isinstance(rec["score"], int) and 0 <= rec["score"] < 10_000_000
            except (ValueError, AssertionError, TypeError, KeyError):
                return self._send(400, {"error": "bad run"})
            with lock:
                db.execute("INSERT OR IGNORE INTO runs (id, player, data, score) VALUES (?, ?, ?, ?)",
                           (rec["id"], rec["player"][:32], json.dumps(rec, ensure_ascii=False), rec["score"]))
                db.commit()
            self._send(201, {"ok": True})

        def log_message(self, fmt, *args):
            print(f"[codekata-server] {self.address_string()} {fmt % args}")

    httpd = ThreadingHTTPServer((host, port), H)
    print(tr("codekata 랭킹 서버", "codekata ranking server") + f": http://{host}:{port}  (db={db_path}, token={'on' if token else 'off'})")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
