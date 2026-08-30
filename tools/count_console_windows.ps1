# count_console_windows.ps1 - zaehlt SICHTBARE Fenster, die waehrend einer Messdauer neu erscheinen.
# Zweck: Abnahme "Prozesse != Fenster" fuer hide-windows.cjs / hf.cmd (Ticket T-20260829-486029203)
# und Diagnose, WELCHE Fenster bei einem "Burst" aufblitzen (Klasse, Titel, Prozess).
# Nutzung:
#   powershell -NoProfile -File count_console_windows.ps1 -Seconds 60 -Interval 40
#   powershell -NoProfile -File count_console_windows.ps1 -Seconds 120 -All -Log "$env:TEMP\fenster.log"
# Ohne -All: nur Konsolenklassen (ConsoleWindowClass, CASCADIA_HOSTING_WINDOW_CLASS).
# Mit -All: jedes neue sichtbare Top-Level-Fenster, je Fenster eine Logzeile "Zeit | Klasse | Prozess | Titel".
param([int]$Seconds = 60, [int]$Interval = 40, [switch]$All, [string]$Log = "")
Add-Type @"
using System; using System.Text; using System.Runtime.InteropServices; using System.Collections.Generic;
public static class WinEnum {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] static extern bool EnumWindows(EnumProc p, IntPtr l);
  [DllImport("user32.dll")] static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll", CharSet=CharSet.Unicode)] static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  public class W { public long H; public string C; public string T; public uint P; }
  public static List<W> Visible(bool all) {
    var r = new List<W>();
    EnumWindows((h, l) => { if (IsWindowVisible(h)) { var sb = new StringBuilder(256); GetClassName(h, sb, 256); var c = sb.ToString();
      if (all || c == "ConsoleWindowClass" || c == "CASCADIA_HOSTING_WINDOW_CLASS") {
        var tb = new StringBuilder(512); GetWindowText(h, tb, 512); uint pid; GetWindowThreadProcessId(h, out pid);
        r.Add(new W { H = (long)h, C = c, T = tb.ToString(), P = pid }); } } return true; }, IntPtr.Zero);
    return r; }
}
"@
$baseline = @{}
foreach ($w in [WinEnum]::Visible($All.IsPresent)) { $baseline[$w.H] = $true }
$seen = @{}
$end = (Get-Date).AddSeconds($Seconds)
while ((Get-Date) -lt $end) {
  foreach ($w in [WinEnum]::Visible($All.IsPresent)) {
    if (-not $baseline.ContainsKey($w.H) -and -not $seen.ContainsKey($w.H)) {
      $seen[$w.H] = $true
      $pn = try { (Get-Process -Id $w.P -ErrorAction Stop).ProcessName } catch { "?" }
      $line = ("{0} | {1} | {2} | {3}" -f (Get-Date -Format "HH:mm:ss.fff"), $w.C, $pn, $w.T)
      if ($Log) { Add-Content -Path $Log -Value $line -Encoding UTF8 }
    }
  }
  Start-Sleep -Milliseconds $Interval
}
$suffix = " (nur Konsolen)"
if ($All) { $suffix = " (alle Klassen)" }
Write-Output ("NEUE_SICHTBARE_FENSTER=" + $seen.Count + $suffix)
