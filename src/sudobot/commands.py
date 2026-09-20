"""Sudobot command discovery module."""

import os
import sys


def discover_commands() -> list[str]:
    """
    Discover available commands from the user's PATH.

    Returns a sorted list of unique command names found in PATH.
    Works on both Windows and Linux/POSIX systems.
    """
    if sys.platform == "win32":
        commands = _discover_windows_commands()
    else:
        commands = _discover_unix_commands()

    # Remove duplicates while preserving order, then sort for determinism
    seen = set()
    unique = []
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            unique.append(cmd)
    return sorted(unique)


def _get_path_dirs() -> list[str]:
    """Get PATH directories, tolerating nonexistent entries."""
    path_str = os.environ.get("PATH", "")
    path_dirs = path_str.split(os.pathsep)
    return [d for d in path_dirs if d]  # Filter empty strings


def _discover_unix_commands() -> list[str]:
    """Discover commands on POSIX/Linux via PATH."""
    commands = []
    path_dirs = _get_path_dirs()
    for pdir in path_dirs:
        if not os.path.isdir(pdir):
            continue  # Skip nonexistent directories
        try:
            for fname in os.listdir(pdir):
                fpath = os.path.join(pdir, fname)
                # Check if file is executable (has execute permission)
                if os.access(fpath, os.X_OK):
                    # Use the filename without extension as the command name
                    cmd_name = _extract_command_name(fname, is_windows=False)
                    if cmd_name:
                        commands.append(cmd_name)
        except (PermissionError, OSError):
            continue  # Tolerate access errors
    return commands


def _discover_windows_commands() -> list[str]:
    """Discover commands on Windows via PATH and PATHEXT."""
    commands = []
    path_dirs = _get_path_dirs()
    pathext = os.environ.get(
        "PATHEXT", ".EXE;.COM;.BAT;.CMD"
    ).lower()
    ext_list = [
        e.strip(".").lower() for e in pathext.split(";") if e
    ]

    for pdir in path_dirs:
        if not os.path.isdir(pdir):
            continue  # Skip nonexistent directories
        try:
            for fname in os.listdir(pdir):
                fpath = os.path.join(pdir, fname)
                if not os.path.isfile(fpath):
                    continue
                # Check executable extensions
                _, ext = os.path.splitext(fname)
                if ext.lower()[1:] in ext_list:  # ext includes the dot
                    cmd_name = _extract_command_name(fname, is_windows=True)
                    if cmd_name:
                        commands.append(cmd_name)
        except (PermissionError, OSError):
            continue  # Tolerate access errors
    return commands


def _extract_command_name(fname: str, is_windows: bool) -> str | None:
    """Extract the command name from a filename."""
    # Remove executable extensions on Windows
    if is_windows:
        _, ext = os.path.splitext(fname)
        name = fname[:-len(ext)] if ext else fname
    else:
        name = fname
    # Skip empty names or names that start with a dot (hidden files)
    if not name or name.startswith("."):
        return None
    return name