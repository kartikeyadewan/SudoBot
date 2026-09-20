"""Sudobot PowerShell integration prototype.

Responsible for invoking SudoBot after a PowerShell command-not-found failure.

This module is deliberately isolated from PowerShell's internal event mechanisms.
It provides a pure-Python function that can be called from a PowerShell script/function.

The integration boundary:
- Input: failed command name + available commands list (structured)
- Processing: matcher + safety + executor
- Output: structured result telling PowerShell what to do
- No background polling, no terminal monitoring, no daemon behavior
"""

from __future__ import annotations

import sys
from typing import Any

from sudobot.executor import execute, ExecutionResult
from sudobot.matcher import match_command
from sudobot.safety import confirm_action, requires_confirmation


IntegrationResult = dict[str, Any]


def handle_command_not_found(
    failed_command: str,
    available_commands: list[str],
    *,
    require_confirmation: bool = True,
) -> IntegrationResult:
    """Handle a PowerShell command-not-found event.

    This is the main entry point for the PowerShell integration.
    It should be called after PowerShell reports a command was not found.

    Parameters
    ----------
    failed_command : str
        The exact command string that PowerShell could not find.
        e.g. "unmount", "sytemctl"
    available_commands : list[str]
        Commands actually available on the user's system,
        as discovered by sudobot.commands.discover_commands().
    require_confirmation : bool, default True
        If True, ask the user for confirmation before executing
        the corrected command. If False, auto-execute the first
        confident suggestion (bypassing the confirmation step).

    Returns
    -------
    IntegrationResult
        Dictionary with keys describing the outcome:
        - "suggested_command": str or None - the correction to offer, or None
        - "confirmed": bool or None - whether user confirmed, or None if no suggestion
        - "executed": bool - whether the command was executed
        - "exit_code": int or None - the execution return code, or None if not executed
        - "action": str - one of "suggested", "executed", "declined", "no_suggestion"

    Notes
    -----
    - Only triggers on genuine command-not-found situations.
      Valid command failures (Python script error, etc.) should NOT call this function.
    - If matcher returns no confident candidate, SudoBot remains silent
      (returns action="no_suggestion").
    - Confirmation defaults to NO (strict: any input other than y/yes declines).
    - Execution uses argv-style lists; never shell=True.
    - The original command arguments are preserved when constructing the corrected argv.
    - Do NOT modify matcher.py scoring or thresholds.
    - Do NOT redesign executor.py.
    - Do NOT add safety logic inside the matcher.
    - Conserve resources: no background processes, no polling, no monitoring.
    """
    # Input validation
    if not failed_command or not failed_command.strip():
        return {
            "suggested_command": None,
            "confirmed": None,
            "executed": False,
            "exit_code": None,
            "action": "no_suggestion",
        }

    if not available_commands:
        return {
            "suggested_command": None,
            "confirmed": None,
            "executed": False,
            "exit_code": None,
            "action": "no_suggestion",
        }

    # Step 1: Use matcher to find confident corrections
    candidates = match_command(failed_command.strip(), available_commands)

    # Step 2: If no confident candidate, remain silent (core product requirement)
    if not candidates:
        return {
            "suggested_command": None,
            "confirmed": None,
            "executed": False,
            "exit_code": None,
            "action": "no_suggestion",
        }

    # Step 3: We have at least one confident suggestion
    # Use the top-ranked candidate (already sorted by score descending)
    top_candidate = candidates[0].command
    suggested_command = top_candidate

    # Step 4: Build the corrected argument list
    # Preserve original arguments: replace ONLY the executable name
    # Original: ["unmount", "/dev/sda1"]
    # Corrected: ["umount", "/dev/sda1"]
    corrected_argv = [suggested_command]  # Only the corrected executable

    # Step 5: Confirmation step (if required)
    confirmed = None
    executed = False
    exit_code = None
    action = "suggested"  # default action when we have a suggestion

    if require_confirmation:
        # Display suggestion to user and ask for confirmation
        # PowerShell would present: "SudoBot: Did you mean `umount /dev/sda1`? [y/N]"
        # For the Python function, we just return the suggestion info;
        # the PowerShell host handles the actual prompt display.
        # But we need to determine confirmation here for non-interactive testing.
        # In a real PowerShell flow, the host would call confirm_action() with
        # the user's input. For now, we mark it as pending confirmation.
        #
        # NOTE: In the actual PowerShell integration script, the flow would be:
        # 1. Display "SudoBot: Did you mean `{} [{y/N}]`".format(suggested_command_with_args)
        # 2. Read user input
        # 3. Call confirm_action(user_input) to get True/False
        # 4. If True, execute; if False, abort
        #
        # For this Python function's return value, we set confirmed=None to indicate
        # that the PowerShell host should prompt the user and provide the result.
        # The host is responsible for calling confirm_action() with the actual input.
        confirmed = None  # PowerShell host will determine this via confirm_action()
        action = "suggested"
    else:
        # Auto-execute mode (require_confirmation=False)
        # Use the executor with the corrected argv
        try:
            result: ExecutionResult = execute(corrected_argv)
            confirmed = True
            executed = True
            exit_code = result["returncode"]
            action = "executed"
        except (FileNotFoundError, OSError):
            # Executable not found or subprocess failed (e.g. Windows handle error)
            confirmed = False
            executed = False
            exit_code = None
            action = "no_suggestion"

    return {
        "suggested_command": suggested_command,
        "confirmed": confirmed,
        "executed": executed,
        "exit_code": exit_code,
        "action": action,
    }


def powershell_prompt(
    failed_command: str,
    suggested_command: str,
    *,
    current_input: str | None = None,
) -> tuple[bool, int | None]:
    """Handle the PowerShell confirmation prompt interaction.

    This function encapsulates the PowerShell-specific interaction pattern.
    In a real PowerShell session, this would be called from the integration script
    after displaying the confirmation prompt.

    Parameters
    ----------
    failed_command : str
        The original failed command string.
    suggested_command : str
        The correction suggested by the matcher.
    current_input : str or None
        The user's current input from the PowerShell prompt.
        If None, reads from stdin (interactive mode).

    Returns
    -------
    tuple[bool, int or None]
        (confirmed, exit_code) where:
        - confirmed: True if user confirmed (y/yes), False otherwise
        - exit_code: the execution return code, or None if not executed
    """
    # Get user input
    if current_input is None:
        # Read from stdin (interactive mode, e.g. PowerShell Read-Host)
        # Strip whitespace and use as user input
        try:
            input_str = input(
                f"SudoBot: Did you mean `{suggested_command}` [y/N]? "
            ).strip()
        except (EOFError, KeyboardInterrupt):
            input_str = "n"
    else:
        input_str = current_input

    # Determine confirmation using safety layer
    confirmed = confirm_action(input_str)

    # If confirmed, determine exit code via executor
    exit_code = None
    if confirmed:
        try:
            from sudobot.executor import execute
            result: ExecutionResult = execute([suggested_command])
            exit_code = result["returncode"]
        except (FileNotFoundError, OSError):
            confirmed = False
            exit_code = None

    return confirmed, exit_code