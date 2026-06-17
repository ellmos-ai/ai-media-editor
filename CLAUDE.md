# ai-media-editor — KI-Medien-Editor (Video · Audio · Podcast)

Claude Code als Video-/Podcast-Editor (nach dem Setup von Julian Ivanov,
YouTube `_7bhJYTi5e0`), aber mit **eigener lokaler/Mac-Transkription statt
ElevenLabs**. Du (Claude Code) bist der Editor — wie im Video. Die Skripte
hier erledigen die deterministische Vorbereitung; die kreativen Schnitt- und
Animations-Entscheidungen triffst du.

## Drei-Werkzeug-Stack (wie im Video)

| Werkzeug | Rolle | Hier |
|---|---|---|
| **video-use** (browser-use) | Schnitt anhand Wort-Transkript | `<TOOLS_ROOT>\video-use` |
| **Hyperframes** (HeyGen) | HTML/CSS/JS → MP4-Animationen | `npx --yes hyperframes …` (Node ≥ 22) |
| ~~Claude Design (Web)~~ → **`frontend-design`-Skill** | Motion-Graphics/Branding generieren | lokaler Skill, kein Browser/ZIP nötig |

**ElevenLabs Scribe ist ersetzt** durch `stt/transcribe_local.py` (faster-whisper
für 1 Sprecher, WhisperX für mehrere) mit **Mac-Studio-primär, lokal-Fallback**.
Der Ersatz erzeugt **byte-kompatibles Scribe-JSON** → video-use bleibt ungepatcht.

## Architektur-Split (wichtig)

- **Code/Doku/Projekte** liegen hier in `ai-media-editor` (OneDrive, versioniert).
- **Schwere Tools + venv** liegen in `<TOOLS_ROOT>` (NICHT OneDrive —
  venv-/Sync-Konflikte vermeiden). Immer mit dem venv-Python arbeiten:
  `<TOOLS_ROOT>\.venv\Scripts\python.exe`.

## Die 8 Usecases

| # | Usecase | Engine | Output |
|---|---|---|---|
| 1 | Audio, 1 Sprecher | faster-whisper | Audio-Podcast geschnitten |
| 2 | Audio, mehrere Sprecher | WhisperX +diarize | Audio-Podcast, Sprecher-getrennt |
| 3 | Video (A+V), 1 Sprecher | faster-whisper | Video geschnitten + Animationen *(Original-Setup)* |
| 4 | Video (A+V), mehrere Sprecher | WhisperX +diarize | Video geschnitten + Animationen + Sprecher-Tracking |
| 5 | Video, nur Tonspur nutzen | je nach | Audio-Podcast (Bild verworfen) |
| 6 | Erklärvideo aus Audio | je nach | voll generiertes Video (frontend-design + Hyperframes) |
| 7 | Audio + animiertes Cover | faster-whisper | Audio + Hyperframes-Cover-Loop |
| 8 | Werbeclip / Ad (kurz) | faster-whisper | Werbeclip 15–60 s (16:9 + 9:16) — OpenMontage `clip-factory` od. frontend-design+Hyperframes |

Details + Schritt-für-Schritt je Modus: **`docs/USECASES.md`**.

## Workflow (immer gleich)

```bash
VENV="<TOOLS_ROOT>/.venv/Scripts/python.exe"

# 0. Einmal: Umgebung prüfen
PYTHONIOENCODING=utf-8 "$VENV" editor.py doctor

# 1. Vorbereiten: transkribieren (geroutet) + packen → takes_packed.md
PYTHONIOENCODING=utf-8 "$VENV" editor.py prepare "<media>" --mode <1-7> [--project <name>] [--num-speakers N]
```

`prepare` legt `projects/<name>/edit/` an mit `transcripts/<stem>.json` (Scribe-Format),
`takes_packed.md` und `cut_view.md`. **`takes_packed.md` ist deine primäre Lesefassung**
für Schnitte; **`cut_view.md` zeigt die Pausen als explizite Schnittkandidaten**.

## Kern: Schneiden in sinnvolle Abschnitte (Pausen = Schnittinfo)

Worum es eigentlich geht: das Material in **sinnvolle Abschnitte schneiden**. Die
**Pausen sind die wertvollste Schnittinformation** — sie stecken exakt im Scribe-JSON
und werden in `cut_view.md` sichtbar gemacht (✂✂ ≥0.8s stark · ✂ ≥0.4s gut · · ≥0.15s
möglich, plus ⟦TRIM⟧ für Vorlauf/Stille). Schneide an den stärksten Pausen, snappe auf
Wortgrenzen, padde die Kanten. Alles andere (Animationen, Cover, Diarisierung) ist
nachgelagert.

Danach faehrst **du** den kreativen Teil — lies dazu `<TOOLS_ROOT>\video-use\SKILL.md`
(der vollständige video-use-Editor-Workflow inkl. **Hard Rules** für korrektes Rendern)
und `docs/USECASES.md` (was je Modus zu tun ist).

## Harte Regeln (aus video-use SKILL.md — nicht verhandelbar)

1. **Nie mitten im Wort schneiden** — Schnittkanten auf Wortgrenzen aus dem Transkript snappen.
2. **Jede Schnittkante padden** (30–200 ms) — absorbiert Timestamp-Drift.
3. **Untertitel ZULETZT** in der Filterkette (nach allen Overlays).
4. **Pro-Segment extrahieren → `-c copy` concat** (kein Single-Pass-Filtergraph).
5. **30 ms Audio-Fades an jeder Segmentgrenze** (sonst Knackser).
6. **Transkripte cachen** — nie neu transkribieren, außer die Quelle änderte sich.
7. **Animationen parallel** über mehrere `Agent`-Subagenten bauen.
8. **Strategie vom User bestätigen lassen**, bevor du schneidest.

## STT-Engine-Logik

- 1 Sprecher → **faster-whisper** (schnell, kein Token nötig).
- mehrere Sprecher (Usecase 2/4 oder `--num-speakers > 1`) → **faster-whisper +
  tokenfreie LLM-Diarisierung** (`stt/diarize_llm.py`). Whisper transkribiert, dann
  ordnet **das LLM die Sprecher aus dem Text zu** (Anrede, Frage/Antwort, Pausen) —
  **kein HuggingFace-Token** nötig. Ablauf: `editor.py prepare` erzeugt
  `edit/diarization/<stem>.prompt.md` + `.phrases.json`; Claude Code (oder eine
  lokale Mac-LLM) schreibt `<stem>.labels.json` und ruft `diarize_llm.py apply`.
  Das ist der MetaMedia-v1.1-Ansatz ("Sprecher aus dem Text").
  - **Diarisierung ist best-effort, nicht Perfektion.** Sie ist nur in manchen Fällen
    überhaupt nötig. Bei Erklär-/Inhaltsvideos zählen **Sinn und Inhalt mehr als die
    satzgenaue Zuordnung** — wenn von zwei Sprechern mal ein Satz „falsch" gelabelt ist,
    schadet das dem Verständnis nicht. Nicht überoptimieren; im Zweifel grob zuordnen
    und weiter zum Schnitt.
  - **Akustische Alternative** (`whisperx`): präziser bei Cross-Talk, braucht aber
    den **HF-Token** (`hf_token`, pyannote ist gated). Nur nutzen wenn LLM-Zuordnung
    nicht reicht; `config/settings.json` → `engines.multi_speaker="whisperx"`.
- **Compute:** Default Mac Studio (`compute.prefer="mac"`); bei SSH-Ausfall automatisch
  lokal. Umstellen in `config/settings.json`.

## Verweise

- Usecase-Details: `docs/USECASES.md`
- video-use-Editor-Workflow + Render-Helpers: `<TOOLS_ROOT>\video-use\SKILL.md`
- Branding/Design-Tokens: `brand/design-tokens.css`
- Konfiguration: `config/settings.json`
