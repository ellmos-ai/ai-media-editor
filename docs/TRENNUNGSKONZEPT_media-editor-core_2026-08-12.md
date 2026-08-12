# Trennungskonzept: media-editor-core aus ai-media-editor

**Datum:** 2026-08-12 · **Autor:** Operator-Analyse (Fable, ASUS-GEI)
**Status:** ANALYSE — keine physische Extraktion durch diesen Lauf
**Löst bei Umsetzung:** Baukasten-Phase-5-Rest (MODULE-BAUKASTEN-UMSETZUNGSPLAN)
**und** MAPPING-GAPS G5 (ellmos-media-stack blockiert durch fehlendes
`media-editor-core` im Katalog; Validator-Beleg vom 2026-08-12).

## Leitschnitt (aus dem Code selbst)

`editor.py` beschreibt sich als Orchestrator der **deterministischen
Vorbereitungsschritte**: Medien → Engine-/Compute-Routing → Scribe-JSON →
`pack_transcripts` → `takes_packed.md`. Die **kreative Arbeit**
(Schnitt-Entscheidungen, Animationen, Render) fährt danach ein LLM interaktiv.
Genau diese Linie ist die Modulgrenze.

## Zuordnung

| Bestandteil | Ziel | Begründung |
|---|---|---|
| `editor.py` (Orchestrator) | **media-editor-core** | deterministische Pipeline, kein LLM-Zwang |
| `stt/transcribe_local.py`, `stt/scribe_schema.py`, `stt/mac_remote.py` | **media-editor-core** | lokale/entfernte STT-Engines + Schema = Kernfähigkeit |
| `stt/diarize_llm.py` | **media-editor-core als Adapter** (Grenzfall) | Schema/Aufruf deterministisch, LLM-Provider injizierbar halten — der Kern trägt den Adapter, der Stack liefert das Modell |
| `tools/` (cut_view, frame_view, compose_cover, compose_music) | **media-editor-core** | deterministische Werkzeuge |
| `config/` | **media-editor-core** (Schema) | Werte bleiben Installationsdatum |
| `production/` (musik, podcast-tts, pr, storys, text, video-generativ) | **ellmos-media-stack** (Skills/Workflows) | kreative Usecase-Strecken, LLM-/dienstgebunden |
| `projects/` | **weder noch — Laufzeitdaten** | Baukastenregel: keine Runtime-Daten in Modulquellen; gehört in ein Arbeitsverzeichnis außerhalb der Quelle |
| `brand/`, `assets/`, App-Doku | **ai-media-editor (Produkt)** | Produktidentität bleibt bei der App |

**ai-media-editor bleibt als Produkt/App bestehen** und konsumiert den Kern —
das ist die Datenkaskaden-Regel (App = Speicherpunkt + GUI, Modul = Fähigkeit),
kein Abriss.

## Identitäten (Regel: Modulname ≠ zwingend Paketname)

- Modul-ID im Katalog: `media-editor-core` (Kategorie-Vorschlag: `domains`,
  alternativ `tools` — Entscheid beim Katalog-Eigentümer).
- Python-Paket: `media_editor_core`; Repo-Frage offen: eigenes Repo vs.
  Unterpaket im bestehenden `ellmos-ai/ai-media-editor` (Empfehlung:
  zunächst **Unterpaket + eigenes Modulmanifest**, kein Repo-Split — kleinster
  reversibler Schritt, Plan-D-konform).

## Migrationsschritte (catalog-first, move-later)

1. **Kern-Manifest anlegen** (`ellmos-module.v2`, `status: planned`) — nach
   dem mac-backup-Präzedenzfall sind planned-Module katalogfähig ohne
   Code-Pflicht. **Offene Prüffrage (nicht behauptet):** ob
   `validate_composition.py` eine `required`-Komponente mit
   `status: planned` akzeptiert — wenn nein, Stack-Seite bis zur Extraktion
   auf `optional` stellen oder Gate dokumentiert lassen.
2. `projects/`-Laufzeitdaten aus der Quelle heraus konfigurieren
   (Arbeitsverzeichnis-Default außerhalb des Repos).
3. Code-Extraktion ins Unterpaket `media_editor_core/` mit eigener
   Testabdeckung (bestehende 38 Tests zuordnen).
4. `production/`-Strecken als Stack-Skills im `ellmos-media-stack`
   komponieren; erst danach Stack-Manifest mit `required` validieren und
   registrieren.
5. Katalog neu bauen, Regression über alle Stacks, Karten nachziehen.

## Abgrenzung

Dieser Lauf hat **nichts verschoben, extrahiert oder registriert**. Die
physische Extraktion (Schritte 2–5) ist ein eigener, freigabewürdiger
Arbeitsblock im Modul-/Katalog-Eigentümerkontext.

---

## Nachtrag: Schritt 1 umgesetzt [C 2026-08-12, ~06:55]

Das `planned`-Manifest liegt im Katalog: `.MODULES/.DOMAINS/media-editor-core/`
(`ellmos-module.v2.json`, `status: planned`, `kind: service` — die Kategorie
`domains` erlaubt kein `library`, zulässig sind service/stack-candidate/
workflow), Katalog auf **52 Module** neu gebaut, Katalogtests 25/25 grün,
Regression über alle 9 registrierten Stacks grün. **Die offene
Validator-Prüffrage ist beantwortet:** `validate_composition.py` akzeptiert
`planned`-Komponenten — ein Test-Stack mit `media-editor-core` validiert OK,
sobald Sichtbarkeit (`internal`) und `max_data_sensitivity` (`sensitive`)
passen; der Status selbst ist kein Blocker. Damit reduziert sich G5 auf:
ellmos-media-stack-Entwurf ohne die nicht-existente Rolle
`media.editing.core` und mit passenden Policies materialisieren (Rollen-
einführung bleibt beim Eigentümer von `composition.rules.json`).
`provides` des Manifests bleibt bewusst leer. Schritte 2–5 (Extraktion)
weiterhin offen.
