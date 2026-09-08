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

- **Local-First & Zero-Egress**: Local transcription is the default. It executes locally without transmitting raw media or credentials to external SaaS APIs.
- **Sensitive Media Isolation**: Runtime media, source recordings, transcripts, frame exports, and project output are strictly contained in `projects/` and excluded from version control via `.gitignore`.
- **Credential & Secret Protection**: Real host/user/ssh paths, HuggingFace tokens, and keys must remain in `config/settings.json`, which is excluded from version control. Never commit secrets.
- **Subprocess & Path Sanitization**: Path traversal boundaries and stem containment prevent arbitrary filesystem escape. Arguments to ffmpeg, Hyperframes, video-use, and STT engines are validated.
- **Controlled Remote Compute**: If remote compute is explicitly enabled, media transfers over configured SSH targets use temporary credential files, strict job isolation, and mandatory remote cleanup on every exit path.
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

- **Local-First & Zero-Egress**: Lokale Transkription ist der Standard. Die Verarbeitung erfolgt vollständig lokal ohne unbefugte Datenübertragung oder Telemetrie.
- **Schutz sensibler Mediendaten**: Rohaufnahmen, Transkripte, Frame-Exporte und Schnittdaten verbleiben isoliert in `projects/` und sind per `.gitignore` von der Versionskontrolle ausgeschlossen.
- **Zugangsdaten & Geheimnisschutz**: Reale Hostnamen, SSH-Konfigurationen und Tokens gehören ausschließlich in `config/settings.json` und werden niemals ins Repository committet.
- **Subprozess- & Pfadvalidierung**: Pfadtraversal-Schutz und Stem-Containment verhindern Ausbrüche aus Projektverzeichnissen; Aufrufparameter für ffmpeg, Hyperframes und STT-Engines werden validiert.
- **Isoliertes Remote-Compute**: Bei aktivierter SSH-Verarbeitung werden Zugangsdaten über temporäre Dateien geführt, Jobs isoliert und bei jedem Beendigungspfad bereinigt.
- **Produktions-Gate**: Optionale Cloud-Workflows unter `production/` erfordern eine explizite Rechte-, Einverständnis- und Lizenzprüfung vor jedem Upload.

### Reaktionszeiten & SLA-Zusagen

- **Erstreaktion**: Innerhalb von 48 Stunden zur Eingangsbestätigung eingereichter Meldungen.
- **Technische Triage**: Innerhalb von 5 Werktagen mit Schweregrad-Einstufung und Bestätigung.
- **Behebung & Patches**: Zeitnahe Bereitstellung von Sicherheitsadvisories und Patches auf allen unterstützten Zweigen (`0.2.x`).
