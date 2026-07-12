<#
.SYNOPSIS
    Installs (copies) the Forever Winter MO2 game plugin into your Mod
    Organizer 2 install(s).

.DESCRIPTION
    Copies games\game_theforeverwinter.py into
    <MO2>\plugins\basic_games\games\ for every MO2 install found (or the one you
    pass via -Mo2Path). Restart MO2 afterwards.

    This does NOT install the Signature Bypass — that is a manual prerequisite
    in <game>\Windows\ForeverWinter\Binaries\Win64\. See ..\README.md.

.PARAMETER Mo2Path
    Path to a specific MO2 install (the folder containing ModOrganizer.exe).
    If omitted, the script auto-detects common locations and copies to all.

.PARAMETER Force
    Overwrite an existing copy without prompting.

.EXAMPLE
    .\install-plugin.ps1
.EXAMPLE
    .\install-plugin.ps1 -Mo2Path "C:\Modding\MO2" -Force
#>
[CmdletBinding()]
param(
    [string]$Mo2Path,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

$repoRoot   = Split-Path -Parent $PSScriptRoot
$pluginFile = Join-Path $repoRoot 'games\game_theforeverwinter.py'

if (-not (Test-Path $pluginFile)) {
    throw "Plugin file not found at: $pluginFile"
}

# --- Resolve target MO2 install(s) ---------------------------------------
$targets = @()
if ($Mo2Path) {
    $targets += $Mo2Path
} else {
    Write-Host 'Auto-detecting Mod Organizer 2 installs...' -ForegroundColor Cyan
    $candidates = @(
        'C:\Modding\MO2', 'C:\MO2', 'C:\ModOrganizer2',
        'C:\Program Files\ModOrganizer2',
        'D:\Modding\MO2', 'D:\MO2', 'D:\ModOrganizer2',
        'F:\Modding\MO2', 'F:\MO2', 'F:\ModOrganizer2'
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c 'ModOrganizer.exe')) { $targets += $c }
    }
}

if (-not $targets) {
    throw 'No MO2 install found. Pass one explicitly:  .\install-plugin.ps1 -Mo2Path "C:\path\to\MO2"'
}

# --- Copy into each target ------------------------------------------------
foreach ($mo2 in ($targets | Select-Object -Unique)) {
    $gamesDir = Join-Path $mo2 'plugins\basic_games\games'
    if (-not (Test-Path $gamesDir)) {
        Write-Warning "basic_games\games not found under $mo2 (is basic_games installed?). Skipping."
        continue
    }

    $dest = Join-Path $gamesDir 'game_theforeverwinter.py'
    if ((Test-Path $dest) -and -not $Force) {
        $ans = Read-Host "Overwrite existing plugin at`n  $dest`n[y/N]"
        if ($ans -notmatch '^(y|yes)$') { Write-Host 'Skipped.' -ForegroundColor Yellow; continue }
    }

    Copy-Item -Path $pluginFile -Destination $dest -Force
    Write-Host "Installed -> $dest" -ForegroundColor Green
}

Write-Host ''
Write-Host 'Done. Restart Mod Organizer 2, then create/open an instance for The Forever Winter.' -ForegroundColor Cyan
Write-Host 'Reminder: install the Signature Bypass into Binaries\Win64 or no pak mod will load.' -ForegroundColor Yellow
