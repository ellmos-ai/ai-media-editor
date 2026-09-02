# Konsolenfenster-Bursts unter Windows (HyperFrames & Node-Werkzeuge)

Ticket: T-20260829-486029203 · Stand: 2026-09-02

## Symptom
Während HyperFrames-Läufen (Snapshot, Render, Frame-Worker) blitzen Dutzende Konsolenfenster
kurz auf. Funktional ist alles korrekt; die Fenster stören die Arbeit am Rechner.

## Mechanik
Ein Konsolenprogramm (`ffmpeg.exe`, `node.exe`, `cmd.exe`) bekommt beim Start ein **neues
sichtbares Konsolenfenster**, wenn der Elternprozess keine Konsole hat, an die es sich anhängen
kann, oder wenn der Spawn mit `detached`/ohne `windowsHide` läuft. Node-Werkzeuge spawnen pro
Schritt viele kurze Kinder (`npx.cmd`-Shims → `cmd.exe`, Chromium/Puppeteer, `ffmpeg` je
Segment). `child_process.spawn` setzt `windowsHide` standardmäßig **nicht**. HyperFrames 0.7.66
nutzt hier `puppeteer-core` 25.2.1; Playwright war Teil der ursprünglichen Hypothese, ist aber
nicht der Browser-Launcher dieses HyperFrames-Stands.

## Gegenmittel (reversibel, kein Eingriff in HyperFrames)
1. **Node-Preload `tools/hide-windows.cjs`** — umhüllt `spawn/spawnSync/exec/execSync/execFile/
   execFileSync/fork` und **erzwingt** `windowsHide: true` (auch gegen ein explizites `false` des
   Aufrufers; Escape-Luke ist der globale Schalter `HIDE_WINDOWS_PRELOAD_OFF=1`). Aktiv über
   `NODE_OPTIONS=--require <pfad>/hide-windows.cjs` (**Forward-Slashes** — `NODE_OPTIONS` liest
   Backslashes als Escape). Debug: `HIDE_WINDOWS_DEBUG=1` schreibt je Node-Prozess eine Zeile
   `[hide-windows] aktiv in pid …` nach stderr.
2. **Wrapper `tools/hf.cmd`** — setzt das Preload und bevorzugt ein vorhandenes reguläres
   Google Chrome aus `%ProgramW6432%`, `%PROGRAMFILES%`, `%ProgramFiles(x86)%` oder
   `%LOCALAPPDATA%`. Dazu setzt
   das Preload nur im lokalen `setlocal`-Prozessbaum HyperFrames' nativen Override
   `HYPERFRAMES_BROWSER_PATH`; eine bereits gesetzte Vorgabe gewinnt. Wird kein Chrome gefunden,
   bleibt HyperFrames' bisheriger Cache-/Downloadweg unverändert. Opt-out für den gepinnten
   `chrome-headless-shell`: vor dem Aufruf `set HF_PREFER_FULL_CHROME=0` setzen.
   Aus dem Projektordner: `tools\hf.cmd render -q high -o renders\video.mp4`,
   `tools\hf.cmd snapshot --at 5`, …
3. **`tools/hf-hidden.vbs`** — für Aufrufe ohne Terminal (Scheduled Tasks, Starter): startet
   `hf.cmd` in einer versteckten Konsole (`wscript //B //Nologo hf-hidden.vbs render …`); Kinder
   erben die versteckte Konsole. stdout ist dabei unsichtbar.

## Messung — Prozesse ≠ Fenster
`tools/count_console_windows.ps1` zählt **sichtbare** neue Fenster (EnumWindows) während einer
Messdauer; mit `-All -Log <datei>` protokolliert es jedes neue Fenster mit Klasse, Prozess und
Titel. Selbsttest: ein sichtbares `cmd /c timeout 1` wird als 1 gezählt (Klasse
`PseudoConsoleWindow` unter ConPTY-Hosts, sonst `ConsoleWindowClass`).

**Befund 2026-08-30 (ASUS-GEI, Claude-Code-Session):** In allen messbaren Kontexten — Snapshot,
Render über PowerShell/cmd, Render über Git-Bash, Python-`subprocess`-ffmpeg, Claude-Code-Tool-
Spawns — erschienen **0** sichtbare Konsolenfenster, mit und ohne Preload. Der Preload lädt
nachweislich (Debug-Zeilen in `npm-prefix.js`, `npx-cli.js`, `hyperframes.mjs`), der Render ist
damit unverändert erfolgreich. **Die Bursts sind in diesem Kontext nicht reproduzierbar** — sie
stammen also aus einem anderen Aufrufkontext (Kandidaten: Antigravity/agy-Läufe, Codex-Companion,
Playwright mit sichtbarem Browser, andere Fensterklassen). Nächster Schritt: beim nächsten
beobachteten Burst den Zähler im `-All`-Modus mitlaufen lassen und die Logzeilen ans Ticket hängen.

**Gegenbeleg 2026-08-30 (WORKSTATION-LG):** Mit `chrome-headless-shell.exe` erschien trotz
direkter Node-CLI, Python `CREATE_NO_WINDOW` und Preload genau **1** sichtbares
`PseudoConsoleWindow` (414 Samples, 23 Prozessbaum-Nachfahren). Derselbe Laufweg mit regulärem
`chrome.exe` ergab beim Render **0** sichtbare Fenster (8.153 Samples, 94 Nachfahren); Check und
Render waren erfolgreich. Die lokalen PE-Header stützen den Mechanismus: `chrome-headless-shell`
ist ein Windows-CUI-Programm (Subsystem 3), reguläres Chrome ein Windows-GUI-Programm
(Subsystem 2). `windowsHide` ändert dieses Binärmerkmal nicht.

HyperFrames unterstützt die Umschaltung bereits nativ: `HYPERFRAMES_BROWSER_PATH` wird vor dem
gepinnten Cache und auch bei `preferManagedChrome` ausgewertet. Reguläres Chrome fällt auf den
Screenshot-Capture-Pfad zurück; der optimierte BeginFrame-Pfad und die pixelgenaue
Versionsreproduzierbarkeit des gepinnten Browsers entfallen. Wer diese Eigenschaften benötigt,
setzt `HF_PREFER_FULL_CHROME=0`. Der Preload bleibt für `cmd`, `npx`, `ffmpeg` und weitere
Konsolen-Kindprozesse nötig.

## Standardweg (Windows)
HyperFrames **immer über `tools/hf.cmd`** (bzw. `hf-hidden.vbs` ohne Terminal) starten — auch
wenn der Burst in der eigenen Umgebung nicht auftritt. Der Wrapper kombiniert
`windowsHide: true` mit regulärem Full Chrome, sofern es installiert ist. Eine abschließende
0-Fenster-Abnahme für diesen Stand bleibt eine echte Sichtmessung auf WORKSTATION-LG.
