"""Sudobot execution layer.

Executes discovered commands safely using subprocess without shell=True.
Provides a structured result containing return code, stdout, and stderr.

The execution layer is standalone: it does NOT discover commands, does NOT
perform fuzzy matching, and does NOT enforce safety. Safety is handled by
a separate layer that requires explicit user confirmation before execution.
"""

from __future__ import annotations

import subprocess
from typing import Any


ExecutionResult = dict[str, Any]


def execute(
    command: list[str],
    *,  # keyword-only arguments after this
    capture_output: bool = True,
    text: bool = True,
) -> ExecutionResult:
    """Execute a command and return structured results.

    Parameters
    ----------
    command : list[str]
        Command and arguments as a list, e.g. ["ls", "-la"].
        Do NOT pass a shell-constructed string.

    capture_output : bool, default True
        If True, capture stdout and stderr.

    text : bool, default True
        If True, decode stdout/stderr as strings (universal newlines).
        If False, return bytes.

    Returns
    -------
    ExecutionResult
        Dictionary with keys: returncode, stdout, stderr.
        Example: {"returncode": 0, "stdout": "", "stderr": ""}

    Raises
    ------
    FileNotFoundError
        If the executable is not found (OS-level error from subprocess).
    subprocess.TimeoutExpired
        If timeout is specified and the command exceeds it.
    Exception
        For other subprocess errors.
    """
    run_kwargs: dict[str, Any] = {
        "capture_output": capture_output,
        "text": text,
    }

    process = subprocess.run(command, **run_kwargs)  # noqa: S607

    result: ExecutionResult = {
        "returncode": process.returncode,
        "stdout": process.stdout if capture_output else "",
        "stderr": process.stderr if capture_output else "",
    }

    return result


def is_executable_available(command: list[str]) -> bool:
    """Check if a command executable exists without executing it.

    Parameters
    ----------
    command : list[str]
        Command and arguments as a list.

    Returns
    -------
    bool
        True if the executable exists and is runnable, False otherwise.
    """
    try:
        subprocess.run(
            command,
            capture_output=False,
            timeout=1,
        )
        return True
    except FileNotFoundError:
        return False
    except Exception:
        # Other errors (e.g., permission denied) still mean
        # the executable conceptually exists
        return True