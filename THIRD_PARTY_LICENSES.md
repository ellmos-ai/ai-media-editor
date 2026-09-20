# Third-Party Licenses / Drittanbieter-Lizenzen

Stand: 2026-09-20 (Audit-Historie: 2026-09-11) | Version: 0.2.3 | Repository: [ellmos-ai/ai-media-editor](https://github.com/ellmos-ai/ai-media-editor)

This document provides a comprehensive Level 1 Software Bill of Materials (SBOM) and audit inventory of third-party open-source components, runtimes, and libraries utilized or integrated by `ai-media-editor`.

---

## Architecture & Governance Commitments

1. **100% Permissive Open-Source & Dynamic-Link Transparency**:
   All runtime and test dependencies are distributed under permissive open-source licenses (MIT, Apache-2.0, BSD, PSFL) or dynamically linked media utilities (FFmpeg LGPL). There are zero proprietary runtime locks, telemetry trackers, or closed-source binary blobs.

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

---

## RunAsInvoker Non-Elevation Certification

`ai-media-editor` is explicitly designed and certified to execute strictly under standard unprivileged user accounts (`RunAsInvoker`).
- **No Elevated Privileges Required**: Installation, configuration, media preparation, STT routing, frame extraction, pause detection, and media rendering require zero administrator or root privileges.
- **No System Modifications**: The tool does not install system drivers, background system-level services, registry modifications, or root certificates.
- **Strict User-Space Containment**: All generated files, temporary artifacts, and cached models reside strictly within user-specified directories (`projects/`, `<TOOLS_ROOT>/`).

---

## Zero-Copyleft & Dynamic Linking Isolation Boundary

All external multimedia utilities (such as FFmpeg) are accessed strictly across CLI subprocess boundaries (`subprocess.run` / `subprocess.Popen`) using standard streams. This architecture ensures complete dynamic link isolation:
- No proprietary or copyleft viral contamination affects downstream consumer code.
- Users retain the unrestricted freedom to swap, patch, or upgrade external CLI utilities independently.

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
