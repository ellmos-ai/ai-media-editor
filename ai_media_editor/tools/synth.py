"""Eigene Klangsynthese (numpy/scipy), keine Samples/SoundFonts.

Jede Stimme: f(freq, dur, vel, bright, **opt) -> Mono-Array (inkl. Ausklang).
`bright` 0..1 steuert Obertöne/Filter (unter Sprache klein -> Mittenband 1-4 kHz bleibt frei).
Methoden: additive Puls-/Dreieckssynthese (bandbegrenzt), Modalsynthese (Marimba/Glockenspiel),
Karplus-Strong (Pizzicato), 2-Operator-FM (Blech, Glocke), gefiltertes Rauschen (Perkussion).
"""
from __future__ import annotations

import zlib
from typing import Any

import numpy as np
from scipy import signal

SR = 48000
NYQ = SR / 2


def _t(n: int) -> np.ndarray:
    return np.arange(n) / SR


def _rng(*key: Any) -> np.random.Generator:
    """Deterministisches Rauschen je Schlüssel (crc32 statt hash(): str-Hash ist pro Prozess zufällig)."""
    norm = [round(k, 3) if isinstance(k, float) else k for k in key]
    return np.random.default_rng(zlib.crc32(repr(norm).encode()))


def env(
    n: int,
    att: float,
    dur: float,
    rel: float,
    decay: float | None = None,
    sus: float = 1.0,
    rev: bool = False,
) -> np.ndarray:
    """Lineare Attacke, optional exp. Abfall auf `sus`, Halten bis `dur`, exp. Release (Zeitkonstante `rel`)."""
    t = _t(n)
    e = np.minimum(1.0, t / att) if att > 0 else np.ones(n)
    if decay:
        e = e * (sus + (1 - sus) * np.exp(-np.maximum(t - att, 0) / decay))
    off = t > dur
    e[off] *= np.exp(-(t[off] - dur) / rel)
    if rev:  # Rückwärts-Hüllkurve: aus der Stille anschwellen, abrupt enden (musikalischer Witz "falsche Richtung")
        k = int(min(n, (dur + 0.01) * SR))
        e[:k] = np.linspace(0, 1, k) ** 2 * np.minimum(1.0, (k - np.arange(k)) / (0.004 * SR))
        e[k:] = 0
    return e


def phase(
    f: float,
    n: int,
    vib_rate: float = 0.0,
    vib_depth: float = 0.0,
    vib_delay: float = 0.2,
    scoop: float = 0.0,
    scoop_t: float = 0.04,
) -> np.ndarray:
    t = _t(n)
    inst = np.full(n, float(f))
    if vib_depth:
        inst *= 1 + vib_depth * np.clip((t - vib_delay) / 0.25, 0, 1) * np.sin(2 * np.pi * vib_rate * t)
    if scoop:
        inst *= 2 ** (scoop / 1200 * np.exp(-t / scoop_t))
    return 2 * np.pi * np.cumsum(inst) / SR


def additive(ph: np.ndarray, f: float, amps: Any, cutoff: float) -> np.ndarray:
    out = np.zeros_like(ph)
    cutoff = min(cutoff, NYQ * 0.92)
    for k, a in enumerate(amps, 1):
        if k * f >= cutoff:
            break
        if a:
            taper = 1 - (k * f / cutoff) ** 4
            out += a * taper * np.sin(k * ph)
    return out


def lowpass(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    fc = min(fc, NYQ * 0.95)
    return np.asarray(signal.sosfilt(signal.butter(order, fc, "low", fs=SR, output="sos"), x))


def highpass(x: np.ndarray, fc: float, order: int = 2) -> np.ndarray:
    return np.asarray(signal.sosfilt(signal.butter(order, fc, "high", fs=SR, output="sos"), x))


def bandpass(x: np.ndarray, lo: float, hi: float, order: int = 2) -> np.ndarray:
    hi = min(hi, NYQ * 0.95)
    return np.asarray(signal.sosfilt(signal.butter(order, [lo, hi], "band", fs=SR, output="sos"), x))


# ---------------------------------------------------------------- Variante A: Chip
def chip_pulse(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    duty: float = 0.25,
    legato: bool = False,
    rev: bool = False,
    vib: bool = True,
) -> np.ndarray:
    rel = 0.03
    n = int((dur + 6 * rel) * SR)
    ph = phase(f, n, vib_rate=5.6, vib_depth=0.005 if (vib and dur > 0.3) else 0, vib_delay=0.16)
    k = np.arange(1, 64)
    amps = 2 / (np.pi * k) * np.sin(np.pi * k * duty)
    wave = additive(ph, f, amps, 1500 + 13000 * bright ** 1.5)
    e = env(n, 0.002 if legato else 0.004, dur, rel, decay=0.14, sus=0.72, rev=rev)
    return vel * 0.42 * wave * e


def chip_tri(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    legato: bool = False,
    rev: bool = False,
) -> np.ndarray:
    rel = 0.025
    n = int((dur + 6 * rel) * SR)
    ph = phase(f, n, vib_rate=5.2, vib_depth=0.003 if dur > 0.45 else 0, vib_delay=0.25)
    k = np.arange(1, 40)
    amps = np.where(k % 2 == 1, 8 / np.pi ** 2 / k ** 2 * (-1) ** ((k - 1) // 2), 0)
    wave = additive(ph, f, amps, 1800 + 7000 * bright)
    e = env(n, 0.003, dur, rel, decay=0.35, sus=0.85, rev=rev)
    return vel * 0.6 * wave * e


def chip_hat(vel: float, bright: float = 1.0, open_: bool = False) -> np.ndarray:
    tau = 0.09 if open_ else 0.017
    n = int(6 * tau * SR)
    x = highpass(_rng("hat", open_).uniform(-1, 1, n), 7000, 4)
    return vel * 0.32 * x * np.exp(-_t(n) / tau)


def chip_snare(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(0.35 * SR)
    t = _t(n)
    noise = bandpass(_rng("sn").uniform(-1, 1, n), 1200, 7000) * np.exp(-t / 0.07)
    tone = np.sin(2 * np.pi * np.cumsum(160 + 60 * np.exp(-t / 0.02)) / SR) * np.exp(-t / 0.05)
    return vel * 0.5 * (0.75 * noise + 0.45 * tone)


def chip_kick(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(0.4 * SR)
    t = _t(n)
    f = 45 + 115 * np.exp(-t / 0.03)
    return vel * 0.8 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.11)


# ---------------------------------------------------------------- Variante B: gemütlich
def marimba(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    legato: bool = False,
    rev: bool = False,
) -> np.ndarray:
    tau1 = float(np.clip(1.15 - f / 850, 0.16, 0.95))
    n = int(min(4.5 * tau1 + 0.05, 3.5) * SR)
    t = _t(n)
    y = np.zeros(n)
    for r, a, tau in ((1.0, 1.0, tau1), (3.93, 0.18 + 0.3 * bright, tau1 / 3.4), (9.2, 0.03 + 0.1 * bright, tau1 / 8)):
        if f * r < NYQ * 0.9:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau)
    y *= np.minimum(1.0, t / 0.0015)
    m = int(0.004 * SR)
    click = np.zeros(n)
    click[:m] = lowpass(_rng("mar", f).uniform(-1, 1, m), 1500 + 3500 * bright) * np.hanning(m)
    out = y + (0.1 + 0.2 * bright) * click
    if legato:  # Wirbel/Triller: Anschläge kürzer klingen lassen
        out *= np.exp(-np.maximum(t - dur, 0) / 0.08)
    return vel * 0.5 * out


def glock(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    legato: bool = False,
    rev: bool = False,
) -> np.ndarray:
    scale = float(np.clip(1100 / f, 0.35, 1.0))
    n = int(min(3.2 * scale + 0.1, 3.5) * SR)
    t = _t(n)
    y = np.zeros(n)
    for r, a, tau in ((1, 1, 1.5 * scale), (2.76, 0.3, 0.55 * scale), (5.40, 0.13, 0.25 * scale), (8.93, 0.05, 0.12 * scale)):
        if f * r < NYQ * 0.9:
            y += a * np.sin(2 * np.pi * f * r * t) * np.exp(-t / tau)
    y *= np.minimum(1.0, t / 0.001)
    if legato:
        y *= np.exp(-np.maximum(t - dur, 0) / 0.06)
    return vel * 0.33 * y


def pizz(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    t60: float = 0.65,
    legato: bool = False,
    rev: bool = False,
) -> np.ndarray:
    """Karplus-Strong blockweise (Periodenschritt vektorisiert)."""
    N = max(2, int(round(SR / f)))
    total = int((min(dur, 1.0) + 0.45) * SR)
    g = 10 ** (-3 / (t60 * f))
    alpha = 0.25 + 0.5 * bright
    buf = np.asarray(signal.lfilter([alpha], [1, -(1 - alpha)], _rng("pz", f).uniform(-1, 1, N)), dtype=float)
    buf -= buf.mean()
    blocks = []
    for _ in range(total // N + 1):
        blocks.append(buf)
        buf = g * 0.5 * (buf + np.concatenate(([buf[-1]], buf[:-1])))
    y = np.concatenate(blocks)[:total]
    t = _t(total)
    y *= np.exp(-np.maximum(t - dur - 0.12, 0) / 0.07)
    y = lowpass(y, 900 + 3500 * bright)
    return vel * 0.9 * y


def flute(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    legato: bool = False,
    rev: bool = False,
    ocarina: bool = False,
) -> np.ndarray:
    rel = 0.07
    n = int((dur + 6 * rel) * SR)
    ph = phase(f, n, vib_rate=5.0, vib_depth=0.0045 if dur > 0.35 else 0, vib_delay=0.18)
    harm = (1, 0.04, 0.11, 0.0, 0.02) if ocarina else (1, 0.22, 0.07, 0.025, 0.01)
    tone = additive(ph, f, harm, 2500 + 9000 * bright)
    att = 0.012 if legato else (0.06 if ocarina else 0.045)
    e = env(n, att, dur, rel, decay=0.35, sus=0.86, rev=rev)
    breath = bandpass(_rng("br", f).standard_normal(n), max(200, f * 1.2), min(f * 4, 12000)) * (0.012 if ocarina else 0.035)
    out = tone * e + breath * e
    if not legato and not ocarina and bright > 0.5:
        m = int(0.03 * SR)
        out[:m] += 0.09 * bandpass(_rng("ch", f).standard_normal(m), 2000, 6000) * np.hanning(m)
    return vel * 0.5 * out


def shaker(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(0.12 * SR)
    t = _t(n)
    x = bandpass(_rng("sh").uniform(-1, 1, n), 5000, 11000)
    e = np.minimum(1, t / 0.008) * np.exp(-np.maximum(t - 0.008, 0) / 0.035)
    return vel * 0.35 * x * e


def woodblock(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(0.15 * SR)
    t = _t(n)
    y = (np.sin(2 * np.pi * 980 * t) + 0.5 * np.sin(2 * np.pi * 1530 * t)) * np.exp(-t / 0.028)
    return vel * 0.35 * y * np.minimum(1, t / 0.0005)


def framedrum(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(0.6 * SR)
    t = _t(n)
    f = 78 + 25 * np.exp(-t / 0.03)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.17)
    y += 0.15 * lowpass(_rng("fd").uniform(-1, 1, n), 700) * np.exp(-t / 0.03)
    return vel * 0.6 * y


# ---------------------------------------------------------------- Variante C: Marsch
def fm_brass(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    imax: float = 3.0,
    att: float = 0.045,
    rel: float = 0.09,
    lp: float | None = None,
    legato: bool = False,
    rev: bool = False,
) -> np.ndarray:
    n = int((dur + 6 * rel) * SR)
    ph = phase(
        f, n, vib_rate=5.2, vib_depth=0.003 if dur > 0.4 else 0, vib_delay=0.3,
        scoop=0 if legato else -30, scoop_t=0.035,
    )
    e = env(n, 0.012 if legato else att, dur, rel, decay=0.3, sus=0.8, rev=rev)
    index = (0.3 + imax * (0.35 + 0.65 * bright)) * e ** 1.3
    y = 0.6 * np.sin(ph + index * np.sin(ph)) + 0.4 * np.sin(ph * 1.0024 + index * np.sin(ph * 1.0024))
    y = lowpass(y, lp if lp else 1400 + 9000 * bright)
    return vel * 0.42 * e * y


def fm_bell(
    f: float,
    dur: float,
    vel: float,
    bright: float,
    legato: bool = False,
    rev: bool = False,
) -> np.ndarray:
    scale = float(np.clip(900 / f, 0.3, 1.0))
    n = int(min(2.6 * scale + 0.1, 3.0) * SR)
    t = _t(n)
    index = (2.4 * np.exp(-t / 0.18) + 0.25) * min(1.0, 1400 / f)  # hohe Lagen: kleiner Index, keine Spiegelfrequenzen
    y = np.sin(2 * np.pi * f * t + index * np.sin(2 * np.pi * 3.5 * f * t)) * np.exp(-t / (0.9 * scale))
    y *= np.minimum(1.0, t / 0.001)
    if legato:
        y *= np.exp(-np.maximum(t - dur, 0) / 0.06)
    return vel * 0.3 * y


def snare(vel: float, bright: float = 1.0, brush: bool = False) -> np.ndarray:
    n = int(0.4 * SR)
    t = _t(n)
    if brush:
        x = lowpass(_rng("br").uniform(-1, 1, n), 4200) * np.minimum(1, t / 0.012) * np.exp(-t / 0.09)
        return vel * 0.22 * x
    noise = bandpass(_rng("sn2").uniform(-1, 1, n), 1500, 8000) * np.exp(-t / 0.1)
    tone = (np.sin(2 * np.pi * 185 * t) + 0.5 * np.sin(2 * np.pi * 330 * t)) * np.exp(-t / 0.05)
    return vel * 0.42 * (0.8 * noise + 0.35 * tone)


def bdrum(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(0.8 * SR)
    t = _t(n)
    f = 52 + 38 * np.exp(-t / 0.045)
    y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.26)
    y += 0.1 * lowpass(_rng("bd").uniform(-1, 1, n), 1200) * np.exp(-t / 0.012)
    return vel * 0.75 * y


def cymbal(vel: float, bright: float = 1.0) -> np.ndarray:
    n = int(2.2 * SR)
    t = _t(n)
    x = highpass(_rng("cy").uniform(-1, 1, n), 4200, 2)
    return vel * 0.16 * x * np.exp(-t / 0.75) * np.minimum(1, t / 0.002)


# ---------------------------------------------------------------- Raum
def make_ir(t60: float, predelay: float, damp_hz: float, seed: int) -> np.ndarray:
    n = int(t60 * SR)
    t = _t(n)
    rng = np.random.default_rng(seed)
    decay = 10 ** (-3 * t / t60)
    chans = []
    for _ in range(2):
        x = rng.standard_normal(n) * decay
        x = lowpass(x, damp_hz, 1)
        chans.append(np.concatenate([np.zeros(int(predelay * SR)), x]))
    ir = np.stack(chans, axis=1)
    return ir / np.sqrt((ir ** 2).sum() / 2)
