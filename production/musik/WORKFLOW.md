# Musik-Generierung — Workflow

> Generierung von KI-Musik, Stem-Trennung und Audio-Mastering.
> Alle Tools optional (☁️ = externer Cloud-Dienst, kostenpflichtig/freemium).
> Vor jedem Upload gilt das Rechte-/Einwilligungs-/Datenschutz-Gate in
> [`../OVERVIEW.md`](../OVERVIEW.md); insbesondere Lyrics-, Sample- und kommerzielle
> Output-Rechte prüfen.

---

## 1. Song generieren

### 1a. Mit Suno ☁️ (suno.com)

```
1. suno.com → "Create"
2. Modus wählen:
   - "Custom Mode" (empfohlen): Lyrics + Stil getrennt eingeben
   - "Simple Mode": Beschreibung genügt, Lyrics werden generiert
3. Eingabe:
   - Lyrics: vollständigen Songtext einfügen (Verse/Chorus/Bridge markieren)
   - Style prompt: Stil präzise beschreiben, z.B.:
       "cinematic orchestral, slow build, epic, no vocals"
       "indie pop, female vocals, upbeat, acoustic guitar"
   - Titel: optional
4. Generieren → 2 Varianten → beste herunterladen (.mp3/.wav)
```

**Tipps:**
- `[Verse]`, `[Chorus]`, `[Bridge]`, `[Outro]` als Tags in Lyrics verwenden
- Stil-Tokens konkret: BPM, Instrumente, Stimmung, Epoche
- Ohne Vocals: "instrumental only" in den Style prompt

### 1b. Mit Udio ☁️ (udio.com)

```
1. udio.com → Prompt eingeben
2. Stil + Stimmung + Instrumente beschreiben
3. Optional: eigene Lyrics im "Custom Lyrics"-Feld
4. Generieren → Varianten verlängern mit "Extend" (Intro/Outro hinzufügen)
5. Besten Take herunterladen
```

**Unterschied zu Suno:** Udio oft klangstärker bei orchestralen/elektronischen
Stilen; Suno stärker bei Pop/Rock mit Gesang.

---

## 2. Stems extrahieren (Lalal.ai) ☁️

Stems trennen = Gesang / Instrumente / Bass / Schlagzeug isolieren.

```
1. lalal.ai → Datei hochladen
2. Separation-Modus wählen:
   - "Vocal & Instrumental" (Standard, schnell)
   - "5-Stem" (Drums / Bass / Piano / Guitar / Vocals)
   - "6-Stem" oder "Phoenix" für präzisere Ergebnisse
3. Verarbeiten → Stems einzeln herunterladen
```

**Anwendungsfälle:**
- Karaoke-Track erstellen (Gesang entfernen)
- Eigenen Gesang über Instrumental legen
- Problematische Frequenzen isolieren und nachbearbeiten
- Remix: nur Schlagzeug + Bass behalten, Rest ersetzen

---

## 3. Audio optimieren / Mastering (Auphonic) ☁️

Lautstärke normalisieren, Rauschen entfernen, Loudness-Target setzen.

```
1. auphonic.com → neues Projekt anlegen
2. Audio-Datei hochladen (.mp3 / .wav / .flac)
3. Einstellungen:
   - "Loudness Target": -16 LUFS (Podcast), -14 LUFS (YouTube/Streaming)
   - "Noise & Hum Reduction": Stufe nach Bedarf (Low / Medium / High)
   - "Filtering": Hochpassfilter 80 Hz (entfernt Brummen)
   - "Crossgate": Stille-Segmente abschwächen
4. Ausgabe-Format wählen (mp3 192kbps / wav 44.1kHz)
5. Verarbeiten → herunterladen
```

**Hinweis:** Kontingente, Preise und API-Funktionen ändern sich; vor Nutzung die
aktuellen Anbieterbedingungen prüfen.

---

## Outputs

| Schritt | Output | Weiterverwendung |
|---|---|---|
| Song generieren | `.mp3` / `.wav` | Direkt; oder Stems trennen |
| Stems trennen | Je Stem eine Datei | Remix, Karaoke, Sampling |
| Mastering | `.mp3` / `.wav` normalisiert | Finaler Podcast-/Video-Track |

---

## Integration mit dem Editor-Kern

Generierten Track in ai-media-editor-Projekt einbinden:
```bash
# Track liegt z.B. unter projects/<name>/assets/music_track.mp3
# In editor.py overlay-Workflow als Hintergrundspur nutzen (siehe docs/USECASES.md UC6/UC8)
```
