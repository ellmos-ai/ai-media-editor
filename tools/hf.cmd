@echo off
REM hf.cmd - HyperFrames ohne Konsolenfenster-Bursts (Windows). Ticket T-20260829-486029203.
REM Nutzung: tools\hf.cmd render --quality high --output renders\video.mp4
REM          tools\hf.cmd snapshot --at 5   /   tools\hf.cmd check   /   tools\hf.cmd lint
REM Setzt NODE_OPTIONS auf das Preload hide-windows.cjs (erzwingt windowsHide fuer alle Kindprozesse)
REM und bevorzugt regulaeres Chrome. Opt-out: set HF_PREFER_FULL_CHROME=0
REM Ruft npx hyperframes mit allen Argumenten auf. Aus dem HyperFrames-Projektordner aufrufen.
setlocal
set "HF_PRELOAD=%~dp0hide-windows.cjs"
if not defined HF_PREFER_FULL_CHROME set "HF_PREFER_FULL_CHROME=1"
REM NODE_OPTIONS liest Backslashes als Escape - deshalb Forward-Slashes.
set "HF_PRELOAD=%HF_PRELOAD:\=/%"
if defined NODE_OPTIONS (
  set "NODE_OPTIONS=%NODE_OPTIONS% --require "%HF_PRELOAD%""
) else (
  set "NODE_OPTIONS=--require "%HF_PRELOAD%""
)
call npx hyperframes %*
endlocal
