# Third-Party Licenses / Drittanbieter-Lizenzen

Stand: 2026-11-14 (Audit-Historie: 2026-09-30, 2026-09-28, 2026-09-21, 2026-09-20, 2026-09-11) | Version: 0.3.0 (Runtime-Locks gemessen, siehe „Runtime Lock Inventory 0.3.0“) | Repository: [ellmos-ai/ai-media-editor](https://github.com/ellmos-ai/ai-media-editor)

This document provides a comprehensive Level 1 Software Bill of Materials (SBOM) and audit inventory of third-party open-source components, runtimes, and libraries utilized or integrated by `ai-media-editor`. A machine- and terminal-readable plain-text version is available at [`THIRD_PARTY_LICENSES.txt`](THIRD_PARTY_LICENSES.txt).

---

## Architecture & Governance Commitments

1. **Open-Source & Dynamic-Link Transparency** (measured 2026-11-14 for the 0.3.0 runtime locks):
   Most runtime dependencies are permissively licensed (MIT, MIT-0, MIT-CMU, ISC, 0BSD, Zlib, CC0-1.0, Apache-2.0, BSD, PSF-2.0). Weak-copyleft components (used unmodified as separate packages): `certifi` (MPL-2.0), `tqdm` (MPL-2.0 AND MIT), `soxr` (LGPL-2.1-or-later) and the FFmpeg shared libraries bundled in the PyAV (`av`) wheels (LGPL-3.0-or-later on macOS arm64). No package declares GPL, AGPL or SSPL terms. There are zero proprietary runtime locks, telemetry trackers, or closed-source binary blobs.

2. **100% Local-First & Zero Network Egress (`INV-LOCAL-01`)**:
   Every media preparation step, audio transcription, frame sampling, cut evaluation, and procedural waveform synthesis runs strictly offline on the user's workstation. No audio, video, transcript content, or telemetry is ever transmitted to external SaaS platforms.

3. **Unprivileged User-Mode Non-Elevation (`INV-RUNAS-02`)**:
   All scripts, utilities, and subprocesses run under standard unprivileged user accounts (`RunAsInvoker`). Zero administrative or root elevation is requested, permitted, or required.

4. **Fail-Closed Evidence Admission (`INV-PREV-03`)**:
   All external tools (FFmpeg, Node.js, Python virtual environments) are validated through strict preflight probes (`editor.py doctor`). Stale outputs or broken subprocess chains fail closed without corrupting source media.

5. **Console Window Flashing Suppression (`INV-SUBPROC-06`)**:
   Child processes spawned on Windows platforms enforce hidden window handles via preloaded wrappers (`tools/hide-windows.cjs`, `tools/hf.cmd`), eliminating visual disruptions during batch rendering.

---

## Level 1 SBOM & Governance Invariant Cross-Reference

| Component / Dependency | Version / Range | License | Governing Invariant | Isolation & Boundary Guarantee | Upstream Project URL |
|:---|:---|:---|:---|:---|:---|
| **Python Standard Library** | >=3.10 | PSFL-2.0 | `INV-LOCAL-01`, `INV-RUNAS-02` | Unprivileged local-first process orchestration | https://www.python.org |
| **video-use** | Latest clone | MIT | `INV-DETERM-04`, `INV-PREV-03` | Schema-based cutting without cloud API dependency | https://github.com/browser-use/video-use |
| **Hyperframes** | >=1.0.0 | Apache-2.0 | `INV-SUBPROC-06`, `INV-PARITY-07` | Headless rendering with console window suppression | https://github.com/heygen-com/hyperframes |
| **faster-whisper** | >=1.0.0 | MIT | `INV-LOCAL-01`, `INV-BOUNDARY-05` | 100% offline CTranslate2 local speech-to-text | https://github.com/SYSTRAN/faster-whisper |
| **WhisperX** | Optional | BSD-2-Clause | `INV-LOCAL-01`, `INV-PARITY-07` | Local forced acoustic alignment & diarization | https://github.com/m-bain/whisperX |
| **NumPy** | >=1.24.0 | BSD-3-Clause | `INV-DETERM-04`, `INV-LOCAL-01` | Seed-based deterministic waveform synthesis | https://github.com/numpy/numpy |
| **FFmpeg** | >=6.0 | LGPL-2.1+ | `INV-RUNAS-02`, `INV-PREV-03` | Dynamic unprivileged CLI subprocess invocation | https://ffmpeg.org |
| **Node.js** | >=22.0 | MIT | `INV-SUBPROC-06`, `INV-RUNAS-02` | Isolated runtime for motion graphic animation jobs | https://nodejs.org |
| **pytest / pytest-asyncio** | >=8.0.0 | MIT | `INV-PARITY-07`, `INV-DOCS-09` | Automated regression and contract test gates | https://github.com/pytest-dev/pytest |
| **Ruff** | >=0.5.0 | MIT / Apache-2.0 | `INV-DOCS-09`, `INV-PARITY-07` | Static analysis, code formatting, export linting | https://github.com/astral-sh/ruff |
| **setuptools** | >=77.0 | MIT | `INV-RUNAS-02`, `INV-DOCS-09` | Standard PEP 517 / PEP 621 packaging metadata | https://github.com/pypa/setuptools |
| **clip-storyboard-director** (`[storyboard]` extra) | Pinned commit `efd7159` | MIT | N/A (optional companion, not a runtime invariant) | Separate installable "Director" package; `ai-media-editor` runs fully without it | https://github.com/ellmos-ai/clip-storyboard-director |

---

## Runtime Lock Inventory 0.3.0 (measured)

Method: on 2026-11-14 `requirements/runtime-macos-arm64-py312.txt` was installed with `--require-hashes` into a throwaway Python 3.12 environment on macOS arm64, and the license metadata of every installed distribution was read via `importlib.metadata` (`License-Expression`, else `License`, else the trove classifier). Of `requirements/runtime-windows-x64-py312.txt`, the two pins that differ from macOS (`colorama` 0.4.6, `onnxruntime` 1.32.0) were read from their win_amd64 wheels; every other Windows pin has the same version as on macOS. ¹ = taken from the trove classifier only. This is the license declared by each package, not a legal review.

Weak-copyleft components (used unmodified as separate packages): `certifi` (MPL-2.0), `tqdm` (MPL-2.0 AND MIT), `soxr` (LGPL-2.1-or-later) and the FFmpeg shared libraries bundled in the PyAV (`av`) wheels (LGPL-3.0-or-later on macOS arm64). No package declares GPL, AGPL or SSPL terms.

| Package | macOS arm64 | Windows x64 | Declared license |
|:---|:---|:---|:---|
| `anyio` | 4.16.0 | 4.16.0 | MIT |
| `av` | 18.1.0 | 18.1.0 | BSD-3-Clause |
| `certifi` | 2026.10.23 | 2026.10.23 | MPL-2.0 |
| `cffi` | 2.1.1 | 2.1.1 | MIT-0 |
| `charset-normalizer` | 3.5.2 | 3.5.2 | MIT |
| `click` | 8.5.1 | 8.5.1 | BSD-3-Clause |
| `cloudpickle` | 3.1.2 | 3.1.2 | BSD-3-Clause |
| `colorama` | — | 0.4.6 | BSD License¹ |
| `coloredlogs` | 15.0.1 | — | MIT |
| `contourpy` | 1.4.0 | 1.4.0 | BSD-3-Clause |
| `ctranslate2` | 4.9.0 | 4.9.0 | MIT |
| `cycler` | 0.12.1 | 0.12.1 | BSD License¹ |
| `decorator` | 5.3.1 | 5.3.1 | BSD-2-Clause |
| `faster-whisper` | 1.2.1 | 1.2.1 | MIT |
| `filelock` | 4.2.10 | 4.2.10 | MIT |
| `flatbuffers` | 25.12.19 | 25.12.19 | Apache 2.0 |
| `fonttools` | 4.68.0 | 4.68.0 | MIT |
| `fsspec` | 2026.9.0 | 2026.9.0 | BSD-3-Clause |
| `h11` | 0.16.0 | 0.16.0 | MIT |
| `hf-xet` | 1.8.0 | 1.8.0 | Apache-2.0 |
| `httpcore2` | 2.16.0 | 2.16.0 | BSD-3-Clause |
| `httpx2` | 2.16.0 | 2.16.0 | BSD-3-Clause |
| `huggingface-hub` | 2.4.0 | 2.4.0 | Apache-2.0 |
| `humanfriendly` | 10.0 | — | MIT |
| `idna` | 3.20 | 3.20 | BSD-3-Clause |
| `joblib` | 1.6.0 | 1.6.0 | BSD-3-Clause |
| `kiwisolver` | 1.5.1 | 1.5.1 | BSD License¹ |
| `lazy-loader` | 0.6 | 0.6 | BSD-3-Clause |
| `librosa` | 1.0.1 | 1.0.1 | ISC |
| `llvmlite` | 0.50.0 | 0.50.0 | BSD-2-Clause AND Apache-2.0 WITH LLVM-exception |
| `matplotlib` | 3.11.2 | 3.11.2 | Python Software Foundation License¹ |
| `mpmath` | 1.3.0 | — | BSD |
| `msgpack` | 1.2.4 | 1.2.4 | Apache-2.0 |
| `narwhals` | 2.28.0 | 2.28.0 | MIT |
| `numba` | 0.68.1 | 0.68.1 | BSD |
| `numpy` | 2.5.4 | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 |
| `onnxruntime` | 1.23.2 | 1.32.0 | MIT License |
| `packaging` | 26.3 | 26.3 | Apache-2.0 OR BSD-2-Clause |
| `pillow` | 13.0.0 | 13.0.0 | MIT-CMU |
| `platformdirs` | 4.14.5 | 4.14.5 | MIT |
| `pooch` | 1.9.0 | 1.9.0 | BSD-3-Clause |
| `protobuf` | 7.36.2 | 7.36.2 | 3-Clause BSD License |
| `pycparser` | 3.12 | 3.12 | BSD-3-Clause |
| `pyparsing` | 3.3.3 | 3.3.3 | MIT |
| `python-dateutil` | 4.0.0 | 4.0.0 | BSD-3-Clause |
| `pyyaml` | 6.0.3 | 6.0.3 | MIT |
| `requests` | 2.34.2 | 2.34.2 | Apache-2.0 |
| `scikit-learn` | 1.9.1 | 1.9.1 | BSD-3-Clause |
| `scipy` | 1.18.1 | 1.18.1 | BSD License¹ |
| `soundfile` | 0.14.0 | 0.14.0 | BSD 3-Clause License |
| `soxr` | 1.1.0 | 1.1.0 | LGPL-2.1-or-later |
| `sympy` | 1.14.0 | — | BSD |
| `threadpoolctl` | 3.8.0 | 3.8.0 | BSD-3-Clause |
| `tokenizers` | 0.23.3 | 0.23.3 | Apache Software License¹ |
| `tqdm` | 4.70.1 | 4.70.1 | MPL-2.0 AND MIT |
| `truststore` | 0.10.5 | 0.10.5 | MIT |
| `typing-extensions` | 4.16.0 | 4.16.0 | PSF-2.0 |
| `tzdata` | 2026.6 | 2026.6 | Apache-2.0 |
| `urllib3` | 2.8.0 | 2.8.0 | MIT |

---

## RunAsInvoker Non-Elevation Certification

`ai-media-editor` is explicitly designed and certified to execute strictly under standard unprivileged user accounts (`RunAsInvoker`).
- **No Elevated Privileges Required**: Installation, configuration, media preparation, STT routing, frame extraction, pause detection, and media rendering require zero administrator or root privileges.
- **No System Modifications**: The tool does not install system drivers, background system-level services, registry modifications, or root certificates.
- **Strict User-Space Containment**: All generated files, temporary artifacts, and cached models reside strictly within user-specified directories (`projects/`, `<TOOLS_ROOT>/`).

---

## Copyleft Boundaries & Dynamic Linking

- **FFmpeg CLI:** `ai-media-editor` itself calls FFmpeg only as an external program across subprocess boundaries (`subprocess.run` / `subprocess.Popen`) using standard streams. Users can swap, patch, or upgrade the FFmpeg binary independently.
- **FFmpeg libraries via PyAV:** The locked runtime contains PyAV (`av`, BSD-3-Clause), which `faster-whisper` uses for audio decoding. Its wheels bundle FFmpeg shared libraries that are loaded dynamically in-process. On macOS arm64 (av 18.1.0) FFmpeg reports "LGPL version 3 or later" (`--enable-version3`, no `--enable-gpl`). The wheel also bundles further codec libraries (e.g. dav1d, opus, mp3lame, opencore-amr, SVT-AV1) whose individual licenses were not audited separately; the Windows wheel was not inspected.
- **Weak-copyleft Python packages:** `certifi` (MPL-2.0), `tqdm` (MPL-2.0 AND MIT) and `soxr` (LGPL-2.1-or-later) are installed by the user from PyPI as separate, unmodified packages; `ai-media-editor` neither vendors nor modifies them.

---

## Summary of Permissive License Texts

### MIT License
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.

### Apache License 2.0
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at `http://www.apache.org/licenses/LICENSE-2.0`. Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

### BSD Licenses (BSD-2-Clause & BSD-3-Clause)
Redistribution and use in source and binary forms, with or without modification, are permitted provided that the copyright notice, this list of conditions and the following disclaimer are reproduced in source and documentation distributions.

### Python Software Foundation License (PSFL-2.0)
Python software and documentation are licensed under the PSF License Agreement. PSF grants licensee a non-exclusive, royalty-free, worldwide license to reproduce, prepare derivative works, distribute, and display Python solely or in any derivative version thereof.

### GNU Lesser General Public License (LGPL-2.1+)
FFmpeg is dynamically invoked via CLI subprocesses and is licensed under the LGPL version 2.1 or later (or GPL depending on optional build flags). The dynamic invocation preserves user freedom to replace FFmpeg binaries without modifying `ai-media-editor`.
