# Security

## Reporting Vulnerabilities

Please do not open a public issue for security reports. Use GitHub private
vulnerability reporting:

1. Open the repository on GitHub.
2. Go to **Security**.
3. Choose **Report a vulnerability**.

If private vulnerability reporting is not available, contact the maintainer via
[github.com/lukisch](https://github.com/lukisch) with a short description,
reproduction steps, and potential impact.

## Scope

ai-media-editor is a local-first media preparation and editing helper. The main
security surface is local file handling, generated project files, configuration,
and subprocess calls to external media tools.

Local transcription is the default. If remote compute is enabled, the complete
input media is transferred to the user-configured SSH host. Optional
`production/` workflows may upload material to third-party cloud providers only
after the explicit rights, consent, confidentiality, retention, and license gate
in `production/OVERVIEW.md`.

Please report issues related to:

- accidental exposure of source media, transcripts, frame exports, or project
  output files;
- unsafe handling of `config/settings.json`, HuggingFace tokens, SSH settings,
  or local tool paths;
- remote-command injection, failed remote-job cleanup, cache confusion, or an
  unvalidated remote result replacing a valid local transcript;
- command injection or unsafe subprocess arguments around ffmpeg, Hyperframes,
  video-use, faster-whisper, or WhisperX;
- insecure defaults that could write private media into tracked repository
  paths;
- packaging, dependency metadata, or documentation that could lead users to
  commit private config or media.

Runtime media, real settings, project output, and heavy tool installations are
intentionally excluded from Git. Keep `config/settings.json`, `projects/`, media
files, internal reports, virtual environments, and tool caches out of version control.
