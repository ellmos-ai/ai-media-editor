# Security Policy / Sicherheitsrichtlinie

[English](#english) | [Deutsch](#deutsch)

---

<a name="english"></a>
## English

### Supported Versions

| Version | Supported | Notes |
|---------|-----------|-------|
| `0.2.x` | :white_check_mark: | Active development & hardening branch |
| `< 0.2` | :x: | Legacy releases -- please upgrade |

### Reporting a Vulnerability

If you discover a potential security vulnerability in `ai-media-editor`, please report it responsibly:

1. **Do not open a public issue.**
2. **Preferred Method**: Use GitHub Private Vulnerability Reporting via
   [Security Advisories](https://github.com/ellmos-ai/ai-media-editor/security/advisories) → *New draft security advisory*.
3. **Alternative Method**: Contact the maintainers directly via email:
   - `security@open-bricks.org` (Umbrella organization security contact)
   - `security@ellmos.ai`
   - `support@lukasgeiger.com`
   - `lukas@open-bricks.org`

Include detailed reproduction steps, environment details (OS, Python version, tool versions), affected workflows, and an impact assessment.

### Security Guarantees & Scope

`ai-media-editor` is a local-first media preparation and editing orchestrator. The main security surface is local file handling, generated project files, configuration, and subprocess calls to external media tools:

- **Local-First & Remote Routing**: Local STT is the default, but model loading is not forced offline. With `compute.prefer=mac`, the full input media file copy is sent to the configured SSH host; any configured HF token is also transferred.
- **Sensitive Media Handling**: `prepare` leaves the original input at its chosen path and copies it under `projects/<name>/`. Temporary audio may use the OS temp directory. Remote mode stores a working copy under the configured SSH `workdir`; cleanup is attempted in a `finally` block, but success is not verified.
- **Credential & Secret Protection**: Real host/user/ssh paths, HuggingFace tokens, and keys must remain in `config/settings.json`, which is excluded from version control. Never commit secrets.
- **Subprocess & Path Handling**: Project names and transcript stems are validated in specific code paths; these checks are not a filesystem sandbox and do not prevent every possible filesystem escape.
- **Controlled Remote Compute**: If `compute.prefer=mac` is selected, the full input media file copy is sent by SCP to the configured SSH host. Any configured HF token is also sent in a temporary file. The isolated remote job directory is cleaned up in a `finally` block on a best-effort basis; success is not verified.
- **Production Cloud Gate**: Optional `production/` cloud workflows require explicit rights, consent, confidentiality, and licensing clearance before any material is uploaded.

### Response Time & SLA Commitments

- **Initial Response**: Within 48 hours for acknowledgment of submitted vulnerability reports.
- **Technical Triage**: Within 5 business days with vulnerability confirmation and severity rating.
- **Remediation & Patching**: Prompt security advisory and patch release on all supported versions (`0.2.x`).

---

<a name="deutsch"></a>
## Deutsch

### Unterstützte Versionen

| Version | Unterstützt | Anmerkungen |
|---------|-------------|-------------|
| `0.2.x` | :white_check_mark: | Aktiver Entwicklungs- und Härtungszweig |
| `< 0.2` | :x: | Veraltet -- bitte aktualisieren |

### Sicherheitslücken melden

Wenn Sie eine Sicherheitslücke in `ai-media-editor` entdecken, melden Sie diese bitte verantwortungsvoll:

1. **Erstellen Sie kein öffentliches GitHub-Issue.**
2. **Bevorzugter Weg**: Nutzen Sie die private Sicherheitsberatung auf GitHub via
   [Security Advisories](https://github.com/ellmos-ai/ai-media-editor/security/advisories) → *New draft security advisory*.
3. **Alternativer Weg**: Kontaktieren Sie uns direkt per E-Mail:
   - `security@open-bricks.org` (Sicherheitskontakt der Dachorganisation)
   - `security@ellmos.ai`
   - `support@lukasgeiger.com`
   - `lukas@open-bricks.org`

Bitte geben Sie eine genaue Problembeschreibung, Reproduktionsschritte, Betriebssystem-/Python-Version und das erwartete Sicherheitsrisiko an.

### Sicherheitsgarantien & Geltungsbereich

`ai-media-editor` ist ein lokaler Orchestrator für die Medienvorbereitung und den agentengesteuerten Schnitt:

- **Local-First & Remote-Routing**: Lokales STT ist der Standard, aber der Code erzwingt keinen Offline-Modus beim Laden der Modelle. Bei `compute.prefer=mac` wird die vollständige Kopie der Eingabemedien-Datei an den konfigurierten SSH-Host gesendet; jeder konfigurierte HF-Token wird ebenfalls übertragen.
- **Umgang mit sensiblen Mediendaten**: `prepare` lässt die Originaldatei an ihrem Eingabepfad und kopiert sie nach `projects/<name>/`. Temporäres Audio kann im OS-Tempverzeichnis liegen. Im Remote-Modus liegt eine Arbeitskopie im konfigurierten SSH-`workdir`; die Bereinigung wird im `finally`-Block versucht, aber ihr Erfolg nicht geprüft.
- **Zugangsdaten & Geheimnisschutz**: Reale Hostnamen, SSH-Konfigurationen und Tokens gehören ausschließlich in `config/settings.json` und werden niemals ins Repository committet.
- **Subprozess- & Pfadbehandlung**: Projektnamen und Transkript-Stems werden in bestimmten Codepfaden validiert; diese Prüfungen bilden keine Dateisystem-Sandbox und verhindern nicht jede mögliche Umgehung von Dateisystemgrenzen.
- **Remote-Compute**: Bei `compute.prefer=mac` wird die vollständige Kopie der Eingabemedien-Datei per SCP an den konfigurierten SSH-Host gesendet. Jeder konfigurierte HF-Token wird ebenfalls in einer temporären Datei übertragen. Das isolierte Remote-Arbeitsverzeichnis wird im `finally`-Block best-effort bereinigt; der Erfolg wird nicht geprüft.
- **Produktions-Gate**: Optionale Cloud-Workflows unter `production/` erfordern eine explizite Rechte-, Einverständnis- und Lizenzprüfung vor jedem Upload.

### Reaktionszeiten & SLA-Zusagen

- **Erstreaktion**: Innerhalb von 48 Stunden zur Eingangsbestätigung eingereichter Meldungen.
- **Technische Triage**: Innerhalb von 5 Werktagen mit Schweregrad-Einstufung und Bestätigung.
- **Behebung & Patches**: Zeitnahe Bereitstellung von Sicherheitsadvisories und Patches auf allen unterstützten Zweigen (`0.2.x`).
