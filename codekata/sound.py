"""효과음: 첫 실행 때 WAV를 합성해 두고 aplay/paplay/afplay로 논블로킹 재생."""
import math
import random
import shutil
import struct
import subprocess
import wave

from .store import HOME

SR = 22050
SFX_DIR = HOME / "sfx-v1"


def _env(i, n, attack=0.002, k=6.0):
    t = i / SR
    a = min(1.0, t / attack) if attack else 1.0
    return a * math.exp(-k * i / n)


def _tone(freq0, freq1, ms, vol=0.6, k=6.0, wave_fn=math.sin, noise=0.0):
    n = int(SR * ms / 1000)
    out, ph = [], 0.0
    for i in range(n):
        f = freq0 + (freq1 - freq0) * (i / n)
        ph += 2 * math.pi * f / SR
        s = wave_fn(ph) * (1 - noise) + (random.uniform(-1, 1) * noise)
        out.append(s * vol * _env(i, n, k=k))
    return out


def _square(ph):
    return 1.0 if math.sin(ph) >= 0 else -1.0


def _mix(*tracks):
    n = max(len(t) for t in tracks)
    return [max(-1.0, min(1.0, sum(t[i] for t in tracks if i < len(t)))) for i in range(n)]


def _cat(*tracks):
    out = []
    for t in tracks:
        out += t
    return out


def _noise_burst(ms, vol=0.7, k=12.0, smooth=1):
    n = int(SR * ms / 1000)
    raw = [random.uniform(-1, 1) for _ in range(n)]
    if smooth > 1:
        acc, sm = 0.0, []
        for x in raw:
            acc += (x - acc) / smooth
            sm.append(acc * 2.5)
        raw = sm
    return [raw[i] * vol * _env(i, n, attack=0, k=k) for i in range(n)]


def _sounds():
    random.seed(7)
    return {
        "key": _mix(_noise_burst(14, 0.25, 18), _tone(1900, 1500, 14, 0.12, 10)),
        "hit": _mix(_tone(240, 55, 110, 0.85, 7), _noise_burst(35, 0.6, 14, smooth=3)),
        "crit": _mix(_tone(260, 45, 200, 0.9, 5), _noise_burst(70, 0.7, 10, smooth=2),
                     _cat([0.0] * int(SR * 0.03), _tone(1320, 880, 140, 0.25, 6))),
        "miss": _tone(95, 60, 220, 0.45, 4, wave_fn=_square),
        "typo": _tone(160, 120, 45, 0.25, 8, wave_fn=_square),
        "combo": _cat(_tone(660, 660, 55, 0.35, 5), _tone(880, 880, 55, 0.35, 5), _tone(1320, 1320, 110, 0.4, 4)),
        "streak": _cat(_tone(990, 990, 40, 0.25, 6), _tone(1480, 1480, 70, 0.3, 5)),
        "ko": _mix(_noise_burst(800, 0.8, 4, smooth=6), _tone(70, 35, 800, 0.9, 3)),
        "heart": _cat(_tone(520, 520, 90, 0.4, 3), _tone(390, 390, 90, 0.4, 3), _tone(260, 200, 220, 0.45, 3)),
        "select": _tone(1200, 1300, 30, 0.25, 8),
        "tick": _tone(2400, 2400, 8, 0.12, 10),
        "fanfare": _cat(_tone(523, 523, 110, 0.4, 3), _tone(659, 659, 110, 0.4, 3),
                        _tone(784, 784, 110, 0.4, 3), _tone(1046, 1046, 380, 0.45, 2)),
        "var": _cat(*[_tone(880, 880, 60, 0.2, 5) + [0.0] * int(SR * 0.06) for _ in range(3)]),
    }


def _write(path, samples):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32000)) for s in samples))


class Sound:
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.cmd = None
        self.procs = []
        if not enabled:
            return
        for cand in (["aplay", "-q"], ["paplay"], ["afplay"]):
            if shutil.which(cand[0]):
                self.cmd = cand
                break
        if not self.cmd:
            self.enabled = False
            return
        try:
            if not (SFX_DIR / "ko.wav").exists():
                SFX_DIR.mkdir(parents=True, exist_ok=True)
                for name, samples in _sounds().items():
                    _write(SFX_DIR / f"{name}.wav", samples)
        except OSError:
            self.enabled = False

    def play(self, name):
        if not self.enabled:
            return
        self.procs = [p for p in self.procs if p.poll() is None]
        if name in ("key", "tick") and len(self.procs) > 3:
            return
        try:
            self.procs.append(subprocess.Popen(self.cmd + [str(SFX_DIR / f"{name}.wav")],
                                               stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL, start_new_session=True))
        except OSError:
            self.enabled = False
