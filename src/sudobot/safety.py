"""Sudobot safety layer.

Handles user confirmation before command execution.

Safety principles:
- Execution must NEVER happen automatically after fuzzy matching.
- There must be an explicit confirmation step before execution.
- Declining confirmation must execute nothing.
- Safety logic must be separate from execution logic.
- Do not implement an elaborate security framework yet.

The safety layer is standalone: it does NOT discover commands, does NOT
perform fuzzy matching, and does NOT execute commands. It only provides
confirmation decision logic.
"""

from __future__ import annotations


def confirm_action(user_input: str) -> bool:
    """Determine if the user wants to proceed with execution.

    Parameters
    ----------
    user_input : str
        Raw user input from the confirmation prompt.

    Returns
    -------
    bool
        True if the user confirmed (entered 'y' or 'yes'),
        False otherwise (including 'n', 'no', or any other input).

    Notes
    -----
    - The check is case-insensitive and strips whitespace.
    - Any input other than 'y' or 'yes' (after stripping and lowercasing)
      results in False, meaning execution does NOT proceed.
    - This is intentionally strict: the default/fallback is to NOT execute.
    """
    choice = user_input.strip().lower()
    return choice in ("y", "yes")


def requires_confirmation(command: list[str]) -> bool:
    """Determine if a command requires explicit confirmation before execution.

    Parameters
    ----------
    command : list[str]
        Command and arguments as a list.

    Returns
    -------
    bool
        True if the command should require confirmation, False otherwise.

    Notes
    -----
    - Currently, all commands require explicit confirmation.
    - In future versions, this could check for destructive commands
      (rm -rf, format, etc.) specifically.
    - The command list format preserves argument boundaries;
      do NOT reconstruct a shell string for this check.
    """
    # All commands require explicit confirmation in this phase.
    # Future versions may differentiate between safe and destructive commands.
    return True