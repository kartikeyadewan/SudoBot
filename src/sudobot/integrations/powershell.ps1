#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SudoBot PowerShell integration - automatic command-not-found handler.

.DESCRIPTION
    When dot-sourced into a PowerShell session, this script registers a
    session-global command-lookup hook via
    $ExecutionContext.InvokeCommand.CommandNotFoundAction. A `trap` block
    is NOT used because profile-scope traps do not intercept interactive
    CommandNotFoundException errors in Windows PowerShell 5.1.

    The hook fires ONLY when command lookup fails, so valid commands
    (even with nonzero exit codes), syntax errors, permission errors, and
    other runtime failures never invoke SudoBot. The full typed invocation
    (command name plus all arguments) is forwarded to SudoBot's shared CLI
    correction path (match, confirm, execute). Session-only effect.

    This is a development/test integration mechanism. It does not require
    administrator privileges.
#>

function Get-SudoBotArgv {
    param(
        [string]$CommandName,
        [string]$CommandLine
    )
    # Resolve the full argv for a failed invocation.
    # Returns @($CommandName) when the line is unavailable or unparseable.
    # Engine verb-probe lookups (e.g. `get-<name>`) are detected via the
    # line's first token and skipped by returning $null.
    $argv = @($CommandName)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) {
        # No line to inspect: assume an engine verb-probe (`get-<name>`)
        # rather than a genuine typed command, and skip it so the user
        # never sees noise for the probe. A genuinely typed `get-*`
        # command in an interactive session always has a CommandLine.
        if ($CommandName -like 'get-*') { return $null }
        return $argv
    }
    $parseErrors = $null
    $tokens = [System.Management.Automation.PSParser]::Tokenize(
        $CommandLine, [ref]$parseErrors
    )
    if ($null -eq $tokens -or $tokens.Count -eq 0) { return $argv }
    $first = $tokens | Where-Object { $_.Type -eq 'Command' } | Select-Object -First 1
    if ($null -eq $first) { return $argv }
    if ($first.Content -ne $CommandName) { return $null }
    $take = $false
    foreach ($token in $tokens) {
        if (-not $take) {
            if ($token.Type -eq 'Command' -and $token.Content -eq $CommandName) {
                $take = $true
            }
            continue
        }
        if ($token.Type -in @('CommandArgument', 'CommandParameter', 'String', 'Number')) {
            $argv += $token.Content
        }
    }
    return $argv
}

function Get-SudoBotCommandLine {
    param($EventArgs)
    # Best-effort full command line: the event property first (populated
    # for interactive sessions), then session history as a fallback.
    $line = $EventArgs.CommandLine
    if ([string]::IsNullOrWhiteSpace($line)) {
        try { $line = (Get-History -Count 1).CommandLine } catch {}
    }
    return $line
}

# (Re)register the session-global command-not-found handler.
$ExecutionContext.InvokeCommand.CommandNotFoundAction = {
    param($failedCommand, $eventArgs)
    try {
        $line = Get-SudoBotCommandLine -EventArgs $eventArgs
        $argv = Get-SudoBotArgv -CommandName $failedCommand -CommandLine $line
        if ($null -eq $argv) { return }
        # @() re-wrap: a single-element result arrives as a scalar, and
        # splatting a scalar with @ would pass it character-by-character.
        $argv = @($argv)
        if ($argv.Count -eq 0) { return }
        $eventArgs.StopSearch = $true
        $cliArgs = @($argv[0]) + @($argv | Select-Object -Skip 1)
        # Out-Host: native output emitted inside the lookup handler is
        # otherwise swallowed instead of reaching the console.
        & python -c "
import sys
sys.path.insert(0, r'.\src')
from sudobot.cli import _correct_command
sys.exit(_correct_command(sys.argv[1], sys.argv[2:]))
" @cliArgs | Out-Host
    } catch {}
}

Write-Host "SudoBot PowerShell integration loaded." -ForegroundColor Green
Write-Host "Type a command that doesn't exist to test SudoBot." -ForegroundColor DarkGray
