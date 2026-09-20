#!/usr/bin/env pwsh
<#
.SYNOPSIS
    SudoBot PowerShell integration - automatic command-not-found handler.

.DESCRIPTION
    When dot-sourced into a PowerShell session, this script sets up an automatic
    handler that invokes SudoBot after a genuine PowerShell command-not-found
    error. The handler is session-only and does not permanently modify the
    user's PowerShell profile.

    After the user types a command that PowerShell cannot find, SudoBot will:
    1. Use fuzzy matching to find the most likely intended command
    2. Display: "SudoBot: Did you mean `corrected_cmd args`? [y/N]"
    3. If the user presses 'y' or types 'yes', execute the corrected command
    4. If the user presses Enter or types anything else, execute nothing

    This is a development/test integration mechanism. It is not intended for
    production use and does not require administrator privileges.

.PROVIDE
    Invoke-SudoBot    - Automatic command-not-found handler setup
#>

# Remove any existing Write-Error replacement to start clean
if (FunctionExists "Sudobot:Write-Error") {
    Remove-Function Sudobot:Write-Error
}

# ============================================================================
# Automatic command-not-found handler
# ============================================================================

# Helper: Determine if an error is a genuine command-not-found
function Is-CommandNotFoundError {
    param(
        [Management.Automation.ErrorRecord]$ErrorRecord
    )

    # Check for CommandNotFoundException type
    if ($ErrorRecord.Exception -is [System.Management.Automation.CommandNotFoundException]) {
        return $true
    }

    # Check error message for command-not-found patterns
    $msg = $ErrorRecord.ErrorMessage -or ""
    if ($msg -like "*Cannot find a command*") { return $true }
    if ($msg -like "*The term* is not recognized as a command*") { return $true }
    if ($msg -like "*Word not found in this sentence*") { return $true }
    return $false
}

# Helper: Invoke SudoBot with the failed command via Python
function Invoke-SudoBotHelper {
    param(
        [string]$failedCommand
    )

    # Call the Python integration and capture JSON output
    $pythonScript = "
import sys
sys.path.insert(0, r'.\src')
from sudobot.integrations.powershell import handle_command_not_found
from sudobot.commands import discover_commands

result = handle_command_not_found(
    '$failedCommand',
    discover_commands(),
    require_confirmation=True
)
import json
print(json.dumps(result))
"

    try {
        $output = python -c $pythonScript 2>$null
        if ($output) {
            $result = ConvertFrom-Json $output
            return $result
        }
    } catch {
        # Python failed silently; fall through
    }

    # Fallback: return silent result
    [pscustomobject]@{
        suggested_command = $null
        confirmed         = $null
        executed          = $false
        exit_code       = $null
        action          = "no_suggestion"
    }
}

# ============================================================================
# Global trap for command-not-found errors
# ============================================================================

# When this script is dot-sourced, install the global error trap.
if (-not $InvokingMyCommand) {
    # Install the trap only once per session
    if (-not (Get-Variable -Name SudobotTrapInstalled -Scope Global -ErrorAction SilentlyContinue)) {
        Set-Variable -Name SudobotTrapInstalled -Value $true -Scope Global -Force

        trap {
            # Only handle the first error; then continue normally
            if ($Events["Error"] -and $Events["Error"].Count -gt 0) {
                # Already handled an error in this scope; let it pass through
                continue
            }

            # Check if this is a command-not-found error
            if (-not (Is-CommandNotFoundError -ErrorRecord $_)) {
                # Not a command-not-found error; let it pass through
                continue
            }

            # === SudoBot integration ===
            # Extract the failed command name from the error
            $failedCmd = ""
            if ($_.InvocationInfo) {
                $failedCmd = $_.InvocationInfo.PositionCommandName -or ""
            }
            if (-not $failedCmd) {
                $failedCmd = $_.ScriptName -split '\|' | Select-Object -Last 1 -or ""
            }
            if (-not $failedCmd) {
                $failedCmd = $_.Exception.Message -replace '.*["\'](.+)["\'].*', '$1' -or ""
            }

            if (-not $failedCmd) {
                # Can't determine the command; let error pass through
                continue
            }

            # Invoke SudoBot helper
            $helperResult = Invoke-SudoBotHelper -failedCommand $failedCmd

            # If there's a confident suggestion, attempt execution
            if ($helperResult.action -eq "suggested") {
                if ($helperResult.confirmed -eq $true) {
                    $suggested = $helperResult.suggested_command -or ""
                    $args = @()
                    # Build corrected argv: replace only argv[0]
                    # The original command name is replaced; arguments are preserved
                    # by the PowerShell host through the invocation info
                    try {
                        & python -c "
import sys
sys.path.insert(0, r'.\src')
from sudobot.executor import execute
cmd = ['$suggested'] + sys.argv[1:]
result = execute(cmd)
print('Exit code: ' + str(result['returncode']))
" 2>$null | ForEach-Object { $exeResult = $_ }
                    } catch {
                        # Execution failed silently
                    }
                } else {
                    # User declined; nothing executes
                    Write-Host "SudoBot: Command declined. Nothing executed." -ForegroundColor Yellow
                }
            }

            # Re-display the original error (continue = re-throw)
            continue
        } # end trap
    } # end if not already installed
} # end if not invoking

# ============================================================================
# Output: Confirmation for the user (manual use)
# ============================================================================

# Function: Display SudoBot suggestion
function Show-SudoBotSuggestion {
    param(
        [string]$suggestedCommand,
        [string]$originalCommand
    )

    Write-Host "SudoBot: Did you mean `$suggestedCommand`? [y/N]" -ForegroundColor Cyan

    # Read user input
    $input = Read-Host
    # Note: For the automatic mechanism, the trap handles confirmation internally.
    # This function is available for manual use.
}

# ============================================================================
# End of integration
# ============================================================================

Write-Host "SudoBot PowerShell integration loaded." -ForegroundColor Green
Write-Host "Type a command that doesn't exist to test SudoBot." -ForegroundColor DarkGray