"""설정/히스토리 저장소 (~/.codekata)."""
import copy
import json
import os
import tempfile
from pathlib import Path

HOME = Path(os.environ.get("CODEKATA_HOME") or Path.home() / ".codekata")
CONFIG_FILE = HOME / "config.json"
HISTORY_FILE = HOME / "history.json"

RANKED_STAGES = 8  # 랭크전 규격: 8스테이지

DEFAULTS = {
    "player": "",
    "ui": "auto",              # auto | ko | en  (auto = $LANG)
    "provider": "codex",       # codex(ChatGPT 로그인) | offline
    "model": "",               # 비우면 ~/.codex/config.toml 기본 모델
    "effort": "low",
    "lang": "python",
    "langs": ["python", "js", "rust", "cpp"],
    "stages": RANKED_STAGES,
    "sound": True,
    "fx": True,
    "color": True,
    "ai_judge": True,          # 문자열 채점 실패 시 AI VAR 판독
    "prefetch": 3,
    "rank": {
        "backend": "none",     # none | github | http
        "repo": "",            # github: owner/name
        "path": "ranking",
        "url": "",             # http: https://host:port
        "token": "",
        "auto_push": True,
    },
}


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return copy.deepcopy(default)


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name, suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_config():
    return _merge(DEFAULTS, load_json(CONFIG_FILE, {}))


def save_config(cfg):
    save_json(CONFIG_FILE, cfg)


def load_history():
    h = load_json(HISTORY_FILE, {})
    h.setdefault("runs", [])
    h.setdefault("seen", {})
    h.setdefault("pending_push", [])
    return h


def save_history(h):
    for lang, titles in h["seen"].items():
        h["seen"][lang] = titles[-200:]
    save_json(HISTORY_FILE, h)


def player_name(cfg):
    return cfg.get("player") or os.environ.get("USER") or "player"
