# Textproduktion — optionaler Skill

> Dieser Ordner ist ein portabler Pointer. Der vollständige Text-Workflow lebt in
> einem separat installierten Skill namens `textproduction`; dieses Repository
> liefert oder installiert ihn nicht automatisch.

Der Skill kann Prompt-Muster für Blogposts, Social Media, Newsletter,
Marketing-Copy, formelle E-Mails und Berichte enthalten. Prüfe Herkunft und Inhalt
des Skills, bevor du ihn in einer Agent-Runtime aktivierst.

## Presence-Check

Setze `TEXT_PRODUCTION_SKILL` auf das installierte Skill-Verzeichnis. Es muss eine
`SKILL.md` enthalten.

```powershell
$env:TEXT_PRODUCTION_SKILL = "<SKILLS_ROOT>\textproduction"
Test-Path "$env:TEXT_PRODUCTION_SKILL\SKILL.md"
```

```bash
export TEXT_PRODUCTION_SKILL="<SKILLS_ROOT>/textproduction"
test -f "$TEXT_PRODUCTION_SKILL/SKILL.md"
```

Wenn der Check fehlschlägt, installiere den Skill über den vertrauenswürdigen
Skill-Katalog bzw. die dokumentierte Deployment-Methode deiner Runtime. Niemals
einen unbekannten Skill allein aufgrund seines Namens ausführen.

## Nutzung

Lies zuerst `SKILL.md` des installierten Skills. Einstieg im Chat kann z. B.
„Schreibe einen Blogpost über …“ sein; explizite Slash-Commands sind
runtimeabhängig und werden hier nicht vorausgesetzt.

## Verwandte Workflows

- `production/storys/WORKFLOW.md` — narrative Inhalte
- `production/pr/WORKFLOW.md` — PR-Pakete
