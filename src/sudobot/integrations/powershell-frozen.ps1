#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SudoBot PowerShell integration — standalone executable variant.

.DESCRIPTION
    Installed by `sudobot --install` (from a PyInstaller standalone build)
    into a stable per-user location. $SudoBotExe below is baked in at
    install time and MUST be the stable SudoBot executable — never a
    PyInstaller temporary _MEI extraction path.

    When dot-sourced into a PowerShell session, this installs a global
    error trap that delegates genuine command-not-found errors to the
    stable executable. The executable itself performs fuzzy matching,
    confirmation, and execution. Session-only effect.
#>

$SudoBotExe = "@@SUDOBOT_EXE@@"

function Get-SudoBotFailedCommand {
    param(
        [Management.Automation.ErrorRecord]$ErrorRecord
    )
    $failedCmd = ""
    if ($ErrorRecord.InvocationInfo) {
        $failedCmd = $ErrorRecord.InvocationInfo.PositionCommandName
    }
    if (-not $failedCmd) {
        $msg = $ErrorRecord.Exception.Message
        if ($msg -match '["''](.+)["'']') { $failedCmd = $Matches[1] }
    }
    return $failedCmd
}

if (-not (Get-Variable -Name SudobotTrapInstalled -Scope Global -ErrorAction SilentlyContinue)) {
    Set-Variable -Name SudobotTrapInstalled -Value $true -Scope Global -Force

    trap {
        if ($Events["Error"] -and $Events["Error"].Count -gt 0) {
            continue
        }
        $failedCmd = Get-SudoBotFailedCommand -ErrorRecord $_
        if (-not $failedCmd) {
            continue
        }
        & $SudoBotExe $failedCmd
        continue
    }
}

Write-Host "SudoBot PowerShell integration loaded." -ForegroundColor Green
