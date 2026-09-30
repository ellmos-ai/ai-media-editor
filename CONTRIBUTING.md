# Beitragsrichtlinie / Contributing Guide

[Deutsch](#deutsch) | [English](#english)

---

<a name="deutsch"></a>
## Deutsch

Vielen Dank für Ihr Interesse, zu `ai-media-editor` beizutragen!

### Wie Sie beitragen können

1. **Bug melden:** Erstellen Sie ein Issue mit dem Label `bug`
2. **Feature vorschlagen:** Erstellen Sie ein Issue mit dem Label `enhancement`
3. **Code beitragen:** Erstellen Sie einen Pull Request auf Branch `main`

### Pull Requests & Branch-Workflow

1. Forken Sie das Repository oder erstellen Sie einen Feature-Branch: `git checkout -b feature/mein-feature`
2. Committen Sie Ihre Änderungen: `git commit -m "Beschreibung der Änderung"`
3. Pushen Sie den Branch: `git push origin feature/mein-feature`
4. Erstellen Sie einen Pull Request

### Developer Certificate of Origin (DCO)

Dieses Projekt verwendet den [Developer Certificate of Origin (DCO)](https://developercertificate.org/).
Bitte signieren Sie jeden Commit mit `--signoff`:

```bash
git commit --signoff -m "Beschreibung der Änderung"
```

Damit bestätigen Sie, dass Sie das Recht haben, den Code unter der Projektlizenz (MIT) einzureichen.

### Code-Richtlinien & Quality Gates

Vor jedem Commit und Pull Request müssen folgende vier Quality Gates vollständig bestanden werden:

1. **`pytest`** — Die gesamte Testsuite muss zu 100% erfolgreich durchlaufen.
2. **`ruff check .`** — Keine Linting- oder Formatierungsfehler.
3. **`python -m compileall -q .`** — Saubere Bytecode-Kompilierung ohne Syntax- oder Importfehler.
4. **`git diff --check`** — Keine Whitespace- oder Zeilenende-Konflikte.

### Governance, Version Freeze & Lokale Entwicklung

- **Version-Freeze-Disziplin (T-20260920-167562623):** Die Version `0.2.3` bleibt strikt eingefroren. Keine eigenmächtigen Versionserhöhungen; alle Neuerungen und Wartungsschritte werden unter `## [Unreleased]` im `CHANGELOG.md` dokumentiert.
- **Lokale Entwicklung (Plan D):** Der kanonische Arbeitsort und die Source of Truth ist der lokale Git-Klon (`C:\_Local_DEV\repos\ai-media-editor`).
- **Datenschutz & Zero-Egress:** Committen Sie niemals Quellmedien, echte `config/settings.json`, Tokens, Hostnamen, SSH-Schlüssel, Modell-Caches oder virtuelle Umgebungen (`.venv`).
- **Unprivileged User Mode (RunAsInvoker):** Alle Skripte und Tests laufen ohne administrative Privilegien.

---

<a name="english"></a>
## English

Thank you for your interest in contributing to `ai-media-editor`!

### How to Contribute

1. **Report bugs:** Open an issue with the `bug` label
2. **Suggest features:** Open an issue with the `enhancement` label
3. **Contribute code:** Create a Pull Request against the `main` branch

### Pull Requests & Branch Workflow

1. Fork the repository or create a feature branch: `git checkout -b feature/my-feature`
2. Commit your changes: `git commit -m "Description of change"`
3. Push the branch: `git push origin feature/my-feature`
4. Open a Pull Request

### Developer Certificate of Origin (DCO)

This project uses the [Developer Certificate of Origin (DCO)](https://developercertificate.org/).
Please sign off every commit with `--signoff`:

```bash
git commit --signoff -m "Description of change"
```

This certifies that you have the right to submit the code under the project's MIT license.

### Pre-Commit Quality Gates

All contributions must strictly satisfy the following four pre-commit quality gates:

1. **`pytest`** — 100% of the regression and contract test suite must pass.
2. **`ruff check .`** — Zero linting or code formatting violations.
3. **`python -m compileall -q .`** — Clean bytecode compilation with no syntax errors.
4. **`git diff --check`** — Zero trailing whitespace or newline discrepancies.

### Governance, Version Freeze & Local Development

- **Version Freeze Policy (T-20260920-167562623):** Version `0.2.3` is strictly frozen. No unauthorized version bumps; all changes are tracked under `## [Unreleased]` in `CHANGELOG.md`.
- **Local Development (Plan D):** Canonical development occurs in the local git repository clone (`C:\_Local_DEV\repos\ai-media-editor`).
- **Privacy & Zero Network Egress:** Never commit raw media, private recordings, real `config/settings.json`, API credentials, tokens, or virtual environments (`.venv`).
- **Unprivileged User Mode (RunAsInvoker):** All code operates strictly in unprivileged user space.
