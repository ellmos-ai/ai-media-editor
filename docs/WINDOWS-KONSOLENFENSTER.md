# Konsolenfenster-Bursts unter Windows (HyperFrames & Node-Werkzeuge)

Ticket: T-20260829-486029203 · Stand: 2026-08-30

## Symptom
Während HyperFrames-Läufen (Snapshot, Render, Frame-Worker) blitzen Dutzende Konsolenfenster
kurz auf. Funktional ist alles korrekt; die Fenster stören die Arbeit am Rechner.

## Mechanik
Ein Konsolenprogramm (`ffmpeg.exe`, `node.exe`, `cmd.exe`) bekommt beim Start ein **neues
sichtbares Konsolenfenster**, wenn der Elternprozess keine Konsole hat, an die es sich anhängen
kann, oder wenn der Spawn mit `detached`/ohne `windowsHide` läuft. Node-Werkzeuge spawnen pro
Schritt viele kurze Kinder (`npx.cmd`-Shims → `cmd.exe`, Chromium/Playwright, `ffmpeg` je
Segment). `child_process.spawn` setzt `windowsHide` standardmäßig **nicht**; HyperFrames selbst
enthält kein `windowsHide` (0 Treffer im Paket).

## Gegenmittel (beide reversibel, kein Eingriff in HyperFrames)
1. **Node-Preload `tools/hide-windows.cjs`** — umhüllt `spawn/spawnSync/exec/execSync/execFile/
   execFileSync/fork` und **erzwingt** `windowsHide: true` (auch gegen ein explizites `false` des
   Aufrufers; Escape-Luke ist der globale Schalter `HIDE_WINDOWS_PRELOAD_OFF=1`). Aktiv über
   `NODE_OPTIONS=--require <pfad>/hide-windows.cjs` (**Forward-Slashes** — `NODE_OPTIONS` liest
   Backslashes als Escape). Debug: `HIDE_WINDOWS_DEBUG=1` schreibt je Node-Prozess eine Zeile
   `[hide-windows] aktiv in pid …` nach stderr.
2. **Wrapper `tools/hf.cmd`** — setzt das Preload und ruft `npx hyperframes %*` auf. Aus dem
   Projektordner: `tools\hf.cmd render -q high -o renders\video.mp4`, `tools\hf.cmd snapshot --at 5`, …
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

## Standardweg (Windows)
HyperFrames **immer über `tools/hf.cmd`** (bzw. `hf-hidden.vbs` ohne Terminal) starten — auch
wenn der Burst in der eigenen Umgebung nicht auftritt. Das Preload kostet nichts und deckt den
bekannten Mechanismus ab.
