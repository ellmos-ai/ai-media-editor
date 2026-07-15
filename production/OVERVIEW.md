# production/ — Generative Erweiterungen

> Dieser Ordner ergänzt `ai-media-editor` um **generative** Produktionsfähigkeiten.
> Der Kern-Editor (Schnitt, Transkription, Animationen) ist davon getrennt in `tools/`,
> `stt/`, `editor.py`.

## Was hier liegt

| Ordner | Fähigkeit | Externe Tools (optional) |
|---|---|---|
| `musik/` | KI-Musik generieren, Stems trennen, Mastering | Suno, Udio, Lalal.ai, Auphonic |
| `podcast-tts/` | Podcast aus Skript (TTS) oder Dokument (NotebookLM) | ElevenLabs, NotebookLM, Auphonic |
| `video-generativ/` | Text-to-Video, Image-to-Video, Video-Upscaling | Runway, Luma, Pika, Kling, Magnific |
| `text/` | Textproduktion — Pointer auf Skill `textproduction` (Teilskill `text/`) | Claude, DeepL |
| `storys/` | Narrative Produktion — Pointer auf Skill `textproduction` (Teilskill `storys/`) | Claude, Midjourney |
| `pr/` | PR-Pakete — Pointer auf Skill `textproduction` (Teilskill `pr/`); Tool + Templates im Skill | LaTeX (MiKTeX), Canva, Gamma |

## Abgrenzung zum Editor-Kern

`ai-media-editor` **bearbeitet vorhandenes Material** (Schnitt, Transkription,
Animationen aus Aufnahmen). Die `production/`-Workflows **generieren neues Material
von Grund auf**. Beide können sich ergänzen: generierter Musik-Track → in
Editor-Workflow einbinden; fertig geschnittenes Gespräch → PR-Paket erstellen.

## Allgemeine Regeln

- **Optionale externe Tools:** Alle Tools mit ☁️ sind Cloud-Dienste mit eigenen
  Lizenzen/Kosten. Konto und API-Key selbst einrichten. Kein Pflichtbestandteil.
- **Userneutral:** Diese Workflows enthalten keine persönlichen Daten,
  API-Keys oder Kontodaten. Konfiguration immer in `settings.json`/`.env`.
- **Kein bach.db:** Die Workflows speichern nichts in Datenbanken.
  Output-Pfade lokal wählen.

## Pflicht-Gate vor externen Uploads

Jeder Unterordner erbt dieses Gate. Vor einem Upload zu einem mit ☁️ markierten Dienst:

1. Rechte am Eingangsmaterial sowie die beabsichtigte Nutzung des Outputs prüfen.
2. Bei erkennbaren Personen/Stimmen deren ausdrückliche Einwilligung dokumentieren;
   Voice-Cloning nur mit spezifischer Autorisierung der betroffenen Person.
3. Vertraulichkeit und Datenschutz prüfen: Darf das Material den lokalen Rechner bzw.
   die Organisation verlassen? Keine Geheimnisse, Zugangsdaten oder ungeklärten
   Kunden-/Gesundheits-/Personendaten hochladen.
4. Aktuelle Anbieterbedingungen zu Speicherort, Aufbewahrung, Training/Weiterverwendung,
   Löschung, Kosten, Wasserzeichen, Attribution und kommerzieller Lizenz direkt beim
   Anbieter prüfen. Produktfunktionen und Bedingungen ändern sich.
5. Wenn eine Freigabe fehlt oder unklar ist, den Upload stoppen und einen lokalen bzw.
   freigegebenen Prozess verwenden.
