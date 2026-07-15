# Usecases — Schritt für Schritt

8 Eingangs-/Ausgangs-Konfigurationen. Gemeinsam ist immer Phase 0 (Vorbereitung
via `editor.py prepare`); danach unterscheidet sich der kreative Teil.

```bash
VENV="<TOOLS_ROOT>/.venv/Scripts/python.exe"
VU="<TOOLS_ROOT>/video-use"
```

**Phase 0 (alle Usecases):**
```bash
PYTHONIOENCODING=utf-8 "$VENV" editor.py prepare "<media>" --mode <#> --project <name> [--num-speakers N]
```
→ erzeugt `projects/<name>/edit/transcripts/<stem>.json` (Scribe-Format) und
`takes_packed.md`. Letzteres ist die Lesefassung für Schnitt-Entscheidungen.

---

## UC1 — Audio, 1 Sprecher → geschnittener Audio-Podcast
- **Engine:** faster-whisper · **Compute:** lokal (optional Remote→lokal)
1. `prepare --mode 1`
2. `takes_packed.md` lesen → Füllwörter, lange Pausen (≥0,4 s), Versprecher/Retakes markieren.
3. `edl.json` bauen (nur `sources` + Segmente, keine Overlays).
4. Audio rendern: pro Segment extrahieren → 30 ms-Fades → concat. (Reines Audio,
   `render.py --no-subtitles` bzw. nur Audiospur exportieren.)

## UC2 — Audio, mehrere Sprecher (Gespräch) → Audio-Podcast, sprechergetrennt
- **Engine:** faster-whisper + **tokenfreie LLM-Diarisierung** (kein HF-Token)
1. `prepare --mode 2 --num-speakers <N>` (N wenn bekannt) — transkribiert UND erzeugt
   den Diarisierungs-Prompt `edit/diarization/<stem>.prompt.md` + `.phrases.json`.
2. **Sprecher zuordnen (Claude Code als LLM):** Prompt + Phrasen lesen →
   `<stem>.labels.json` schreiben (`[{"i":idx,"speaker":int}]`) →
   `python stt/diarize_llm.py apply --edit-dir <dir> --stem <stem> --labels <labels>`.
   Danach zeigt `takes_packed.md` `S0/S1/...` und bricht an Sprecherwechseln.
3. Schnitt wie UC1, Sprecher-Handoffs mit Luft (400–600 ms).
4. `edl.json` → Audio-Render.
> Hinweis: Die Segmentierung ist **satz-fein** (split an `. ? !` + Pausen), damit
> Sprecherwechsel in flüssigen Dialogen sauber an Segmentgrenzen liegen. Bei sehr
> dichtem Cross-Talk ist die akustische Alternative `whisperx` (HF-Token) präziser.

## UC3 — Video (A+V), 1 Sprecher → geschnittenes Video + Animationen *(das Original-Setup)*
- **Engine:** faster-whisper · voller video-use-Workflow
1. `prepare --mode 3`
1b. **Bild-Ebene** (`editor.py frames`): grobe Übersicht `--contact-sheet`, dann
    interessante Stellen `--from x --to y --step z` nachsampeln. Bilder per Read-Tool
    beurteilen → `frame_view.md` mappt Bild↔Zeit (Scribe-Zeitbasis). Liefert visuelle
    Schnitt-/Overlay-Hinweise, die der reine Transkript-Schnitt nicht sieht.
2. Schnitt wie UC1 (Wortgrenzen, Padding, harte Regeln in `$VU/SKILL.md`).
3. **Animationen:** Storyboard aus dem Transkript → pro Beat eine HTML-Animation.
   - Mit `frontend-design`-Skill HTML/Motion-Graphics erzeugen (Branding aus
     `brand/design-tokens.css`, nicht aufs Gesicht legen → `--safe-margin`).
   - Mit Hyperframes zu MP4 rendern: `npx --yes hyperframes render <comp> -o slot.mp4`.
   - **Parallel** über mehrere `Agent`-Subagenten (eine Animation je Slot).
4. `render.py <edl.json> -o final.mp4 --build-subtitles` — Overlays + Untertitel ZULETZT.
5. Self-Eval (Schnittkanten, Audio-Pops, verdeckte Untertitel), dann 4K-Final.

## UC4 — Video (A+V), mehrere Sprecher → Video + Animationen + Sprecher-Tracking
- **Engine:** faster-whisper + **tokenfreie LLM-Diarisierung** (wie UC2, kein HF-Token)
- Wie UC3 (inkl. **Bild-Ebene** via `editor.py frames` — hilft hier zusätzlich, Sprecher
  im Bild zu verorten/zu bestätigen), zusätzlich: Sprecher-Zuordnung via `diarize_llm`
  (Schritt 2 aus UC2), dann Lower-Third-Namenskarten pro Sprecher (S0/S1…), Schnitt folgt
  Sprecherwechseln.

## UC5 — Video-Ausgangsmaterial, nur Tonspur nutzen → Audio-Podcast
- **Engine:** faster-whisper (bei mehreren Sprechern plus LLM-Diarisierung;
  WhisperX nur wenn entsprechend konfiguriert)
1. `prepare --mode 5` — extrahiert nur die Audiospur, Bild wird verworfen.
2. Weiter wie UC1/UC2 (reiner Audioschnitt).

## UC6 — Erklärvideo aus Audio → voll generiertes Video
- **Engine:** je nach Sprecherzahl · Output: komplett generiert (kein Originalbild)
1. `prepare --mode 6`
2. Transkript → **Storyboard** (Szenen/Beats mit Timestamps).
3. Pro Szene: `frontend-design` erzeugt Motion-Graphics-HTML (Branding-Tokens),
   Hyperframes rendert. Audio (Originaltonspur) als Tonbett darunterlegen.
4. Optional No-Copyright-Musikbett (z. B. Pixabay) ergänzen.

## UC7 — Audio + animiertes Video-Cover
- **Engine:** faster-whisper · Output: Audio + Loop-Cover
1. `prepare --mode 7`
2. Audioschnitt wie UC1.
3. Ein animiertes Cover (Standbild/Loop, Titel + Branding) via `frontend-design`
   → Hyperframes; über die volle Tonspur legen (wie Musik-Video auf YouTube).

## UC8 — Werbeclip / Ad (kurz, 15–60 s) → generierter, gebrandeter Werbespot
- **Engine:** faster-whisper (kurze VO/Brief) · Output: kurzer Ad-Clip (16:9 **und** 9:16)
- **Generierungs-Backend:** OpenMontage `clip-factory` *(reicher: Stock/generierte Clips,
  Musik, Avatar/Voice)* **oder** `frontend-design` + Hyperframes *(reiner Brand-Motion-Clip)*.

1. `prepare --mode 8` — kurze Voiceover-Aufnahme **oder** den gesprochenen Brief transkribieren.
   (Reiner Text-Brief: Brief als VO einsprechen oder Transkript-JSON von Hand füllen.)
2. **Ad-Storyboard** aus dem Transkript: **Hook (0–3 s) → Nutzen/Produkt → CTA (Endcard)**.
   Werbe-Dramaturgie: ein Kernversprechen, ein Call-to-Action, kurze Schnitte.
3. **Generieren — zwei Wege:**
   - **OpenMontage clip-factory** (`<OPENMONTAGE_DIR>`): Pipeline-Definition
     `pipeline_defs/clip-factory.yaml`, Director-Skill `skills/pipelines/clip-factory/`.
     Stages `research → proposal → script → scene_plan → assets → edit → compose`;
     Komposition via Remotion **oder** Hyperframes (dieselbe Engine wie hier).
     ```bash
     OMPY="<OPENMONTAGE_DIR>/.venv/Scripts/python.exe"
     ```
   - **Brand-pur:** `frontend-design` erzeugt Motion-Graphics-HTML aus `brand/design-tokens.css`
     → Hyperframes rendert je Szene → FFmpeg-concat + Musikbett.
4. **Branding & CTA:** Logo/Farben/Font aus `brand/`; Endcard mit CTA + Kontakt/URL.
   Musikbett **kommerziell freigegeben** (Lizenz prüfen, nicht „free for personal").
5. **Render + Untertitel zuletzt**; zusätzlich **9:16-Variante** für Social (Reels/Shorts/TikTok).
6. **Lizenz-Gate (kommerziell!):** Werbung = kommerzielle Nutzung → für **jedes** verwendete
   Modell/Asset die kommerzielle Lizenz prüfen. Manche lokale Video-Modelle (einzelne
   WAN/Hunyuan/CogVideo-Gewichte) und „free"-Stock sind **research-/non-commercial-only**.
   Vor Veröffentlichung die aktuellen Tool-, Asset-, Modell- und Musiklizenzen für den
   konkreten Vertriebsweg prüfen.

---

## Engine- & Compute-Hinweise
- **HF-Token:** nur nötig, wenn `engines.multi_speaker="whisperx"` gesetzt ist. Ohne
  Token liefert WhisperX keine akustische Sprechertrennung; der Standardweg mit
  faster-whisper + LLM-Diarisierung braucht keinen Token.
- **Compute:** Default lokal. Optional `compute.prefer="mac"`; bei SSH-Ausfall wird lokal
  weitergearbeitet. Remote-Modus überträgt die vollständige Eingabedatei an den
  konfigurierten Host und darf nur mit entsprechender Freigabe verwendet werden.
- **Cache:** gültig nur bei gleichem Quellenhash sowie gleicher Engine-, Modell-, Sprach-,
  Geräte- und Sprecherkonfiguration. Veraltete oder beschädigte Caches werden erneuert.
- **Scribe-Kompatibilität:** `transcripts/<stem>.json` enthält die Felder, die die
  eingesetzten video-use-Helfer lesen (`words[]` mit type/text/start/end/speaker_id).
  Es ist ein konsumentenkompatibler Teilvertrag, keine vollständige Byte-Replik.
