# Third-Party Licenses / Drittanbieter-Lizenzen

Stand: 2026-09-11 | Version: 0.2.1 | Repository: [ellmos-ai/ai-media-editor](https://github.com/ellmos-ai/ai-media-editor)

This document provides a comprehensive audit and inventory of third-party open-source components, runtimes, and libraries utilized or integrated by `ai-media-editor`.

---

## Architecture & Governance Commitments

1. **100% Permissive Open-Source & Dynamic-Link Transparency**:
   All runtime and test dependencies are distributed under permissive open-source licenses (MIT, Apache-2.0, BSD, PSFL) or dynamically linked media utilities (FFmpeg LGPL). There are zero proprietary runtime locks or closed-source binary blobs.

2. **100% Local-First & Zero Network Egress (`INV-LOCAL-01`)**:
   Every media preparation step, audio transcription, frame sampling, cut evaluation, and procedural waveform synthesis runs strictly offline on the user's workstation. No audio, video, transcript content, or telemetry is ever transmitted to external SaaS platforms.

3. **Unprivileged User-Mode Non-Elevation (`INV-RUNAS-02`)**:
   All scripts, utilities, and subprocesses run under standard unprivileged user accounts (`RunAsInvoker`). Zero administrative or root elevation is requested or permitted.

4. **Fail-Closed Evidence Admission**:
   All external tools (FFmpeg, Node.js, Python virtual environments) are validated through strict preflight probes (`editor.py doctor`). Stale outputs or broken subprocess chains fail closed without corrupting source media.

---

## Component & Dependency Inventory

| Component / Dependency | License | Upstream URL | Ecosystem Role & Usage |
|:-----------------------|:--------|:-------------|:-----------------------|
| **Python Standard Library** | PSFL-2.0 | https://www.python.org | Base runtime, file orchestration, subprocess management, JSON schemas |
| **video-use** | MIT | https://github.com/browser-use/video-use | Word-level transcript-based video cutting engine and Scribe consumer |
| **Hyperframes** | Apache-2.0 | https://github.com/heygen-com/hyperframes | HTML/CSS/JavaScript to MP4 motion graphics and visual titling renderer |
| **faster-whisper** | MIT | https://github.com/SYSTRAN/faster-whisper | Fast local speech-to-text inference engine powered by CTranslate2 |
| **WhisperX** | BSD-2-Clause | https://github.com/m-bain/whisperX | Forced acoustic alignment and phoneme-level speaker diarization |
| **NumPy** | BSD-3-Clause | https://github.com/numpy/numpy | Mathematical array processing and deterministic waveform synthesis |
| **FFmpeg** | LGPL-2.1+ / GPL-2.0+ | https://ffmpeg.org | Dynamic multimedia muxing, demuxing, audio normalization, frame sampling |
| **Node.js** | MIT | https://nodejs.org | Asynchronous JavaScript runtime driving Hyperframes rendering jobs |
| **pytest** | MIT | https://github.com/pytest-dev/pytest | Automated test runner, fixture management, and contract assertions |
| **Ruff** | MIT / Apache-2.0 | https://github.com/astral-sh/ruff | Fast Python linter, import sorter, and formatting enforcement |
| **setuptools** | MIT | https://github.com/pypa/setuptools | PEP 517 / PEP 621 package build backend and distribution packaging |

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
