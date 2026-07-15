# Story-Produktion — optionaler Skill

> Dieser Ordner ist ein portabler Pointer auf den Unterbereich `storys/` eines
> separat installierten, vertrauenswürdig bezogenen `textproduction`-Skills.

Er kann narrative Texte wie Skripte, Kurzgeschichten, RPG-Abenteuer,
Charakterbögen und Weltenbau abdecken. Bildgenerierung ist optional; dafür gelten
die Rechte-, Einwilligungs- und Cloud-Gates aus [`../OVERVIEW.md`](../OVERVIEW.md).

## Presence-Check

```python
import os
from pathlib import Path

skill_root = Path(os.environ["TEXT_PRODUCTION_SKILL"])
workflow = skill_root / "storys" / "WORKFLOW.md"
if not workflow.is_file():
    raise SystemExit("textproduction/storys ist nicht installiert")
print(workflow)
```

Setze `TEXT_PRODUCTION_SKILL` auf `<SKILLS_ROOT>/textproduction`. Installation und
Aktivierung erfolgen über die dokumentierte Methode deiner Agent-Runtime; dieses
Repository führt kein automatisches Skill-Deployment aus.
