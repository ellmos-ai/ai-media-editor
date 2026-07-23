# synthesize_local_tts.ps1 - lokale Text-zu-Sprache ueber Windows SAPI (System.Speech), kein Cloud-Dienst.
# Null-Kosten-Default fuer UC6/UC7-Inputs (Erklaervideo/Cover aus Text): kein Konto, kein API-Key,
# keine Upload-Gates. Stimme ist eine generische Microsoft-Systemstimme (kein Voice-Cloning,
# kein Consent-Thema). Fuer hoehere Stimmqualitaet siehe die Cloud-Optionen in diesem Ordner.
# Verfuegbare Stimmen anzeigen:
#   powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }"
#
# Aufruf:
#   powershell -File synthesize_local_tts.ps1 -Text "..." -OutFile "out.wav" [-Voice "Microsoft Hedda Desktop"] [-RateWpm 0]

param(
    [string]$Text,
    [string]$TextFile,
    [Parameter(Mandatory=$true)][string]$OutFile,
    [string]$Voice = "Microsoft Hedda Desktop",
    [int]$Rate = 0
)

if ($TextFile) { $Text = Get-Content -Raw -Encoding UTF8 $TextFile }
if (-not $Text) { throw "Weder -Text noch -TextFile angegeben." }

Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice($Voice)
$synth.Rate = $Rate
$synth.SetOutputToWaveFile($OutFile)
$synth.Speak($Text)
$synth.Dispose()

Write-Output "Geschrieben: $OutFile"
