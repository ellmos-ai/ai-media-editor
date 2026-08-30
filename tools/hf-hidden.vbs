' hf-hidden.vbs - startet hf.cmd in einer VERSTECKTEN Konsole (fuer Aufrufe ohne Terminal,
' z. B. Scheduled Tasks oder GUI-Starter). Kinder erben die versteckte Konsole.
' Nutzung: wscript //B //Nologo hf-hidden.vbs render --output renders\video.mp4
' Hinweis: stdout ist dabei unsichtbar - fuer interaktive Laeufe hf.cmd direkt nutzen.
Option Explicit
Dim sh, fso, cmdPath, args, i
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
cmdPath = fso.BuildPath(fso.GetParentFolderName(WScript.ScriptFullName), "hf.cmd")
args = ""
For i = 0 To WScript.Arguments.Count - 1
  args = args & " """ & WScript.Arguments(i) & """"
Next
sh.Run """" & cmdPath & """" & args, 0, True
