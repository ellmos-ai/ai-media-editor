# PR-Produktion — optionaler Skill

> Dieser Ordner ist ein portabler Pointer auf den Unterbereich `pr/` eines separat
> installierten, vertrauenswürdig bezogenen `textproduction`-Skills.

Der optionale Bereich kann Pressemitteilungen, Positionspapiere, Pitch Decks,
Social-Media-Kits sowie lokale LaTeX-PDF-Werkzeuge und Templates enthalten. Die
konkreten Dateien gehören zum Skill und sind nicht Teil dieses Repositories.

## Presence-Check

```python
import os
from pathlib import Path

skill_root = Path(os.environ["TEXT_PRODUCTION_SKILL"])
workflow = skill_root / "pr" / "WORKFLOW.md"
if not workflow.is_file():
    raise SystemExit("textproduction/pr ist nicht installiert")
print(workflow)
```

Setze `TEXT_PRODUCTION_SKILL` auf `<SKILLS_ROOT>/textproduction`. Installation und
Aktivierung erfolgen über die dokumentierte Methode deiner Agent-Runtime; dieses
Repository führt kein automatisches Skill-Deployment aus.

Vor Veröffentlichung Namen, Fakten, Zitate, Bildrechte, Marken, Impressumsdaten,
Empfängerlisten und Freigabestatus prüfen. Für Cloud-basierte Deck-/Design-Tools
gilt zusätzlich das Gate aus [`../OVERVIEW.md`](../OVERVIEW.md).
