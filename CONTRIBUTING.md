# Contributing

Contributions are welcome when they keep the repository local-first, portable,
and safe for private media.

## Before opening a pull request

1. Do not commit source media, transcripts, frame exports, real
   `config/settings.json`, tokens, hostnames, SSH keys, model caches, or venvs.
2. Keep heavy tools and environments outside synchronized repository folders.
3. Add a regression test for behavior changes. Tests must not require network,
   SSH, cloud accounts, real media, or model downloads.
4. Run:

   ```bash
   python -m unittest discover -s tests -v
   ruff check .
   python editor.py modes
   ```

5. Document any remaining manual integration check explicitly. A mocked unit
   test is not proof that ffmpeg, STT models, SSH, or a provider is live.

## Security and privacy

Use private vulnerability reporting as described in [`SECURITY.md`](SECURITY.md).
For cloud-production documentation, preserve the rights, consent,
confidentiality, retention, and commercial-license gates in
[`production/OVERVIEW.md`](production/OVERVIEW.md).

## Style

- Python 3.11+ syntax, standard library first, subprocess arguments as lists.
- Quote every value that must cross a remote shell boundary.
- Treat cache validity and generated-file provenance as explicit contracts.
- Keep user-facing README content in English; German agent/workflow guides may
  remain German when that is the clearest operational source.
