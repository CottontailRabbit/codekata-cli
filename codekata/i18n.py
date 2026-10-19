"""UI 언어 (ko / en). tr("한국어", "English") 로 현재 언어 문자열을 고른다."""
import os

UI = "ko"


def detect():
    # gettext 우선순위: LANGUAGE > LC_ALL > LC_MESSAGES > LANG
    for var in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        loc = os.environ.get(var, "")
        if loc and loc not in ("C", "POSIX", "C.UTF-8"):
            return "ko" if loc.lower().startswith("ko") else "en"
    return "en"


def set_ui(value):
    global UI
    UI = value if value in ("ko", "en") else detect()
    return UI


def tr(ko, en):
    return en if UI == "en" else ko


def pick(v):
    """("ko", "en") 튜플이나 {"ko":..,"en":..} 사전이면 현재 언어 쪽을, 문자열이면 그대로."""
    if isinstance(v, (tuple, list)) and len(v) == 2 and all(isinstance(x, str) for x in v):
        return tr(v[0], v[1])
    if isinstance(v, dict) and "ko" in v:
        return v.get(UI) or v["ko"]
    return v
