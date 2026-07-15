# Podcast-TTS — Workflow

> Podcast aus einem **Skript** erstellen (Text→Sprache) oder aus einem **Dokument**
> automatisch generieren (NotebookLM). Dies ist die Gegenrichtung zur lokalen
> Transkription im Editor-Kern (dort: Sprache→Text).
>
> Alle Tools optional (☁️ = externer Cloud-Dienst, kostenpflichtig/freemium).
> Vor jedem Upload gilt das Rechte-/Einwilligungs-/Datenschutz-Gate in
> [`../OVERVIEW.md`](../OVERVIEW.md).

---

## Abgrenzung

| Dieser Workflow | Editor-Kern (stt/) |
|---|---|
| Text/Dokument **→ Audio** (generieren) | Audio/Video **→ Text** (transkribieren, schneiden) |
| ElevenLabs TTS, NotebookLM | faster-whisper, WhisperX |
| Neuen Podcast-Inhalt erzeugen | Bestehende Aufnahme bearbeiten |

---

## 1. TTS-Podcast aus Skript (ElevenLabs) ☁️

```
1. Skript vorbereiten:
   - Vollständigen Podcast-Text in Absätze gliedern
   - Sprecher-Wechsel markieren: [SPRECHER_A] / [SPRECHER_B]
   - Pausen mit <break time="1s"/> oder Leerzeilen

2. elevenlabs.io → "Speech Synthesis" oder "Projects"
   - "Projects" (empfohlen für lange Texte): Kapitel anlegen,
     je Sprecher eigene Stimme auswählen
   - Einzelne Absätze: "Speech Synthesis" → Text eingeben → Stimme wählen

3. Stimmen konfigurieren:
   - Stimmen klonen: nur mit dokumentierter, spezifischer Einwilligung der
     betroffenen Person; anschließend die aktuell angebotene Voice-Funktion nutzen
   - Fertige Stimmen: "Voice Library" durchsuchen (Sprache, Stil, Geschlecht filtern)
   - Für Deutsch: auf Deutsch trainierte Stimmen bevorzugen

4. Stability / Similarity / Style:
   - Stability 50–70 % (natürlicher Klang vs. Konsistenz)
   - Similarity 70–85 %
   - Style 10–30 % (zu hoch = übertrieben)

5. Generieren → je Segment herunterladen oder Projekt als ZIP exportieren

6. Segmente zusammenfügen (optional):
   ffmpeg -f concat -safe 0 -i segments.txt -c copy podcast_final.mp3
```

---

## 2. Dokument → Podcast (NotebookLM) ☁️

NotebookLM generiert automatisch ein **2-Sprecher Audio Overview** aus Dokumenten —
ideal für informative Podcasts ohne Skript-Schreiben.

```
1. notebooklm.google.com → "New Notebook"

2. Quellen hinzufügen (aktuelle Mengen- und Formatgrenzen beim Anbieter prüfen):
   - PDF hochladen
   - Google Docs verlinken
   - URLs einfügen (Webseiten, Artikel)
   - Text direkt einfügen

3. "Audio Overview" generieren:
   - Unten rechts auf "Audio Overview" klicken
   - Wartezeit: 1–5 Minuten je nach Dokumentgröße
   - Ergebnis: automatisch erzeugte Dialog-/Podcast-Ausgabe; verfügbare Sprachen,
     Stimmen und Längen in der aktuellen Anbieteroberfläche prüfen

4. Anhören und herunterladen (Download-Symbol)

5. Optional: Anweisungen anpassen ("Customize" / "Guide the audio overview"):
   - Zielgruppe vorgeben (Einsteiger / Experten)
   - Fokus-Themen benennen
   - Format (Interview, Erklärung, Diskussion)
```

**Hinweis:** Sprach-, Stimmen- und Exportfunktionen von Cloud-Diensten ändern sich.
Vor Produktionsbeginn einen kurzen, unkritischen Test mit der gewünschten Sprache durchführen.

---

## 3. Nachbearbeitung (Auphonic) ☁️

TTS-Ausgaben klingen oft zu laut/zu leise oder haben Rauschen aus der Komprimierung.

```
1. TTS-Datei in Auphonic hochladen (auphonic.com)
2. Ziel-Loudness: -16 LUFS (Podcast-Standard)
3. "Noise & Hum Reduction": Low (TTS hat meist wenig Rauschen)
4. Exportformat: MP3 192 kbps oder WAV 44.1 kHz
```

---

## Outputs

| Schritt | Output | Weiterverwendung |
|---|---|---|
| ElevenLabs TTS | `.mp3` / `.wav` je Segment oder gesamt | Direkt / Auphonic |
| NotebookLM | `.wav` Audio Overview | Direkt / Auphonic |
| Auphonic | `.mp3` normalisiert | Fertig-Podcast |

---

## Integration mit dem Editor-Kern

Nach Generierung kann das TTS-Audio im Editor-Kern weiterbearbeitet werden —
z.B. Stille kürzen, Abschnitte neu ordnen, Animationscover anfügen (UC7).
Dafür: TTS-Datei als Input für `editor.py prepare --mode 1` nutzen.
