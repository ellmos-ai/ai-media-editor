"""Lokaler STT-Adapter — ElevenLabs-Scribe-Ersatz fuer video-use.

Transkribiert Audio/Video mit wort-genauen Zeitstempeln und schreibt das
Ergebnis kompatibel mit den verwendeten ElevenLabs-Scribe-Feldern nach
<edit_dir>/transcripts/<stem>.json. Danach laeuft die gesamte
video-use-Pipeline (pack_transcripts -> render) unveraendert.

Zwei Engines:
  * faster-whisper  — 1 Sprecher, schnell, saubere Windows-Installation.
                      Wort-Zeitstempel via word_timestamps=True.
  * whisperx        — N Sprecher (Gespraechsmodus), forced alignment +
                      pyannote-Diarisierung. Braucht HuggingFace-Token.

Dieses Script ist plattform-agnostisch: identisch lokal (Windows) und auf
dem Mac Studio (per SSH) lauffaehig. Das Compute-Routing (Mac primaer,
lokal Fallback) macht stt/mac_remote.py.

Usage:
    python transcribe_local.py <media> --edit-dir <dir> \
        --engine faster|whisperx --model <size> --language de \
        [--num-speakers N] [--hf-token TOKEN] [--device cpu|cuda|auto]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

CACHE_VERSION = 1

# Modul sowohl als Teil des Pakets (ai-media-editor/stt) als auch standalone (auf dem
# Mac kopiert) importierbar machen.
try:
    from .scribe_schema import Word, build_scribe_payload, speaker_label
except ImportError:  # standalone
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scribe_schema import Word, build_scribe_payload, speaker_label


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cache_signature(
    media: Path,
    engine: str,
    model: str,
    language: str | None,
    device: str,
    num_speakers: int | None,
    hf_token: str | None,
) -> dict:
    """Return the complete, secret-free cache contract for one transcription."""
    stat = media.stat()
    return {
        "cache_version": CACHE_VERSION,
        "source_sha256": _sha256(media),
        "source_size": stat.st_size,
        "engine": engine,
        "model": model,
        "language": language,
        "device": device,
        "num_speakers": num_speakers,
        "diarization_token_present": bool(hf_token),
    }


def _valid_payload(payload: object) -> bool:
    if not isinstance(payload, dict) or not isinstance(payload.get("words"), list):
        return False
    for word in payload["words"]:
        if not isinstance(word, dict) or word.get("type") not in {"word", "spacing", "audio_event"}:
            return False
        if not isinstance(word.get("text"), str):
            return False
        if not all(key in word for key in ("start", "end", "speaker_id")):
            return False
        start, end = word["start"], word["end"]
        if isinstance(start, bool) or isinstance(end, bool):
            return False
        if not isinstance(start, (int, float)) or not isinstance(end, (int, float)):
            return False
        if not math.isfinite(start) or not math.isfinite(end) or start < 0 or end < start:
            return False
        if not isinstance(word["speaker_id"], str) or not word["speaker_id"].strip():
            return False
    return True


def cache_is_valid(
    media: Path,
    transcript_path: Path,
    engine: str,
    model: str,
    language: str | None,
    device: str,
    num_speakers: int | None,
    hf_token: str | None,
    metadata_path: Path | None = None,
) -> bool:
    """Check source/settings metadata and the minimum downstream JSON schema."""
    metadata_path = metadata_path or transcript_path.with_suffix(".meta")
    if not transcript_path.is_file() or not metadata_path.is_file() or not media.is_file():
        return False
    try:
        actual = json.loads(metadata_path.read_text(encoding="utf-8"))
        expected = cache_signature(media, engine, model, language, device, num_speakers, hf_token)
        payload = json.loads(transcript_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return actual == expected and _valid_payload(payload)


def extract_audio(media_path: Path, dest: Path) -> None:
    """Mono 16kHz PCM-WAV — identisch zu video-use/helpers/transcribe.py."""
    cmd = [
        "ffmpeg", "-y", "-i", str(media_path),
        "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
        str(dest),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def resolve_device(device: str) -> tuple[str, str]:
    """(device, compute_type). 'auto' -> cuda wenn verfuegbar, sonst cpu/int8."""
    if device == "auto":
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda", "float16"
        except Exception:
            pass
        return "cpu", "int8"
    return device, ("float16" if device == "cuda" else "int8")


# --------------------------------------------------------------------------- #
# Engine 1: faster-whisper (1 Sprecher)
# --------------------------------------------------------------------------- #
def transcribe_faster_whisper(
    audio_path: Path,
    model_size: str = "medium",
    language: str | None = "de",
    device: str = "auto",
) -> tuple[list[Word], str]:
    from faster_whisper import WhisperModel

    dev, compute_type = resolve_device(device)
    model = WhisperModel(model_size, device=dev, compute_type=compute_type)
    segments, info = model.transcribe(
        str(audio_path),
        language=language,
        word_timestamps=True,
        beam_size=5,
        vad_filter=True,
    )
    words: list[Word] = []
    for seg in segments:
        for w in (seg.words or []):
            if w.start is None or w.end is None:
                continue
            words.append(Word(text=w.word, start=w.start, end=w.end, speaker="speaker_0"))
    detected = getattr(info, "language", language or "de")
    return words, detected


# --------------------------------------------------------------------------- #
# Engine 2: WhisperX (N Sprecher, Diarisierung)
# --------------------------------------------------------------------------- #
def transcribe_whisperx(
    audio_path: Path,
    model_size: str = "large-v3",
    language: str = "de",
    device: str = "auto",
    hf_token: str | None = None,
    num_speakers: int | None = None,
) -> tuple[list[Word], str]:
    import whisperx

    dev, compute_type = resolve_device(device)
    model = whisperx.load_model(model_size, dev, compute_type=compute_type, language=language)
    audio = whisperx.load_audio(str(audio_path))
    result = model.transcribe(audio, language=language)

    align_model, meta = whisperx.load_align_model(language_code=language, device=dev)
    result = whisperx.align(
        result["segments"], align_model, meta, audio, dev,
        return_char_alignments=False,
    )

    speaker_remap: dict[str, str] = {}
    if hf_token:
        diarize_model = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=dev)
        kwargs = {}
        if num_speakers:
            kwargs["num_speakers"] = num_speakers
        diarize_segments = diarize_model(audio, **kwargs)
        result = whisperx.assign_word_speakers(diarize_segments, result)

    def map_speaker(raw: str | None) -> str:
        if not raw:
            return "speaker_0"
        if raw not in speaker_remap:
            # "SPEAKER_00" -> stabiler 0-basierter Scribe-Index
            idx = len(speaker_remap)
            speaker_remap[raw] = speaker_label(idx)
        return speaker_remap[raw]

    words: list[Word] = []
    for seg in result.get("segments", []):
        seg_start = seg.get("start", 0.0)
        seg_end = seg.get("end", seg_start)
        for w in seg.get("words", []):
            text = (w.get("word") or "").strip()
            if not text:
                continue
            start = w.get("start", seg_start)
            end = w.get("end", start if start is not None else seg_end)
            if start is None or end is None:
                continue
            words.append(Word(text=text, start=start, end=end, speaker=map_speaker(w.get("speaker"))))
    return words, language


# --------------------------------------------------------------------------- #
# Orchestrierung
# --------------------------------------------------------------------------- #
def transcribe_one(
    media: Path,
    edit_dir: Path,
    engine: str = "faster",
    model: str | None = None,
    language: str | None = "de",
    device: str = "auto",
    num_speakers: int | None = None,
    hf_token: str | None = None,
    force: bool = False,
    verbose: bool = True,
) -> Path:
    """Transkribiert eine Datei -> Scribe-JSON. Gecached wie das Original."""
    if engine not in {"faster", "whisperx"}:
        raise ValueError(f"Unbekannte STT-Engine: {engine!r}")
    if not media.is_file():
        raise FileNotFoundError(f"Mediendatei nicht gefunden: {media}")
    selected_model = model or ("large-v3" if engine == "whisperx" else "medium")
    signature = cache_signature(media, engine, selected_model, language, device, num_speakers, hf_token)
    transcripts_dir = edit_dir / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    out_path = transcripts_dir / f"{media.stem}.json"
    metadata_path = out_path.with_suffix(".meta")

    if not force and cache_is_valid(
        media, out_path, engine, selected_model, language, device, num_speakers, hf_token, metadata_path
    ):
        if verbose:
            print(f"cached: {out_path.name}")
        return out_path
    if out_path.exists() and verbose and not force:
        print(f"  Cache ungültig/veraltet: {out_path.name} wird neu erzeugt")

    t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / f"{media.stem}.wav"
        if verbose:
            print(f"  extrahiere Audio aus {media.name}", flush=True)
        extract_audio(media, audio)

        if verbose:
            print(f"  transkribiere ({engine}, model={selected_model})", flush=True)

        if engine == "whisperx":
            words, lang = transcribe_whisperx(
                audio, model_size=selected_model, language=language or "de",
                device=device, hf_token=hf_token, num_speakers=num_speakers,
            )
        else:  # faster
            words, lang = transcribe_faster_whisper(
                audio, model_size=selected_model, language=language, device=device,
            )

    payload = build_scribe_payload(words, language_code=lang)
    transcript_fd, transcript_name = tempfile.mkstemp(
        prefix=f".{out_path.name}.", suffix=".tmp", dir=out_path.parent
    )
    os.close(transcript_fd)
    metadata_fd, metadata_name = tempfile.mkstemp(
        prefix=f".{metadata_path.name}.", suffix=".tmp", dir=metadata_path.parent
    )
    os.close(metadata_fd)
    transcript_tmp = Path(transcript_name)
    metadata_tmp = Path(metadata_name)
    try:
        transcript_tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(transcript_tmp, out_path)
        metadata_tmp.write_text(json.dumps(signature, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(metadata_tmp, metadata_path)
    finally:
        transcript_tmp.unlink(missing_ok=True)
        metadata_tmp.unlink(missing_ok=True)

    if verbose:
        n_words = sum(1 for w in payload["words"] if w["type"] == "word")
        n_spk = len({w["speaker_id"] for w in payload["words"] if w.get("speaker_id")})
        dt = time.time() - t0
        print(f"  gespeichert: {out_path.name} | {n_words} Woerter, {n_spk} Sprecher, {dt:.1f}s")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Lokaler Scribe-Ersatz (faster-whisper / WhisperX)")
    ap.add_argument("media", type=Path, help="Audio- oder Videodatei")
    ap.add_argument("--edit-dir", type=Path, default=None, help="Default: <media_parent>/edit")
    ap.add_argument("--engine", choices=["faster", "whisperx"], default="faster")
    ap.add_argument("--model", type=str, default=None, help="Whisper-Modellgroesse")
    ap.add_argument("--language", type=str, default="de")
    ap.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto")
    ap.add_argument("--num-speakers", type=int, default=None)
    token_group = ap.add_mutually_exclusive_group()
    token_group.add_argument("--hf-token", type=str, default=None,
                             help="HuggingFace-Token (lokale WhisperX-Diarisierung)")
    token_group.add_argument("--hf-token-file", type=Path, default=None,
                             help="Datei mit HuggingFace-Token (für geschützte Remote-Übergabe)")
    ap.add_argument("--force", action="store_true", help="Cache ignorieren")
    args = ap.parse_args()

    media = args.media.resolve()
    if not media.exists():
        sys.exit(f"Datei nicht gefunden: {media}")
    edit_dir = (args.edit_dir or (media.parent / "edit")).resolve()

    hf_token = args.hf_token
    if args.hf_token_file:
        hf_token = args.hf_token_file.read_text(encoding="utf-8").strip() or None

    transcribe_one(
        media=media, edit_dir=edit_dir, engine=args.engine, model=args.model,
        language=args.language, device=args.device, num_speakers=args.num_speakers,
        hf_token=hf_token, force=args.force,
    )


if __name__ == "__main__":
    main()
