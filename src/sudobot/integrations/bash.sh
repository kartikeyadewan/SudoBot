#!/usr/bin/env bash
#
# SudoBot Bash integration
# When sourced into a Bash session, this script defines command_not_found_handle()
# which automatically invokes SudoBot after a genuine command-not-found event.
#
# Activation:
#   source src/sudobot/integrations/bash.sh
#
# This affects only the current shell session. No permanent modifications.

# -- BUG 1 FIX: Derive repo root from BASH_SOURCE[0] ------------

# bash.sh is at SudoBot/src/sudobot/integrations/bash.sh.
# Going up three levels from the script reaches the repo root SudoBot.
if [ -z "${SUDOBOT_REPO_ROOT:-}" ]; then
    SCRIPT_PATH="${BASH_SOURCE[0]}"
    SCRIPT_PATH="$(cd "$(dirname "$SCRIPT_PATH")" 2>/dev/null && pwd)/$(basename "$SCRIPT_PATH" 2>/dev/null)"
    # Three dirname levels from SCRIPT_PATH reaches SudoBot:
    # integrations/ -> sudobot/ -> SudoBot/src -> SudoBot
    REPO_ROOT="$(cd "$SCRIPT_PATH/../../.." 2>/dev/null && pwd)"
    if [ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT" ]; then
        SUDOBOT_REPO_ROOT="$REPO_ROOT"
    fi
fi

# Set PYTHONPATH so the Python subprocess can find sudobot modules.
# We prioritize the src layout from the derived repo root.
if [ -n "$SUDOBOT_REPO_ROOT" ] && [ -d "$SUDOBOT_REPO_ROOT/src" ]; then
    export PYTHONPATH="$SUDOBOT_REPO_ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
fi

# -- BUG 2 FIX: Use python3 executable ---------------------------

# Prefer python3; fall back to python if python3 is unavailable.
_PYTHON_EXEC="python3"
if ! command -v "$_PYTHON_EXEC" >/dev/null 2>&1; then
    _PYTHON_EXEC="python"
fi

# Allow override via environment for flexibility (e.g. custom venv).
if [ -n "${SUDOBOT_PYTHON_EXEC:-}" ]; then
    _PYTHON_EXEC="$SUDOBOT_PYTHON_EXEC"
fi

# -- BUG 3 & 4 FIX: command_not_found_handle ---------------------

# This function is invoked automatically by Bash when a command
# is not found. It is the core of the SudoBot integration.
#
# $1 - the command name that could not be found
# $2..$n - the command's arguments (preserved from original)
command_not_found_handle() {
    local failed_cmd="$1"
    shift

    # Protect against empty input
    if [ -z "$failed_cmd" ]; then
        # Still let Bash report its own "command not found"
        return 0
    fi

    # BUG 3 FIX: Capture Python exit status IMMEDIATELY after substitution.
# We capture the exit status right after the command substitution,
# before any other command can overwrite $?.
# The available commands list is passed from bash.sh; if empty/unbound,
# the Python side (handle_command_not_found) will call discover_commands()
# from commands.py to build the list automatically.
local python_exit_status
local python_output
python_output=$(
    "$_PYTHON_EXEC" -c "
import sys, json
sys.path.insert(0, '$PYTHONPATH')
from sudobot.integrations.bash import handle_command_not_found

result = handle_command_not_found(
    '$failed_cmd',
    require_confirmation=True
)
print(json.dumps(result))
" )

    # Capture exit status immediately - before any other command
    python_exit_status=$?

    # BUG 4 FIX: Report errors, don't hide them during development.
    # We check exit status first, then output validity.
    if [ "$python_exit_status" -ne 0 ]; then
        # Preserve stderr for debugging - do NOT redirect to /dev/null
        echo "SudoBot: Python subprocess exited with status $python_exit_status" >&2
        # Also report if output is empty
        if [ -z "$python_output" ]; then
            echo "SudoBot: No stdout from Python integration" >&2
        fi
        # Fall back to silent behavior per core product requirement
        return 0
    fi

    # If output is empty despite success, that's also an issue
    if [ -z "$python_output" ]; then
        echo "SudoBot: Empty output from Python integration" >&2
        return 0
    fi

    # Parse the JSON result from Python using Python itself
    local parse_result
    parse_result=$(python3 -c "
import sys, json
try:
    d = json.loads(sys.argv[1])
    print(d.get('action', 'no_suggestion'))
    print(d.get('suggested_command', ''))
    print(d.get('confirmed', ''))
except Exception as e:
    print('no_suggestion')
    print('')
    print('')
" "$python_output" 2>&1)

    local action suggested_cmd confirmed
    action=$(echo "$parse_result" | head -1 2>/dev/null || echo "no_suggestion")
    suggested_cmd=$(echo "$parse_result" | sed -n '2p' 2>/dev/null || echo "")
    confirmed=$(echo "$parse_result" | sed -n '3p' 2>/dev/null || echo "")

    # --- If there is a confident suggestion, present it ---

    if [ "$action" = "suggested" ] && [ -n "$suggested_cmd" ]; then
        # Display the SudoBot suggestion
        # This appears AFTER Bash's "command not found" message
        echo "SudoBot: Did you mean \`$suggested_cmd\`? [y/N]"

        # Read user input from stdin (normal read, not <&1)
        local user_input
        read -r user_input

        # Determine confirmation using the safety layer logic
        # confirm_action returns True only for y or yes (case-insensitive)
        local confirmed=false
        local uc
        uc=$(echo "$user_input" | tr '[:upper:]' '[:lower:]' | tr -d '[:space:]')
        if [ "$uc" = "y" ] || [ "$uc" = "yes" ]; then
            confirmed=true
        fi

        # If user confirmed, execute the corrected command
        if [ "$confirmed" = "true" ]; then
            # Pass suggested_cmd and original arguments as positional argv elements to Python
            local exec_exit_status
            local exec_output
            exec_output=$(
                "$_PYTHON_EXEC" -c '
import sys, json
try:
    _tty = open("/dev/tty", "w")
except Exception:
    _tty = sys.stdout
sys.path.insert(0, "'"${PYTHONPATH}"'")
from sudobot.executor import execute
argv = [sys.argv[1]] + list(sys.argv[2:])
result = execute(argv)
_tty.write(result.get("stdout", ""))
_tty.write(result.get("stderr", ""))
_tty.flush()
print(json.dumps({"exit_code": result["returncode"]}))
' "$suggested_cmd" "$@" 2>/dev/null
            )

            # Capture exit status immediately
            exec_exit_status=$?

            if [ "$exec_exit_status" -ne 0 ]; then
                echo "SudoBot: Executor exited with status $exec_exit_status" >&2
            fi

            # Return control to Bash
            return 0
            else
                return 0
            fi
    else
        return 0
    fi
}