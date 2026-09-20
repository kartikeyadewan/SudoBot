"""Sudobot Bash integration - minimal prototype.

When Bash's command_not_found_handle is defined (by sourcing bash.sh),
this module provides the integration logic that SudoBot uses to suggest
and potentially execute corrected commands.

The core function is handle_command_not_found(), which the bash.sh
activation script calls after Bash reports a command was not found.
"""

from __future__ import annotations

import sys
from typing import Any

ExecutionResult = dict[str, Any]


def handle_command_not_found(
    failed_command: str,
    *,
    available_commands: list[str] | None = None,
    require_confirmation: bool = True,
) -> dict[str, Any]:
    """Handle a Bash command-not-found event.

    This is the main entry point for the Bash integration.
    It should be called from command_not_found_handle after Bash
    reports a command was not found.

    Parameters
    ----------
    failed_command : str
        The exact command string that Bash could not find.
    available_commands : list[str] or None
        Commands actually available on the system. If None, the
        function uses a minimal default set. The Bash handler may
        supply a richer list from PATH.
    require_confirmation : bool, default True
        If True, ask the user for confirmation before executing
        the corrected command.

    Returns
    -------
    dict
        Keys: suggested_command, confirmed, executed, exit_code,
        action. See module docstring for details.
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

    if available_commands is None:
        from sudobot.commands import discover_commands
        available_commands = discover_commands()

    if not available_commands:
        return {
            "suggested_command": None,
            "confirmed": None,
            "executed": False,
            "exit_code": None,
            "action": "no_suggestion",
        }

    # Step 1: Use matcher to find confident corrections
    from sudobot.matcher import match_command

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
    # The original arguments are preserved; only argv[0] changes.
    # This function only returns the suggested command; the Bash handler
    # is responsible for constructing the corrected argv with preserved args.

    # Step 5: Confirmation step
    confirmed = None
    executed = False
    exit_code = None
    action = "suggested"  # default when we have a suggestion

    if require_confirmation:
        # In the Bash flow, the handler will determine confirmation
        # by reading user input and calling confirm_action().
        # For this function's return value, we set confirmed=None
        # to indicate the Bash handler should prompt the user.
        confirmed = None
        action = "suggested"
    else:
        # Auto-execute mode
        from sudobot.executor import execute

        try:
            # Execute just the suggested command (no args preserved in this simple path)
            result: ExecutionResult = execute([suggested_command])
            confirmed = True
            executed = True
            exit_code = result["returncode"]
            action = "executed"
        except (FileNotFoundError, OSError):
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