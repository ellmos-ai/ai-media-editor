"""Gruselige Ambient-Atmo für den Halloween-Loop, durchkomponiert auf dem Szenen-/Pausenraster.

Eigene Synthese (numpy/scipy, Instrumente aus synth.py = VisionFlow-v5-Werkzeug), keine Samples,
keine Musik-KI. Bett (Drohne + Wind) folgt dem Raster, jede Szene hat eigene Klangereignisse auf
ihren Animationsmomenten, jede Ruhephase eine eigene Spieluhr-Phrase. Loopfähig (Nachhall wird an
den Anfang überblendet). Pegel: −16 LUFS-I; WAV ≤ −3,5 dBTP, damit auch nach AAC-Kodierung ≤ −1,5 dBTP (gemessen mit ffmpeg ebur128).

Aufruf: python -m ai_media_editor.tools.atmo loop.json -o atmo.wav [--pause 8]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal
from scipy.io import wavfile

if __package__:
    from .synth import (
        SR,
        _rng,
        bandpass,
        bdrum,
        env,
        fm_bell,
        glock,
        highpass,
        lowpass,
        make_ir,
        pizz,
    )
else:  # pragma: no cover - Direktausführung aus dem Ordner
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from synth import (  # type: ignore[no-redef]
        SR,
        _rng,
        bandpass,
        bdrum,
        env,
        fm_bell,
        glock,
        highpass,
        lowpass,
        make_ir,
        pizz,
    )


def hz(m: float) -> float:
    return float(440.0 * 2 ** ((m - 69) / 12))


class Mix:
    def __init__(self, seconds: float) -> None:
        self.n = int(seconds * SR)
        self.wet = np.zeros((self.n, 2))   # Ereignisse → Hall
        self.dry = np.zeros((self.n, 2))   # Bett

    def add(
        self,
        t: float,
        x: np.ndarray,
        gain: float = 1.0,
        pan: float = 0.0,
        bus: str = "wet",
    ) -> None:
        i = int(t * SR)
        if i >= self.n or i + len(x) <= 0:
            return
        x = x[max(0, -i): self.n - i] * gain
        i = max(0, i)
        a = (pan + 1) * np.pi / 4
        b = self.wet if bus == "wet" else self.dry
        b[i: i + len(x), 0] += x * np.cos(a)
        b[i: i + len(x), 1] += x * np.sin(a)


def noise(key: Any, sec: float) -> np.ndarray:
    return _rng("n", key).uniform(-1, 1, int(sec * SR))


def lfo(key: Any, n: int, rate: float) -> np.ndarray:
    """Glatte Zufallskurve 0..1 mit ~rate Hz."""
    k = max(4, int(n / SR * rate) + 4)
    pts = _rng("lfo", key).uniform(0, 1, k)
    return np.interp(np.linspace(0, k - 3, n), np.arange(k), pts)


# ---------------------------------------------------------------- Klangereignisse
def hit(m: Mix, t: float, g: float = 1.0) -> None:          # tiefer Aufprall
    m.add(t, lowpass(bdrum(1.0), 220), 1.2 * g)
    m.add(t, lowpass(noise(("hit", t), 0.5), 900) * np.exp(-np.arange(int(0.5 * SR)) / (0.08 * SR)), 0.35 * g)


def swell(m: Mix, t_end: float, dur: float, g: float = 1.0) -> None:   # anschwellendes Rauschen, endet auf t_end
    n = int(dur * SR)
    x = highpass(noise(("sw", t_end), dur), 1500) * np.linspace(0, 1, n) ** 3
    m.add(t_end - dur, x, 0.5 * g, pan=0.0)


def stinger(m: Mix, t: float, g: float = 1.0) -> None:      # Schreck: dissonantes Glockenbündel + Aufprall
    for k, mid in enumerate((50, 51, 57, 68, 80)):
        m.add(t + 0.01 * k, fm_bell(hz(mid), 1.5, 0.9, 1.0), 0.55 * g, pan=-0.6 + 0.3 * k)
    hit(m, t, g)


def whoosh(m: Mix, t: float, dur: float, up: bool = True, g: float = 1.0) -> None:
    n = int(dur * SR)
    lo, hi = bandpass(noise(("wl", t), dur), 200, 700), bandpass(noise(("wh", t), dur), 1200, 4000)
    k = np.linspace(0, 1, n) if up else np.linspace(1, 0, n)
    e = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    m.add(t, (lo * (1 - k) + hi * k) * e, 0.7 * g)


def heartbeat(m: Mix, t: float, g: float = 1.0) -> None:
    for dt, v in ((0.0, 1.0), (0.22, 0.7)):
        m.add(t + dt, lowpass(bdrum(v), 140), 1.0 * g)


def bell(
    m: Mix,
    t: float,
    mid: float,
    g: float = 0.4,
    pan: float = 0.0,
    kind: str = "glock",
) -> None:
    f = {"glock": glock, "fm": fm_bell, "pizz": pizz}[kind]
    m.add(t, f(hz(mid), 0.6, 1.0, 0.6), g, float(pan))


def skitter(m: Mix, t0: float, t1: float, per_s: float, key: Any, g: float = 0.18) -> None:
    r = _rng("sk", key)
    for t in np.sort(r.uniform(t0, t1, int((t1 - t0) * per_s))):
        x = highpass(r.uniform(-1, 1, int(0.004 * SR)), 2500) * np.hanning(int(0.004 * SR))
        m.add(float(t), x, float(g * r.uniform(0.4, 1.0)), pan=float(r.uniform(-0.9, 0.9)))


def flutter(m: Mix, t0: float, t1: float, rate: float, g: float = 0.5) -> None:
    n = int((t1 - t0) * SR)
    am = 0.5 + 0.5 * np.sin(2 * np.pi * rate * np.arange(n) / SR)
    m.add(t0, bandpass(noise(("fl", t0), t1 - t0), 300, 1300) * am ** 3 * env(n, 0.3, t1 - t0 - 0.6, 0.2), g)


def snore(m: Mix, t0: float, t1: float, g: float = 0.6) -> None:
    n = int((t1 - t0) * SR)
    br = np.clip(np.sin(2 * np.pi * 0.42 * np.arange(n) / SR), 0, 1) ** 2
    m.add(t0, lowpass(noise(("sn", t0), t1 - t0), 400) * br, g)


def slurp(m: Mix, t: float, g: float = 0.6) -> None:
    whoosh(m, t, 0.55, up=True, g=g)
    m.add(t + 0.5, pizz(hz(43), 0.3, 1.0, 0.2), 0.8 * g)


# ---------------------------------------------------------------- Szenen (Zeiten relativ zum Clipstart)
def scene_cues(m: Mix, sid: str, s: float) -> None:
    if sid == "01-weisse-frau":
        swell(m, s + 16.7, 1.6)
        stinger(m, s + 16.7, 1.1)
        bell(m, s + 16.7, 88, 0.3, kind="fm")
    elif sid == "05-kuerbis-lacht":
        for k in range(7):
            bell(m, s + 8 + k * 0.48, (62, 65, 62, 69, 62, 65, 74)[k], 0.5, pan=-0.3 + 0.1 * k, kind="pizz")
        for k in range(14):
            bell(m, s + 15.1 + k * 0.32, 50 + (0, 3, 7, 10, 12, 10, 7, 3)[k % 8], 0.55, kind="pizz")
        for k in range(5):
            bell(m, s + 21.2 + k * 0.28, 74 + (0, 1, 0, 1, 3)[k], 0.35, kind="pizz")
    elif sid == "03-riesenspinne":
        for k in range(10):
            bell(m, s + 1.4 + k * 0.6, 62 - k, 0.45, pan=0.0, kind="pizz")
        skitter(m, s + 12, s + 15.5, 28, sid, 0.25)
        swell(m, s + 16.3, 1.0)
        stinger(m, s + 16.35, 1.0)
        whoosh(m, s + 18.2, 1.4, up=True, g=0.8)
        skitter(m, s + 22.5, s + 26, 18, sid + "b", 0.2)
    elif sid == "08-bettlakengespenst":
        for k in range(6):
            bell(m, s + 5 + k * 0.38, (74, 77, 81, 86, 89, 93)[k], 0.3, pan=-0.5 + 0.2 * k)
        bell(m, s + 7.6, 57, 0.6, kind="fm")
        for k in range(6):
            bell(m, s + 12 + k * 0.2, (89, 86, 81, 77, 74, 69)[k], 0.3)
        hit(m, s + 13.2, 0.7)
        for k in range(8):
            bell(m, s + 13.5 + k * 0.3, 81 + (0, 1)[k % 2], 0.18, pan=float(np.sin(k)))
        for k in range(10):
            bell(m, s + 19 + k * 0.2, 69 + (0, 3)[k % 2], 0.3, kind="pizz", pan=0.5)
    elif sid == "06-scream-opfer":
        swell(m, s + 1.5, 0.8)
        stinger(m, s + 1.5, 1.0)
        for t in (5.5, 7.2, 8.4, 15.6, 16.6):
            hit(m, s + t, 0.75)
        skitter(m, s + 9.9, s + 14.5, 14, sid, 0.12)
        swell(m, s + 18.4, 1.2, 0.9)
        whoosh(m, s + 18.4, 1.0, up=False, g=1.0)
        hit(m, s + 19.25, 0.8)
    elif sid == "02-schleimgeist":
        for t in (7.6, 14.4, 22.8):
            for k, mid in enumerate((81, 85, 88)):
                bell(m, s + t + 0.09 * k, mid, 0.28, pan=0.3)
        slurp(m, s + 20.2)
        for k in range(6):
            bell(m, s + 20.8 + k * 0.17, 45 + 2 * k, 0.4, kind="pizz", pan=-0.4 + 0.15 * k)
        whoosh(m, s + 26.2, 2.2, up=True, g=0.6)
    elif sid == "07-vampir-fledermaus":
        for k, mid in enumerate((38, 41, 45, 44)):
            bell(m, s + 1.5 + 2.5 * k, mid, 0.45, kind="fm")
        swell(m, s + 13.2, 1.6)
        whoosh(m, s + 13.2, 1.6, up=True)
        for k, mid in enumerate((74, 75, 80, 86)):
            bell(m, s + 13.25 + 0.05 * k, mid, 0.3, kind="fm", pan=-0.5 + 0.33 * k)
        flutter(m, s + 13.8, s + 21.6, 4.2, 0.45)
        swell(m, s + 21.4, 2.2, 0.8)
    elif sid == "11-kobolde-schatz":
        for k, t in enumerate((1.6, 2.2, 2.8)):
            bell(m, s + t + 0.3, (67, 71, 74)[k], 0.4, kind="pizz", pan=(-0.6, 0.0, 0.6)[k])
        for k in range(6):
            bell(m, s + 4.6 + 1.6 * k + 0.95, 86 + (0, 2, 4, 5, 7, 9)[k], 0.25, pan=-0.6)
        hit(m, s + 15.8, 0.5)
        bell(m, s + 15.8, 79, 0.5, kind="fm")
        for k in range(3):
            bell(m, s + 16.1 + 0.6 * k, 93, 0.15, pan=-0.6)
        snore(m, s + 21.0, s + 27.5, 0.55)
        bell(m, s + 27.6, 62, 0.6, kind="fm")
        for k in range(3):
            bell(m, s + 31.5 + 0.15 * k, (74, 67, 62)[k], 0.45, kind="pizz", pan=(-0.6, 0.6, 0.0)[k])
    elif sid == "09-silhouette":
        bell(m, s + 17.45, 93, 0.25, kind="fm")
        hit(m, s + 17.45, 0.6)
        for k in range(14):
            heartbeat(m, s + 18 + 6 * (1 - (1 - k / 14) ** 1.6), 0.55 + 0.03 * k)
        swell(m, s + 24.6, 1.2, 0.7)
    elif sid == "04-kleine-spinnen":
        skitter(m, s + 1, s + 12, 40, sid + "a", 0.14)
        skitter(m, s + 12, s + 22.5, 70, sid + "b", 0.14)
        skitter(m, s + 22.5, s + 27, 140, sid + "c", 0.16)
        for k, mid in enumerate((70, 69, 70, 69, 70, 69)):
            bell(m, s + 4 + 3 * k, mid, 0.2, kind="fm")
    elif sid == "10-hexe-lockt":
        motif = (74, 77, 76, 73, 74, 81, 80, 77, 74)
        for k in range(9):
            bell(m, s + 7.1 + k * 1.45, motif[k], 0.32, pan=-0.3)
        for k in range(12):
            bell(m, s + 21 + 0.11 * k, 88 + (0, 1)[k % 2], 0.12, kind="fm", pan=0.3)
        swell(m, s + 26, 2.4, 0.5)


PAUSE_PHRASES: list[list[int | None]] = [  # je Ruhephase eine eigene Spieluhr-Phrase (None = Pause), durchkomponiert
    [74, 77, 81, 80, 77, 74], [81, 79, 77, 76, 74, 73, 74], [62, 65, 69, 68],
    [86, 85, 82, 81, 77], [74, 75, 74, 70], [77, 81, 84, 81, 79, 77, 76],
    [69, 70, 73, 74], [86, 81, 77, 74, 69], [74, None, 74, 80],
    [70, 69, 70, 69, 66], [74, 77, 76, 74, 73, 74],
]


def compose(cfg: dict[str, Any], pause: float) -> tuple[np.ndarray, float]:
    order, dur = cfg["order"], cfg["durations_s"]
    grid: list[tuple[str, float, float]] = []
    t = 0.0
    for sid in order:
        grid.append((sid, t, t + float(dur[sid])))
        t += float(dur[sid]) + pause
    L, tail = t, 7.0
    m = Mix(L + tail)
    n = m.n
    tt = np.arange(n) / SR
    # Bett: Szenen lauter, Pausen leiser (weiche Rampen)
    lvl = np.full(n, 0.55)
    for _, a, b in grid:
        lvl += 0.45 * (np.clip((tt - a) / 1.5, 0, 1) - np.clip((tt - b) / 1.5, 0, 1))
    tt_mod = tt % L  # Bett periodisch → nahtloser Loop

    def quantize_freq(f: float) -> float:
        """f·L ganzzahlig → keine Phasennaht am Loopende."""
        return round(f * L) / L

    drone = np.zeros(n)
    for k, (f, a) in enumerate(((36.71, 0.5), (73.42, 0.35), (110.0, 0.18), (73.9, 0.2), (174.6, 0.06)), 1):
        drone += a * np.sin(2 * np.pi * quantize_freq(f) * tt_mod + 3 * np.sin(2 * np.pi * tt_mod / L * k))
    drone = drone * (0.75 + 0.25 * lfo("dr", n, 0.08))
    wind = np.zeros(n)
    for k, (lo, hi) in enumerate(((180, 420), (380, 900), (800, 1700))):
        wind += bandpass(_rng("wind", k).uniform(-1, 1, n), lo, hi) * lfo(("w", k), n, 0.12) ** 2 * (1.0, 0.7, 0.35)[k]
    m.dry[:, 0] += (0.22 * drone + 0.9 * wind) * lvl
    m.dry[:, 1] += (0.22 * drone + 0.9 * np.roll(wind, int(0.013 * SR))) * lvl
    # Ruhephasen: tiefe Glocke + eigene Phrase
    for i, (sid, a, b) in enumerate(grid):
        bell(m, b + 0.3, 38, 0.5, kind="fm")
        r = _rng("ph", i)
        for k, mid in enumerate(PAUSE_PHRASES[i % len(PAUSE_PHRASES)]):
            if mid is not None:
                bell(m, b + 1.2 + k * 0.78 + float(r.uniform(-0.04, 0.04)), mid, 0.3, pan=float(r.uniform(-0.5, 0.5)))
        scene_cues(m, sid, a)
    ir = make_ir(3.6, 0.03, 5200, 7)
    wet = np.stack([signal.fftconvolve(m.wet[:, c], ir[:, c])[:n] for c in range(2)], axis=1)
    out = m.dry + 0.55 * m.wet + 0.45 * wet
    # Loop: Ausklang nach L auf den Anfang überblenden
    k = int(tail * SR)
    L_n = n - k
    w = np.sin(np.linspace(0, np.pi / 2, k))[:, None]
    out[:k] = out[:k] * w + out[L_n:] * np.cos(np.linspace(0, np.pi / 2, k))[:, None]
    return out[:L_n], L


def measure(path: str | Path) -> tuple[float, float]:
    p = subprocess.run(
        ["ffmpeg", "-nostats", "-hide_banner", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = p.stderr or ""
    summary_idx = stderr.rfind("Summary:")
    s = stderr[summary_idx:] if summary_idx >= 0 else stderr
    match_i = re.search(r"I:\s+(-?[\d.]+)\s+LUFS", s)
    match_tp = re.search(r"Peak:\s+(-?[\d.inf]+)\s+dBFS", s)
    if match_i is None or match_tp is None:
        raise RuntimeError(f"ffmpeg ebur128 Summary nicht lesbar für {path}: {stderr[-400:]}")
    return float(match_i.group(1)), float(match_tp.group(1))


def master(
    x: np.ndarray,
    path: str | Path,
    target: float = -16.0,
    tp_max: float = -1.5,
) -> tuple[float, float]:
    """Pegel auf target LUFS-I, weiche Spitzenbegrenzung, True Peak ≤ tp_max (gemessen, iterativ)."""
    peak = float(np.max(np.abs(x)))
    if peak > 0:
        x = x / peak * 0.5
    ceil = 10 ** ((tp_max - 0.7) / 20)
    i: float = target
    tp: float = tp_max
    for _ in range(6):
        y = np.clip(x, -4, 4)
        a = np.abs(y)
        th = 0.6 * ceil
        y = np.where(a > th, np.sign(y) * (th + (ceil - th) * np.tanh((a - th) / (ceil - th))), y)
        wavfile.write(str(path), SR, (y * 32767).astype(np.int16))
        i, tp = measure(path)
        if abs(i - target) < 0.3 and tp <= tp_max:
            return i, tp
        x = x * 10 ** ((target - i) / 20)
        if tp > tp_max:
            ceil *= 10 ** ((tp_max - tp - 0.2) / 20)
    return i, tp


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Erzeugt die loopfähige Halloween-Atmo passend zum Szenen-/Pausenraster.")
    ap.add_argument("config", help="Pfad zur loop.json")
    ap.add_argument("-o", "--out", default="atmo.wav", help="Ausgabe-WAV-Pfad")
    ap.add_argument("--pause", type=float, help="Schwarzpause in Sekunden (überschreibt loop.json)")
    ap.add_argument("--tp", type=float, default=-3.5, help="True-Peak-Ziel des WAV; Reserve, weil AAC ~2 dB überschwingt")
    a = ap.parse_args(argv)
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    pause = float(a.pause if a.pause is not None else cfg["pause_s"])
    out, L = compose(cfg, pause)
    i, tp = master(out, a.out, tp_max=a.tp)
    print(f"atmo: {L:.1f} s, {i:.1f} LUFS-I, True Peak {tp:.1f} dBTP -> {a.out}")


if __name__ == "__main__":
    main()
