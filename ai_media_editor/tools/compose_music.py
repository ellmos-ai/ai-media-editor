#!/usr/bin/env python3
"""
compose_music.py — storyline-driven, video-synced score generator.

Method ("Storyline -> Score")
-----------------------------
Reconstructed from a one-off video-synced score (179.5 s, 5 music sections
mapped from 7 story acts). The method, as it was actually implemented:

1. Story acts are grouped into music sections with exact time windows
   (several acts may share one section; boundaries are audible but fluid).
2. Each section carries an emotion + intensity. Intensity drives tempo feel
   (BPM), layer count (pads -> arp -> bass -> drums -> lead -> epic doubling)
   and the volume ramp. Emotion drives the chord progression and waveform
   character.
3. Special events sit on the timeline:
   - "damp": a Gaussian volume dip (depth, width sigma in seconds) that ducks
     the music on a dramatic beat (reference: depth 0.5 at t=84 s).
   - "climax": a time window that forces full layering, peak volume and
     octave doubling of the pads.
   - "outro": from its start, drums/bass/lead drop out, bells fade to silence.
4. Glue: raised-cosine smoothing at section boundaries, global fade in/out,
   a delay-network reverb, peak normalization to a background-friendly level.

Synthesis is pure waveform synthesis with numpy (sine/triangle/square/saw/
noise oscillators, ADSR envelopes, harmonic layering). No samples, no MIDI
hardware, no cloud service. Output: stereo WAV + MP3 (via ffmpeg) + an
arrangement/note log (JSON) + a Standard MIDI File (.mid, type 1 with tempo
map and GM program hints per style).

The genre ceiling (chiptune/ambient/electronic only — no pop/rock/classical/
orchestral film music) is the *sound backend*, not the composition. The
arrangement is backend-neutral: render the .mid through a SoundFont engine
(e.g. FluidSynth + a GM SF2) or a DAW for realistic instruments.

TODO(humanize): optional per-note velocity/timing jitter (option "humanize")
so sample-based rendering does not sound mechanical. Not implemented yet.

Dependencies: numpy (required) + ffmpeg on PATH (optional, for MP3 only).

Usage:
    python compose_music.py storyline.json [-o out/score] [--seed N] [--no-mp3]
    python compose_music.py --init            # print a storyline template
    python compose_music.py --selftest        # render 3 s and verify output
    # outputs: <out>.wav  <out>.mp3  <out>.notes.json  <out>.mid
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44100

# ---------------------------------------------------------------------------
# Storyline defaults and emotion model
# ---------------------------------------------------------------------------

# Emotions map to chord progressions in scale degrees (1-based) and a default
# intensity. The progressions below are exactly the ones the reference score
# used per section (C minor): calm = i-VI-III-VII, tense = iv-i-V-i,
# alive = VI-VII-i-III, driving = i-VII-VI-V, epic = iv-V-VI-i.
EMOTIONS = {
    "calm": {"intensity": 0.20, "progression": [1, 6, 3, 7]},
    "tense": {"intensity": 0.35, "progression": [4, 1, 5, 1]},
    "alive": {"intensity": 0.55, "progression": [6, 7, 1, 3]},
    "driving": {"intensity": 0.70, "progression": [1, 7, 6, 5]},
    "epic": {"intensity": 0.90, "progression": [4, 5, 6, 1]},
    "outro": {"intensity": 0.15, "progression": [1, 3, 6, 1]},
}

STYLES = ("chiptune", "ambient", "electronic")

# Intensity thresholds at which layers join (reference-score behaviour).
THRESH_ARP = 0.25
THRESH_BASS = 0.40
THRESH_LEAD = 0.45
THRESH_DRUMS = 0.50
THRESH_DRIVE = 0.65  # per-beat bass, double hi-hats
THRESH_EPIC = 0.85   # pad octave doubling
THRESH_SPARSE_BELLS = 0.30  # below this: lonely bells instead of an arp

MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]  # aeolian
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]  # ionian

NOTE_OFFSETS = {
    "C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5,
    "F#": 6, "GB": 6, "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10,
    "BB": 10, "B": 11,
}

ARP_PATTERNS = [
    [0, 4, 7, 12],   # up
    [12, 7, 4, 0],   # down
    [0, 7, 4, 12],   # broken
    [0, 12, 4, 7],   # pingpong
]

# Constant stereo placement per layer (linear pan, -1 left .. +1 right).
PAN = {"pad": -0.2, "bass": 0.0, "arp": 0.25, "lead": 0.1,
       "kick": 0.0, "snare": -0.05, "hihat": 0.15, "bell": 0.3}


def midi_to_hz(midi_note: float) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def key_to_midi(key: str, octave: int = 3) -> int:
    name = key.strip().upper()
    if name not in NOTE_OFFSETS:
        raise ValueError(f"Unbekannte Tonart: {key!r} (erlaubt: {sorted(NOTE_OFFSETS)})")
    return 12 * (octave + 1) + NOTE_OFFSETS[name]


def degree_chord(tonic: int, scale: list[int], degree: int, mode: str) -> list[int]:
    """Triad on a 1-based scale degree, built from scale tones."""
    idx = degree - 1
    chord = [tonic + scale[(idx + 2 * k) % 7] + 12 * ((idx + 2 * k) // 7)
             for k in range(3)]
    if mode == "minor" and degree == 5:
        chord[1] += 1  # harmonic-minor dominant (V major), as in the reference
    return chord


# ---------------------------------------------------------------------------
# Oscillators and envelopes (reference implementations)
# ---------------------------------------------------------------------------

def sine_wave(freq, duration, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * freq * t)


def triangle_wave(freq, duration, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return 2 * np.abs(2 * (t * freq - np.floor(t * freq + 0.5))) - 1


def square_wave(freq, duration, sr=SAMPLE_RATE, duty=0.5):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sign(np.sin(2 * np.pi * freq * t) + (1 - 2 * duty))


def sawtooth_wave(freq, duration, sr=SAMPLE_RATE):
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return 2 * (t * freq - np.floor(t * freq + 0.5))


def noise(duration, sr, rng):
    return rng.uniform(-1, 1, int(sr * duration))


def adsr_envelope(duration, attack=0.01, decay=0.05, sustain_level=0.7,
                  release=0.1, sr=SAMPLE_RATE):
    n = int(sr * duration)
    env = np.zeros(n)
    a_samples = int(sr * min(attack, duration * 0.25))
    d_samples = int(sr * min(decay, duration * 0.25))
    r_samples = int(sr * min(release, duration * 0.4))
    s_samples = max(0, n - a_samples - d_samples - r_samples)
    if a_samples > 0:
        env[:a_samples] = np.linspace(0, 1, a_samples)
    if d_samples > 0:
        env[a_samples:a_samples + d_samples] = np.linspace(1, sustain_level, d_samples)
    if s_samples > 0:
        env[a_samples + d_samples:a_samples + d_samples + s_samples] = sustain_level
    if r_samples > 0:
        env[-r_samples:] = np.linspace(sustain_level, 0, r_samples)
    return env


def fade_in(n_samples):
    return np.linspace(0, 1, n_samples) ** 2


def fade_out(n_samples):
    return np.linspace(1, 0, n_samples) ** 2


# ---------------------------------------------------------------------------
# Instruments (reference designs, style variants added)
# ---------------------------------------------------------------------------

def pad_sound(freq, duration, brightness=0.5, sr=SAMPLE_RATE, style="chiptune"):
    """Warm pad: sine + filtered harmonics + triangle sub."""
    sig = sine_wave(freq, duration, sr) * 0.6
    sig += sine_wave(freq * 2, duration, sr) * 0.2 * brightness
    sig += sine_wave(freq * 3, duration, sr) * 0.1 * brightness
    sig += triangle_wave(freq * 0.5, duration, sr) * 0.15  # sub
    attack = 1.2 if style == "ambient" else 0.8
    env = adsr_envelope(duration, attack=attack, decay=0.3, sustain_level=0.6,
                        release=1.5, sr=sr)
    return sig[:len(env)] * env


def lead_sound(freq, duration, sr=SAMPLE_RATE, style="chiptune"):
    if style == "ambient":
        sig = triangle_wave(freq, duration, sr) * 0.4
        sig += sine_wave(freq, duration, sr) * 0.3
        env = adsr_envelope(duration, attack=0.05, decay=0.15,
                            sustain_level=0.5, release=0.4, sr=sr)
    elif style == "electronic":
        sig = sawtooth_wave(freq, duration, sr) * 0.3
        sig += sawtooth_wave(freq * 1.004, duration, sr) * 0.15  # detune
        sig += square_wave(freq * 0.5, duration, sr, duty=0.5) * 0.15
        env = adsr_envelope(duration, attack=0.005, decay=0.08,
                            sustain_level=0.55, release=0.15, sr=sr)
    else:  # chiptune: square + light detune + triangle (reference lead)
        sig = square_wave(freq, duration, sr, duty=0.25) * 0.35
        sig += square_wave(freq * 1.003, duration, sr, duty=0.25) * 0.15
        sig += triangle_wave(freq, duration, sr) * 0.2
        env = adsr_envelope(duration, attack=0.005, decay=0.08,
                            sustain_level=0.5, release=0.15, sr=sr)
    return sig[:len(env)] * env


def bass_sound(freq, duration, sr=SAMPLE_RATE):
    """Deep bass from triangle + sine."""
    sig = triangle_wave(freq, duration, sr) * 0.5
    sig += sine_wave(freq, duration, sr) * 0.5
    env = adsr_envelope(duration, attack=0.005, decay=0.15, sustain_level=0.6,
                        release=0.1, sr=sr)
    return sig[:len(env)] * env


def arp_note(freq, duration, sr=SAMPLE_RATE, style="chiptune"):
    if style == "ambient":
        sig = sine_wave(freq, duration, sr) * 0.3
        sig += sine_wave(freq * 2, duration, sr) * 0.1
    elif style == "electronic":
        sig = sawtooth_wave(freq, duration, sr) * 0.25
        sig += square_wave(freq, duration, sr, duty=0.25) * 0.15
    else:  # chiptune: fast arpeggio note (reference)
        sig = square_wave(freq, duration, sr, duty=0.125) * 0.3
        sig += sine_wave(freq * 2, duration, sr) * 0.15
    env = adsr_envelope(duration, attack=0.002, decay=0.05, sustain_level=0.3,
                        release=0.05, sr=sr)
    return sig[:len(env)] * env


def bell_sound(freq, duration, sr=SAMPLE_RATE):
    """Sine bell with 2nd harmonic, fast attack, long release."""
    sig = sine_wave(freq, duration, sr)
    sig += sine_wave(freq * 2.0, duration, sr) * 0.3
    env = adsr_envelope(duration, attack=0.001, decay=0.5, sustain_level=0.1,
                        release=min(1.5, duration * 0.6), sr=sr)
    return sig[:len(env)] * env


def kick_drum(duration=0.15, sr=SAMPLE_RATE):
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    freq_sweep = 150 * np.exp(-t * 30) + 40
    phase = np.cumsum(2 * np.pi * freq_sweep / sr)
    sig = np.sin(phase) * np.exp(-t * 15)
    return sig * 0.5


def hihat(duration, sr, rng):
    n = int(sr * duration)
    sig = noise(duration, sr, rng)
    env = np.exp(-np.linspace(0, 20, n))
    return sig * env * 0.15


def snare(duration, sr, rng):
    n = int(sr * duration)
    t = np.linspace(0, duration, n, endpoint=False)
    tone = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 30)
    nz = noise(duration, sr, rng) * np.exp(-t * 15)
    return (tone * 0.4 + nz * 0.3) * 0.4


# ---------------------------------------------------------------------------
# Mix helpers
# ---------------------------------------------------------------------------

def place(bufs, signal, start_s, sr, pan=0.0):
    """Add a mono signal into the stereo buffer pair at start_s (seconds)."""
    start = int(start_s * sr)
    if start < 0 or start >= len(bufs[0]):
        return
    end = min(start + len(signal), len(bufs[0]))
    length = end - start
    if length <= 0:
        return
    # constant-power pan
    theta = (pan + 1.0) * np.pi / 4.0
    bufs[0][start:end] += signal[:length] * np.cos(theta)
    bufs[1][start:end] += signal[:length] * np.sin(theta)


def delay_reverb(signal, delay_ms=100, decay=0.25, sr=SAMPLE_RATE):
    """Feedback-delay reverb. Equivalent to the reference IIR loop
    out[i] += out[i-delay]*decay, computed as its FIR impulse response."""
    delay = int(sr * delay_ms / 1000)
    if delay <= 0 or decay <= 0:
        return signal
    # The kernel is sparse: taps decay^k at offsets k*delay. Summing the few
    # shifted copies directly is O(taps * N) — much faster than np.convolve
    # with a mostly-zero kernel of length n*delay.
    out = signal.copy()
    gain = 1.0
    for k in range(1, 64):
        gain *= decay
        if gain < 1e-3:
            break
        out[delay * k:] += signal[:len(signal) - delay * k] * gain
    return out


def smooth_boundaries(buf, boundaries, fade_dur, sr):
    """Raised-cosine smoothing at section boundaries (reference crossfade)."""
    fade_samples = int(fade_dur * sr)
    for boundary in boundaries:
        center = int(boundary * sr)
        half = fade_samples // 2
        start = max(0, center - half)
        end = min(len(buf), center + half)
        n = end - start
        if n > 0:
            curve = 0.5 * (1 + np.cos(np.linspace(-np.pi, np.pi, n)))
            buf[start:end] *= 0.7 + 0.3 * curve


def write_wav(path, left, right, sr):
    """Write stereo 16-bit PCM WAV. Caller is responsible for level/peak."""
    inter = np.empty(len(left) * 2, dtype=np.float64)
    inter[0::2] = left
    inter[1::2] = right
    data = np.clip(inter * 32767, -32767, 32767).astype(np.int16)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def gen_melody(rng, scale, tonic, n=16):
    """Seeded random walk over scale tones. The reference score used
    hand-written melodies; a storyline may supply an explicit "melody"
    (MIDI list) per section — this is the deterministic fallback."""
    mel, pos = [], 0
    for _ in range(n):
        pos = int(np.clip(pos + rng.integers(-2, 3), 0, 9))
        mel.append(tonic + 12 + scale[pos % 7] + 12 * (pos // 7))
    return mel


# ---------------------------------------------------------------------------
# MIDI export (Standard MIDI File written directly — no dependencies)
# ---------------------------------------------------------------------------

# General MIDI program map per style preset (0-based program numbers).
# Rough genre hints for SoundFont/DAW rendering; edit the .mid to taste.
# GM reference (1-based): 15 Tubular Bells, 39/40 Synth Bass 1/2,
# 81/82 Lead 1 (square)/Lead 2 (sawtooth), 89 Pad 2 (warm), 92 Pad 4 (choir).
GM_PROGRAMS = {
    "chiptune": {"pad": 88, "bass": 38, "arp": 80, "lead": 80, "bell": 14},
    "ambient": {"pad": 91, "bass": 38, "arp": 88, "lead": 88, "bell": 14},
    "electronic": {"pad": 88, "bass": 39, "arp": 81, "lead": 81, "bell": 14},
}

LAYER_CHANNELS = {"pad": 0, "bass": 1, "arp": 2, "lead": 3, "bell": 4}
DRUM_CHANNEL = 9  # GM percussion channel (10, 1-based)
DRUM_NOTES = {"kick": 36, "snare": 38, "hihat": 42}
TICKS_PER_QUARTER = 480


def _varlen(value: int) -> bytes:
    """SMF variable-length quantity."""
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append(0x80 | (value & 0x7F))
        value >>= 7
    return bytes(reversed(out))


def _tempo_segments(sections, default_bpm):
    segs = sorted((s["start"], s["bpm"]) for s in sections)
    if not segs or segs[0][0] > 0:
        segs.insert(0, (0.0, default_bpm))
    return segs


def _sec_to_tick(t, segs):
    tick = 0.0
    for i, (start, bpm) in enumerate(segs):
        end = segs[i + 1][0] if i + 1 < len(segs) else float("inf")
        tick += (min(t, end) - start) * bpm / 60.0 * TICKS_PER_QUARTER
        if t < end:
            break
    return int(round(tick))


def _velocity(vel):
    """Map internal amplitude (~0.02..0.6) to a MIDI velocity (1..127)."""
    return max(1, min(127, int(round(vel * 320))))


def write_midi(path, notes, sections, style, default_bpm):
    """Write the arrangement as a Standard MIDI File (type 1).

    Track 0: tempo map (one tempo event per section start, so the .mid lines
    up with the rendered audio both in seconds and on the musical grid).
    Track 1: program change per layer channel + note on/off from the note log;
    drum layers go to the GM percussion channel.
    """
    segs = _tempo_segments(sections, default_bpm)
    programs = GM_PROGRAMS.get(style, GM_PROGRAMS["chiptune"])

    tempo_track = bytearray()
    last = 0
    for start, bpm in segs:
        tick = _sec_to_tick(start, segs)
        mpq = int(round(60_000_000 / bpm))
        tempo_track += _varlen(tick - last)
        tempo_track += b"\xff\x51\x03" + mpq.to_bytes(3, "big")
        last = tick
    tempo_track += _varlen(0) + b"\xff\x2f\x00"

    events = []  # (tick, order, payload); order sorts offs before ons
    for layer, channel in LAYER_CHANNELS.items():
        events.append((0, -1, bytes([0xC0 | channel, programs[layer]])))
    note_count = 0
    for n in notes:
        layer = n["layer"]
        if layer in DRUM_NOTES:
            channel, pitch = DRUM_CHANNEL, DRUM_NOTES[layer]
        elif layer in LAYER_CHANNELS and n["midi"] is not None:
            channel, pitch = LAYER_CHANNELS[layer], int(n["midi"])
        else:
            continue
        on = _sec_to_tick(n["t"], segs)
        off = _sec_to_tick(n["t"] + n.get("dur", 0.25), segs)
        if off <= on:
            off = on + 1
        v = _velocity(n.get("vel", 0.3))
        events.append((on, 1, bytes([0x90 | channel, pitch & 0x7F, v])))
        events.append((off, 0, bytes([0x80 | channel, pitch & 0x7F, 0])))
        note_count += 1

    events.sort(key=lambda e: (e[0], e[1]))
    track = bytearray()
    last = 0
    for tick, _order, payload in events:
        track += _varlen(tick - last)
        track += payload
        last = tick
    track += _varlen(0) + b"\xff\x2f\x00"

    with open(path, "wb") as f:
        f.write(b"MThd" + (6).to_bytes(4, "big"))
        f.write((1).to_bytes(2, "big"))  # format 1
        f.write((2).to_bytes(2, "big"))  # 2 tracks
        f.write(TICKS_PER_QUARTER.to_bytes(2, "big"))
        f.write(b"MTrk" + len(tempo_track).to_bytes(4, "big") + tempo_track)
        f.write(b"MTrk" + len(track).to_bytes(4, "big") + track)
    return {"note_events": note_count, "tempo_events": len(segs)}


# ---------------------------------------------------------------------------
# Storyline validation
# ---------------------------------------------------------------------------

def validate_storyline(story: dict) -> dict:
    if not isinstance(story, dict):
        raise ValueError("Storyline muss ein JSON-Objekt sein")
    duration = float(story.get("duration", 0))
    if duration <= 0:
        raise ValueError("Storyline braucht 'duration' > 0 (Sekunden)")
    style = story.get("style", "chiptune")
    if style not in STYLES:
        raise ValueError(f"Unbekannter Stil: {style!r} (erlaubt: {STYLES})")
    mode = story.get("mode", "minor")
    if mode not in ("minor", "major"):
        raise ValueError("'mode' muss 'minor' oder 'major' sein")
    sections = story.get("sections")
    if not sections:
        raise ValueError("Storyline braucht mindestens eine Sektion")
    norm_sections = []
    prev_end = 0.0
    for i, sec in enumerate(sections):
        start = float(sec["start"])
        end = float(sec["end"])
        emotion = sec.get("emotion", "calm")
        if emotion not in EMOTIONS:
            raise ValueError(
                f"Sektion {i}: unbekannte Emotion {emotion!r} "
                f"(erlaubt: {sorted(EMOTIONS)})")
        if end <= start:
            raise ValueError(f"Sektion {i}: end ({end}) <= start ({start})")
        if start < prev_end - 1e-9:
            raise ValueError(f"Sektion {i}: überlappt die vorherige Sektion")
        if end > duration + 1e-9:
            raise ValueError(f"Sektion {i}: end ({end}) liegt hinter duration")
        intensity = float(sec.get("intensity", EMOTIONS[emotion]["intensity"]))
        norm_sections.append({
            "start": start,
            "end": end,
            "emotion": emotion,
            "intensity": min(1.0, max(0.0, intensity)),
            "bpm": float(sec.get("bpm", story.get("bpm", 100))),
            "melody": sec.get("melody"),
            "comment": sec.get("comment", ""),
        })
        prev_end = end
    events = story.get("events", [])
    damps, climaxes, outro_start = [], [], None
    for ev in events:
        etype = ev.get("type")
        if etype == "damp":
            damps.append({
                "time": float(ev["time"]),
                "depth": float(ev.get("depth", 0.5)),
                "width": float(ev.get("width", 1.0)),
            })
        elif etype == "climax":
            climaxes.append((float(ev["start"]), float(ev["end"])))
        elif etype == "outro":
            outro_start = float(ev["start"])
        else:
            raise ValueError(f"Unbekannter Event-Typ: {etype!r}")
    reverb = story.get("reverb", {})
    return {
        "title": story.get("title", "score"),
        "duration": duration,
        "sr": int(story.get("sr", SAMPLE_RATE)),
        "key": story.get("key", "C"),
        "mode": mode,
        "style": style,
        "seed": int(story.get("seed", 1)),
        "bpm": float(story.get("bpm", 100)),
        "fade_in": float(story.get("fade_in", 3.0)),
        "fade_out": float(story.get("fade_out", 5.0)),
        "crossfade": float(story.get("crossfade", 2.5)),
        "peak": float(story.get("peak", 0.85)),
        "drive": float(story.get("drive", 2.0)),
        "reverb_delay_ms": float(reverb.get("delay_ms", 100)),
        "reverb_decay": float(reverb.get("decay", 0.25)),
        "sections": norm_sections,
        "damps": damps,
        "climaxes": climaxes,
        "outro_start": outro_start,
    }


# ---------------------------------------------------------------------------
# Section renderer
# ---------------------------------------------------------------------------

class _Context:
    def __init__(self, cfg):
        self.cfg = cfg
        self.sr = cfg["sr"]
        self.style = cfg["style"]
        self.tonic = key_to_midi(cfg["key"])
        self.scale = MINOR_SCALE if cfg["mode"] == "minor" else MAJOR_SCALE

    def damp_factor(self, t):
        """Gaussian volume dips (reference: 1 - depth*exp(-((t-T)^2)/(2*sigma^2)))."""
        factor = 1.0
        for d in self.cfg["damps"]:
            factor *= 1.0 - d["depth"] * np.exp(
                -((t - d["time"]) ** 2) / (2.0 * d["width"] ** 2))
        return factor

    def in_climax(self, t):
        return any(start <= t < end for start, end in self.cfg["climaxes"])

    def in_outro(self, t):
        start = self.cfg["outro_start"]
        return start is not None and t >= start

    def outro_factor(self, t):
        """Fade to 20 % across the outro (reference: vol*(1 - progress*0.8))."""
        start = self.cfg["outro_start"]
        if start is None or t < start:
            return 1.0
        span = max(self.cfg["duration"] - start, 1e-9)
        return max(0.2, 1.0 - 0.8 * (t - start) / span)


def render_section(ctx, sec, bufs, notes, rng):
    sr = ctx.sr
    start, end = sec["start"], sec["end"]
    sec_dur = end - start
    beat = 60.0 / sec["bpm"]
    chord_dur = beat * 4
    intensity = sec["intensity"]
    progression = EMOTIONS[sec["emotion"]]["progression"]
    chords = [degree_chord(ctx.tonic, ctx.scale, d, ctx.cfg["mode"])
              for d in progression]
    melody = sec["melody"] or gen_melody(rng, ctx.scale, ctx.tonic)
    melody_idx = 0

    t = start
    chord_idx = 0
    while t < end - 0.3:
        progress = (t - start) / max(sec_dur, 1e-9)
        in_climax = ctx.in_climax(t)
        in_outro = ctx.in_outro(t)
        ie = max(intensity, 0.9) if in_climax else intensity
        vol = 0.05 + 0.40 * ie + progress * 0.15 * max(ie, 0.2)
        vol *= ctx.damp_factor(t)
        if in_outro:
            vol *= ctx.outro_factor(t)

        chord = chords[chord_idx % len(chords)]
        dur = min(chord_dur, end - t)

        # Pads (always present; octave doubling at epic intensity)
        brightness = 0.2 + 0.6 * ie
        for i, note in enumerate(chord):
            pad = pad_sound(midi_to_hz(note), dur, brightness, sr, ctx.style)
            v = vol * 0.3
            place(bufs, pad * v, t, sr, pan=-0.3 + 0.3 * i)
            notes.append({"t": round(t, 3), "layer": "pad", "midi": note,
                          "dur": round(dur, 3), "vel": round(v, 4)})
            if ie >= THRESH_EPIC or in_climax:
                pad2 = pad_sound(midi_to_hz(note + 12), dur,
                                 min(1.0, brightness + 0.1), sr, ctx.style)
                v2 = vol * 0.15
                place(bufs, pad2 * v2, t, sr, pan=-0.3 + 0.3 * i)
        # Quiet sections: deep sub-pad a octave below (reference section 1)
        if ie < 0.3:
            sub = pad_sound(midi_to_hz(chord[0] - 12), dur, 0.2, sr, ctx.style)
            place(bufs, sub * vol * 0.5, t, sr, pan=0.0)

        # Bass (dropped in the outro)
        if ie >= THRESH_BASS and not in_outro:
            bass_freq = midi_to_hz(chord[0] - 12)
            if ie >= THRESH_DRIVE:
                for b in range(int(dur / beat)):
                    bt = t + b * beat
                    if bt >= end:
                        break
                    bs = bass_sound(bass_freq, beat * 0.8, sr)
                    v = vol * 0.45
                    place(bufs, bs * v, bt, sr, pan=PAN["bass"])
                    notes.append({"t": round(bt, 3), "layer": "bass",
                                  "midi": chord[0] - 12,
                                  "dur": round(beat * 0.8, 3), "vel": round(v, 4)})
            else:
                bs = bass_sound(bass_freq, dur, sr)
                v = vol * 0.4
                place(bufs, bs * v, t, sr, pan=PAN["bass"])
                notes.append({"t": round(t, 3), "layer": "bass",
                              "midi": chord[0] - 12, "dur": round(dur, 3),
                              "vel": round(v, 4)})

        # Drums (dropped in the outro; ambient keeps silent unless intense)
        drums_on = (ie >= THRESH_DRUMS and not in_outro
                    and (ctx.style != "ambient" or ie >= 0.75))
        if drums_on:
            for b in range(int(dur / beat)):
                bt = t + b * beat
                if bt >= end:
                    break
                kv = vol * (0.6 if in_climax else (0.55 if ie >= THRESH_DRIVE else 0.5))
                place(bufs, kick_drum(0.12, sr) * kv, bt, sr, pan=PAN["kick"])
                notes.append({"t": round(bt, 3), "layer": "kick", "midi": None,
                              "dur": 0.12, "vel": round(kv, 4)})
                hv = vol * 0.5
                place(bufs, hihat(0.04, sr, rng) * hv, bt + beat * 0.5, sr,
                      pan=PAN["hihat"])
                if ie >= THRESH_DRIVE:
                    place(bufs, hihat(0.03, sr, rng) * vol * 0.5,
                          bt + beat * 0.25, sr, pan=PAN["hihat"])
                    place(bufs, hihat(0.03, sr, rng) * vol * 0.4,
                          bt + beat * 0.75, sr, pan=PAN["hihat"])
                if b % 2 == 1:
                    sv = vol * (0.5 if in_climax else 0.45)
                    place(bufs, snare(0.1, sr, rng) * sv, bt, sr, pan=PAN["snare"])
                    notes.append({"t": round(bt, 3), "layer": "snare",
                                  "midi": None, "dur": 0.1, "vel": round(sv, 4)})
        elif 0.3 <= ie < THRESH_DRUMS and not in_outro:
            # Tension pulse: quiet snare every 2 beats (reference section 2)
            for b in range(4):
                bt = t + b * beat
                if bt < end and b % 2 == 1:
                    sv = vol * 0.3
                    place(bufs, snare(0.08, sr, rng) * sv, bt, sr, pan=PAN["snare"])
                    notes.append({"t": round(bt, 3), "layer": "snare",
                                  "midi": None, "dur": 0.08, "vel": round(sv, 4)})

        # Arpeggio
        if ie >= THRESH_ARP:
            pattern = ARP_PATTERNS[int(rng.integers(0, len(ARP_PATTERNS)))]
            arp_dur = beat * (0.25 if ie >= THRESH_DRUMS else 0.5)
            if ctx.style == "ambient":
                arp_dur = beat * 0.5
            octave = 12 if ie >= THRESH_DRUMS else 0
            reps = int(dur / (arp_dur * len(pattern)))
            for rep in range(reps):
                for i, offset in enumerate(pattern):
                    at = t + (rep * len(pattern) + i) * arp_dur
                    if at < min(t + dur, end) - 0.05:
                        note = chord[i % len(chord)] + offset + octave
                        sig = arp_note(midi_to_hz(note), arp_dur * 0.7, sr,
                                       ctx.style)
                        v = vol * 0.25
                        place(bufs, sig * v, at, sr, pan=PAN["arp"])
                        notes.append({"t": round(at, 3), "layer": "arp",
                                      "midi": note, "dur": round(arp_dur * 0.7, 3),
                                      "vel": round(v, 4)})

        # Lead melody (dropped in the outro)
        if ie >= THRESH_LEAD and not in_outro:
            mel_dur = beat * 0.5
            for b in range(8):
                mt = t + b * mel_dur
                if mt < end - 0.1:
                    note = melody[melody_idx % len(melody)]
                    lead = lead_sound(midi_to_hz(note), mel_dur * 0.8, sr,
                                      ctx.style)
                    v = vol * 0.25
                    place(bufs, lead * v, mt, sr, pan=PAN["lead"])
                    notes.append({"t": round(mt, 3), "layer": "lead",
                                  "midi": note, "dur": round(mel_dur * 0.8, 3),
                                  "vel": round(v, 4)})
                    melody_idx += 1

        # Outro: quiet bells replacing everything else (reference finale)
        if in_outro:
            for i in range(3):
                at = t + i * 1.5
                if at < end - 1.0:
                    note = chord[i % len(chord)] + 24
                    bell = bell_sound(midi_to_hz(note), 1.5, sr)
                    v = vol * 0.15 * ctx.outro_factor(at)
                    place(bufs, bell * v, at, sr, pan=PAN["bell"])
                    notes.append({"t": round(at, 3), "layer": "bell",
                                  "midi": note, "dur": 1.5, "vel": round(v, 4)})

        t += chord_dur
        chord_idx += 1

    # Very quiet sections: lonely bells every ~8 s (reference section 1)
    if intensity < THRESH_SPARSE_BELLS:
        for gt in np.arange(start + 10, end - 5, 8):
            note = ctx.tonic + 24 + int(rng.choice([0, 3, 7, 12]))
            bell = bell_sound(midi_to_hz(note), 2.0, sr)
            prog = (gt - start) / max(sec_dur, 1e-9)
            v = (0.04 + prog * 0.06) * ctx.damp_factor(gt)
            place(bufs, bell * v, float(gt), sr, pan=PAN["bell"])
            notes.append({"t": round(float(gt), 3), "layer": "bell",
                          "midi": note, "dur": 2.0, "vel": round(v, 4)})


# ---------------------------------------------------------------------------
# Top-level compose
# ---------------------------------------------------------------------------

def compose(storyline: dict, out_prefix, write_mp3: bool = True,
            verbose: bool = True) -> dict:
    cfg = validate_storyline(storyline)
    sr = cfg["sr"]
    total = int(round(cfg["duration"] * sr))
    bufs = [np.zeros(total, dtype=np.float64), np.zeros(total, dtype=np.float64)]
    notes: list[dict] = []
    rng = np.random.default_rng(cfg["seed"])
    ctx = _Context(cfg)

    for sec in cfg["sections"]:
        if verbose:
            print(f"  Sektion {sec['start']:7.1f}-{sec['end']:7.1f}s "
                  f"{sec['emotion']:8s} intensity={sec['intensity']:.2f} "
                  f"bpm={sec['bpm']:.0f}")
        render_section(ctx, sec, bufs, notes, rng)

    boundaries = [s["start"] for s in cfg["sections"][1:]]
    min_len = min(s["end"] - s["start"] for s in cfg["sections"])
    xfade = min(cfg["crossfade"], min_len * 0.5)
    for buf in bufs:
        smooth_boundaries(buf, boundaries, xfade, sr)

    fi = int(min(cfg["fade_in"], cfg["duration"] * 0.2) * sr)
    fo = int(min(cfg["fade_out"], cfg["duration"] * 0.2) * sr)
    for buf in bufs:
        if fi > 0:
            buf[:fi] *= fade_in(fi)
        if fo > 0:
            buf[-fo:] *= fade_out(fo)

    for i in range(2):
        bufs[i] = delay_reverb(bufs[i], cfg["reverb_delay_ms"],
                               cfg["reverb_decay"], sr)

    # Gentle tanh drive: lifts the mean level towards the reference master
    # (measured on the original score: mean ~ -22 dB, max ~ -1.6 dB)
    # without hard clipping; drive=1.0 is neutral.
    drive = max(cfg["drive"], 1.0)
    if drive > 1.0:
        norm = float(np.tanh(drive))
        bufs[0] = np.tanh(bufs[0] * drive) / norm
        bufs[1] = np.tanh(bufs[1] * drive) / norm

    peak = float(np.max(np.abs(np.concatenate(bufs))))
    if peak > 0:
        scale = cfg["peak"] / peak
        bufs[0] *= scale
        bufs[1] *= scale

    out_prefix = Path(out_prefix)
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    wav_path = out_prefix.with_suffix(".wav")
    notes_path = out_prefix.with_suffix(".notes.json")
    mp3_path = out_prefix.with_suffix(".mp3")

    write_wav(wav_path, bufs[0], bufs[1], sr)
    if verbose:
        print(f"  WAV: {wav_path} ({wav_path.stat().st_size / 1e6:.1f} MB)")

    arrangement = {
        "title": cfg["title"],
        "duration": cfg["duration"],
        "sample_rate": sr,
        "channels": 2,
        "key": cfg["key"],
        "mode": cfg["mode"],
        "style": cfg["style"],
        "seed": cfg["seed"],
        "sections": [{k: v for k, v in s.items() if k != "melody"}
                     for s in cfg["sections"]],
        "events": {"damps": cfg["damps"],
                   "climaxes": [{"start": a, "end": b}
                                for a, b in cfg["climaxes"]],
                   "outro_start": cfg["outro_start"]},
        "notes": notes,
    }
    notes_path.write_text(json.dumps(arrangement, indent=1),
                          encoding="utf-8")
    if verbose:
        print(f"  Arrangement/Noten-Log: {notes_path} ({len(notes)} Ereignisse)")

    midi_path = out_prefix.with_suffix(".mid")
    midi_stats = write_midi(midi_path, notes, cfg["sections"], cfg["style"],
                            cfg["bpm"])
    if verbose:
        print(f"  MIDI: {midi_path} ({midi_stats['note_events']} Noten, "
              f"{midi_stats['tempo_events']} Tempo-Events)")

    mp3_written = None
    if write_mp3:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            print("  Warnung: ffmpeg nicht gefunden — MP3 übersprungen",
                  file=sys.stderr)
        else:
            result = subprocess.run(
                [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame",
                 "-b:a", "192k", "-ar", str(sr), str(mp3_path)],
                capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  Warnung: ffmpeg-Fehler: {result.stderr[-400:]}",
                      file=sys.stderr)
            else:
                mp3_written = mp3_path
                if verbose:
                    print(f"  MP3: {mp3_path} "
                          f"({mp3_path.stat().st_size / 1e6:.1f} MB)")

    return {"wav": wav_path, "mp3": mp3_written, "notes": notes_path,
            "midi": midi_path, "config": cfg, "note_count": len(notes)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

TEMPLATE = {
    "title": "my-score",
    "duration": 60.0,
    "bpm": 100,
    "key": "C",
    "mode": "minor",
    "style": "chiptune",
    "seed": 42,
    "sections": [
        {"start": 0.0, "end": 20.0, "emotion": "calm", "intensity": 0.2,
         "bpm": 60, "comment": "opening, almost nothing, slow build"},
        {"start": 20.0, "end": 40.0, "emotion": "driving", "intensity": 0.7,
         "bpm": 120, "comment": "main part, background level"},
        {"start": 40.0, "end": 60.0, "emotion": "epic", "intensity": 0.8,
         "bpm": 110, "comment": "climax + outro"},
    ],
    "events": [
        {"type": "damp", "time": 20.0, "depth": 0.5, "width": 1.0,
         "comment": "duck on a dramatic beat"},
        {"type": "climax", "start": 44.0, "end": 54.0},
        {"type": "outro", "start": 54.0, "comment": "bells fade out"},
    ],
}

SELFTEST_STORYLINE = {
    "title": "selftest",
    "duration": 3.0,
    "bpm": 120,
    "key": "C",
    "mode": "minor",
    "style": "chiptune",
    "seed": 7,
    "sections": [
        {"start": 0.0, "end": 1.5, "emotion": "calm", "intensity": 0.2},
        {"start": 1.5, "end": 3.0, "emotion": "driving", "intensity": 0.8},
    ],
    "events": [{"type": "damp", "time": 0.75, "depth": 0.5, "width": 0.2}],
}


def selftest() -> int:
    print("compose_music selftest: rendere 3 s ...")
    with tempfile.TemporaryDirectory() as tmp:
        result = compose(SELFTEST_STORYLINE, Path(tmp) / "selftest",
                         write_mp3=False, verbose=False)
        wav_path = result["wav"]
        with wave.open(str(wav_path), "rb") as w:
            assert w.getnchannels() == 2, "WAV nicht stereo"
            assert w.getsampwidth() == 2, "WAV nicht 16-bit"
            assert w.getframerate() == SAMPLE_RATE, "falsche Sample-Rate"
            n = w.getnframes()
            expected = int(3.0 * SAMPLE_RATE)
            assert n == expected, f"Samplezahl {n} != {expected}"
            frames = np.frombuffer(w.readframes(n), dtype=np.int16)
        assert int(np.max(np.abs(frames))) > 100, "WAV ist (fast) still"
        payload = json.loads(result["notes"].read_text(encoding="utf-8"))
        assert payload["notes"], "Noten-Log ist leer"
        assert len(payload["sections"]) == 2, "Sektionen fehlen im Log"
        midi_bytes = result["midi"].read_bytes()
        assert midi_bytes.startswith(b"MThd"), "kein SMF-Header"
        assert midi_bytes.count(b"MTrk") == 2, "SMF braucht 2 Tracks"
        assert b"\xff\x51\x03" in midi_bytes, "Tempo-Event fehlt im SMF"
    print(f"  OK: stereo 16-bit {SAMPLE_RATE} Hz, 3.0 s, "
          f"{result['note_count']} Noten-Ereignisse, Peak vorhanden, SMF valide")
    print("selftest bestanden")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Storyline-JSON -> videosynchroner Score (WAV + MP3 + Noten-Log)")
    parser.add_argument("storyline", nargs="?", help="Pfad zur Storyline-JSON")
    parser.add_argument("-o", "--out", help="Ausgabe-Präfix (ohne Endung)")
    parser.add_argument("--seed", type=int, help="Seed überschreiben")
    parser.add_argument("--no-mp3", action="store_true", help="nur WAV schreiben")
    parser.add_argument("--init", action="store_true",
                        help="Storyline-Template auf stdout ausgeben")
    parser.add_argument("--selftest", action="store_true",
                        help="3-s-Render mit Selbstprüfung")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if args.init:
        print(json.dumps(TEMPLATE, indent=2))
        return 0
    if not args.storyline:
        parser.error("Storyline-JSON fehlt (oder --init / --selftest nutzen)")

    story_path = Path(args.storyline)
    storyline = json.loads(story_path.read_text(encoding="utf-8"))
    if args.seed is not None:
        storyline["seed"] = args.seed
    out = args.out or str(story_path.with_suffix(""))
    print(f"=== compose_music: {storyline.get('title', story_path.stem)} ===")
    result = compose(storyline, out, write_mp3=not args.no_mp3)
    print("=== Fertig ===")
    print(f"  WAV:   {result['wav']}")
    if result["mp3"]:
        print(f"  MP3:   {result['mp3']}")
    print(f"  Noten: {result['notes']}")
    print(f"  MIDI:  {result['midi']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
