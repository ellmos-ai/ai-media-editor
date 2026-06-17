<p align="center"><img src="assets/banner.svg" alt="ai-media-editor — Video · Audio · Podcast, local" width="100%"></p>

# ai-media-editor — KI-Medien-Editor (Video · Audio · Podcast, lokal, ohne ElevenLabs)

Claude Code als Video-/Podcast-Editor (Setup nach YouTube `_7bhJYTi5e0`,
Julian Ivanov), aber mit **eigener Transkription statt ElevenLabs Scribe**.

## Was es ist

Der Drei-Werkzeug-Stack aus dem Video:
- **video-use** — schneidet anhand des Wort-Transkripts (Pausen/Versprecher raus)
- **Hyperframes** — HTML/CSS/JS → MP4-Animationen
- **`frontend-design`-Skill** — erzeugt Motion-Graphics/Branding (ersetzt das
  Web-Tool „Claude Design")

…wobei die **ElevenLabs-Scribe-Transkription** ersetzt ist durch lokale Engines
(**faster-whisper** für 1 Sprecher, **WhisperX** für Gespräche) mit
**Mac-Studio-primär, Laptop-Fallback**. Der Ersatz schreibt byte-kompatibles
Scribe-JSON — video-use läuft dadurch komplett ungepatcht.

## Setup

1. **Konfig anlegen:** `config/settings.example.json` → `config/settings.json` kopieren und
   eigene Werte eintragen (Compute `local`/`mac`, Engines, `paths.*`).
2. **`<TOOLS_ROOT>`** in dieser Doku = `paths.tools_root` aus deiner `settings.json` — der Ort der
   schweren Tools + venv (`video-use`, ffmpeg, Node ≥ 22). **Nicht** in einem synchronisierten
   Cloud-Ordner anlegen (venv-/Sync-Konflikte). `<OPENMONTAGE_DIR>` = optionaler OpenMontage-Klon
   (nur für Werbeclip-Usecase 8).
3. Externe Werkzeuge: `video-use` (browser-use-basierter Transkript-Schnitt), Hyperframes (HTML→MP4),
   sowie der `frontend-design`-Skill. STT lokal via faster-whisper/WhisperX.

## Schnellstart

```bash
VENV="<TOOLS_ROOT>/.venv/Scripts/python.exe"

# Umgebung prüfen
PYTHONIOENCODING=utf-8 "$VENV" editor.py doctor

# Usecase-Tabelle
PYTHONIOENCODING=utf-8 "$VENV" editor.py modes

# Projekt vorbereiten (transkribieren + packen)
PYTHONIOENCODING=utf-8 "$VENV" editor.py prepare "C:/pfad/zu/aufnahme.mp4" --mode 3 --project mein-video
```

Danach faehrt **Claude Code** den kreativen Schnitt/Animations-Teil — Anleitung in
[`CLAUDE.md`](CLAUDE.md) und [`docs/USECASES.md`](docs/USECASES.md).

## Die 8 Usecases

| # | Eingang | Sprecher | Output |
|---|---|---|---|
| 1 | Audio | 1 | Audio-Podcast geschnitten |
| 2 | Audio | mehrere | Audio-Podcast, sprechergetrennt |
| 3 | Video (A+V) | 1 | Video geschnitten + Animationen |
| 4 | Video (A+V) | mehrere | Video + Animationen + Sprecher-Tracking |
| 5 | Video → nur Tonspur | 1/mehrere | Audio-Podcast (Bild verworfen) |
| 6 | Audio | 1/mehrere | Erklärvideo voll generiert |
| 7 | Audio | 1 | Audio + animiertes Cover |
| 8 | Audio/Brief | 1 | Werbeclip/Ad (15–60 s, 16:9 + 9:16) — OpenMontage clip-factory / Hyperframes |

## Struktur

```
ai-media-editor/                         (OneDrive — Code/Doku/Projekte)
├── CLAUDE.md                    ← Anleitung für Claude Code (Editor-Workflow)
├── README.md
├── editor.py                    ← Orchestrator (prepare / modes / doctor)
├── stt/
│   ├── scribe_schema.py         ← Scribe-JSON-Format (Vertrag mit video-use)
│   ├── transcribe_local.py      ← faster-whisper + WhisperX → Scribe-JSON
│   └── mac_remote.py            ← Compute-Routing (Mac primär, lokal Fallback)
├── config/settings.json         ← Mac-SSH, Engines, Modelle, HF-Token
├── brand/design-tokens.css      ← Branding für generierte Animationen
├── docs/USECASES.md             ← Schritt-für-Schritt je Modus
└── projects/<name>/edit/        ← pro Projekt: transcripts/, takes_packed.md, …

<TOOLS_ROOT>/     (NICHT OneDrive — venv/Tools)
├── .venv/                       ← Python-venv (faster-whisper, video-use, …)
└── video-use/                   ← geklontes browser-use/video-use (ungepatcht)
```

## Voraussetzungen

- **Lokal:** ffmpeg ✅, Node ≥ 22 ✅ (Hyperframes), venv unter `<TOOLS_ROOT>`.
- **Mac Studio:** faster-whisper + WhisperX im `science`-venv ✅, per SSH erreichbar.
- **HuggingFace-Token** nur für WhisperX-Sprechertrennung (UC2/UC4) — in
  `config/settings.json`.

## Herkunft / Lizenzen

- video-use: [browser-use/video-use](https://github.com/browser-use/video-use)
- Hyperframes: [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) (Apache-2.0)
- STT: faster-whisper (MIT), WhisperX (BSD-2) — die WhisperX-Integration basiert
  auf dem MetaMedia-Prototyp (`.UMBRUCH/.../MetaMedia/prototype`), die
  faster-whisper-Basis auf dem USB-Podcast-Studio.
