# Generatives Video — Workflow

> KI-Video aus Text oder Bild generieren, Video verlängern und upscalen.
> Dies ergänzt die UC6-/UC8-Animationen im Editor-Kern (Hyperframes/frontend-design)
> um vollständig generiertes Video-Material.
>
> Alle Tools optional (☁️ = externer Cloud-Dienst, kostenpflichtig/freemium).
> Vor jedem Upload gilt das Rechte-/Einwilligungs-/Datenschutz-Gate in
> [`../OVERVIEW.md`](../OVERVIEW.md). Für Personen-, Marken- und Referenzbilder
> zusätzlich Einwilligung, Persönlichkeitsrechte und kommerzielle Nutzung prüfen.

---

## Abgrenzung zum Editor-Kern

| Dieser Workflow | Editor-Kern (UC3/4/6/8) |
|---|---|
| Neues Video-Material generieren | Vorhandenes Material bearbeiten/animieren |
| Runway, Luma, Pika, Kling | Hyperframes + frontend-design-Skill |
| Text-Prompt oder Bild als Eingabe | Audio-Transkript als Grundlage |

Generiertes Material kann anschließend in den Editor-Kern eingebunden werden
(als B-Roll, Intro/Outro, Überblendung).

---

## 1. Text-to-Video

### 1a. Runway ☁️ (runwayml.com)

```
1. runwayml.com → aktuelle Video-Generierungsfunktion öffnen
2. Prompt eingeben (Englisch empfohlen):
   - Motiv: Subjekt, Aktion, Umgebung
   - Stil: "cinematic", "photorealistic", "animation", "drone shot"
   - Kamera: "slow motion", "handheld", "aerial", "zoom in"
   Beispiel: "A lone lighthouse on a rocky cliff at sunset, cinematic, slow motion,
              golden hour lighting, waves crashing below"
3. Verfügbare Länge, Format und Kosten in der aktuellen Oberfläche prüfen
4. Generieren → Video herunterladen (.mp4)
5. Verlängern: "Extend" → neues Ende-Frame nutzen
```

### 1b. Luma Dream Machine ☁️ (lumaresearch.ai/dream-machine)

```
1. Prompt eingeben (Englisch, detailliert)
2. Falls angeboten, Stil/Modell passend zum Ziel auswählen
3. Optional: Referenz-Bild nur mit geklärten Rechten hochladen
4. Generieren → Ergebnis prüfen und herunterladen
```

Die verfügbaren Modelle und Steuerungsmöglichkeiten ändern sich. Mit demselben
unkritischen Testprompt mehrere Dienste vergleichen, bevor Produktionsdaten hochgeladen werden.

### 1c. Pika Labs ☁️ (pika.art)

```
1. pika.art → Prompt eingeben
2. Optionale Parameter:
   - Aspect Ratio: 16:9 / 9:16 / 1:1
   - Camera: static / pan / zoom / rotate
   - Motion strength: 1–10
3. Generieren → herunterladen
```

Vor dem Render die aktuell unterstützten Seitenverhältnisse und Motion Controls prüfen.

### 1d. Kling AI ☁️ (klingai.com)

```
1. klingai.com → "AI Video" → Text-to-Video
2. Prompt in einer aktuell unterstützten Sprache eingeben
3. Verfügbare Dauer, Modell und Kamera-Steuerung auswählen
4. Generieren → herunterladen
```

Mit einem unkritischen Testclip prüfen, ob Bewegungs- und Charakterkonsistenz für
das konkrete Projekt ausreichen.

---

## 2. Image-to-Video

Aus einem Standbild ein kurzes Video generieren (Bewegung hinzufügen).

### Runway Image-to-Video ☁️

```
1. runwayml.com → "Generate" → "Image to Video"
2. Bild hochladen (JPG/PNG)
3. Optional: End-Frame hochladen (kontrolliert Bewegungsrichtung)
4. Bewegungs-Prompt eingeben: "slow zoom in", "parallax effect", "water rippling"
5. Motion Amount: 1–10 (1 = minimal, 10 = stark)
6. Generieren → herunterladen
```

### Luma Dream Machine Image-to-Video ☁️

```
1. Bild hochladen
2. Prompt für Bewegung eingeben
3. Optional: Key-Frame-Paar (Start + End-Bild)
4. Generieren → herunterladen
```

---

## 3. Video-Upscaling (Magnific) ☁️

AI-generiertes oder niedrig aufgelöstes Video hochskalieren.

```
1. magnific.ai → "Upscale Video"
2. Video hochladen (max. Dateigröße beachten — plan-abhängig)
3. Verfügbare Zielauflösung und Stilparameter auswählen
4. Kreativitäts-/HDR-Regler bei realem Material zunächst niedrig testen
5. Verarbeiten → Qualitäts- und Rechteprüfung → herunterladen
```

**Hinweis:** Kosten können bild-/frameabhängig sein. Vor einem langen Lauf Preis und
Testausschnitt prüfen; Entwürfe lokal oder in niedriger Auflösung halten.

---

## Outputs

| Schritt | Output | Weiterverwendung |
|---|---|---|
| Text-to-Video | `.mp4` 5–10s | B-Roll, Intro/Outro, Standalone |
| Image-to-Video | `.mp4` 3–10s | Animiertes Produktbild, Cover |
| Upscaling | `.mp4` hochaufgelöst | Finales Publishing |

---

## Prompt-Muster (Englisch)

```
[SUBJEKT] [AKTION], [UMGEBUNG], [STIL], [KAMERA], [LICHT]

Beispiele:
"Ancient library interior, dust particles floating in light beams, cinematic,
 slow dolly forward, warm afternoon light"

"Product bottle rotating slowly on white surface, studio lighting, clean,
 commercial photography style, 360 rotation"

"Mountain lake at dawn, mist rising from water, aerial shot pulling back slowly,
 golden hour, photorealistic"
```

---

## Integration mit dem Editor-Kern

Generiertes Material als B-Roll in Editor-Workflow nutzen:
```bash
# Generiertes B-Roll liegt z.B. unter projects/<name>/assets/broll_01.mp4
# In docs/USECASES.md UC3/UC6/UC8: B-Roll-Overlay via video-use einbauen
```
