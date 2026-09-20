"""Sudobot CLI — typo correction utility.

Supports --install, --uninstall, --version, --help, and direct command correction.
"""

from __future__ import annotations

import os
import sys
import argparse

from sudobot import __version__
from sudobot.matcher import match_command
from sudobot.integrations.bash import handle_command_not_found as bash_handle


def _get_integrations_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "integrations")


def _get_bash_script_path() -> str:
    return os.path.join(_get_integrations_dir(), "bash.sh")


def _get_powershell_script_path() -> str:
    return os.path.join(_get_integrations_dir(), "powershell.ps1")


def _read_shell_config(path: str) -> str:
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return ""


def _write_shell_config(path: str, content: str) -> None:
    with open(path, "w") as f:
        f.write(content)


def _bash_config_paths() -> list[str]:
    paths = []
    home = os.path.expanduser("~")
    for name in (".bashrc", ".bash_profile", ".profile"):
        paths.append(os.path.join(home, name))
    return paths


def _powershell_profile_path() -> str:
    return os.path.expandvars("$PROFILE")


def _install_bash() -> list[str]:
    bash_script = _get_bash_script_path()
    if not os.path.exists(bash_script):
        return ["Bash integration script not found at " + bash_script]
    changes = []
    for path in _bash_config_paths():
        content = _read_shell_config(path)
        marker = f"# SudoBot bash integration"
        source_line = f"\nsource {bash_script}\n"
        if marker in content:
            continue
        with open(path, "a") as f:
            f.write(f"\n{marker}\n{source_line}")
        changes.append(f"Added to {path}")
    if not changes:
        changes.append("Bash integration already configured")
    return changes


def _install_powershell() -> list[str]:
    ps_script = _get_powershell_script_path()
    if not os.path.exists(ps_script):
        return ["PowerShell integration script not found at " + ps_script]
    changes = []
    profile_path = _powershell_profile_path()
    content = _read_shell_config(profile_path)
    marker = "# SudoBot PowerShell integration"
    source_line = f"\n. '{ps_script}'\n"
    if marker in content:
        changes.append("PowerShell integration already configured")
    else:
        with open(profile_path, "a") as f:
            f.write(f"\n{marker}\n{source_line}")
        changes.append(f"Added to {profile_path}")
    return changes


def install() -> list[str]:
    changes = []
    changes.extend(_install_bash())
    changes.extend(_install_powershell())
    return changes


def _uninstall_bash() -> list[str]:
    changes = []
    marker = "# SudoBot bash integration"
    for path in _bash_config_paths():
        content = _read_shell_config(path)
        if marker not in content:
            continue
        lines = content.splitlines()
        new_lines = []
        skip = False
        for line in lines:
            if marker in line:
                skip = True
                continue
            if skip and line.strip() == "":
                skip = False
                continue
            if skip and line.strip().startswith("source "):
                continue
            if skip and line.strip().startswith("# SudoBot"):
                continue
            skip = False
            new_lines.append(line)
        new_content = "\n".join(new_lines).strip() + "\n"
        with open(path, "w") as f:
            f.write(new_content)
        changes.append(f"Removed from {path}")
    return changes


def _uninstall_powershell() -> list[str]:
    changes = []
    marker = "# SudoBot PowerShell integration"
    profile_path = _powershell_profile_path()
    content = _read_shell_config(profile_path)
    if marker not in content:
        return ["PowerShell integration not configured"]
    lines = content.splitlines()
    new_lines = []
    skip = False
    for line in lines:
        if marker in line:
            skip = True
            continue
        if skip and line.strip() == "":
            skip = False
            continue
        if skip and (". '" in line or ". \"" in line):
            continue
        skip = False
        new_lines.append(line)
    new_content = "\n".join(new_lines).strip() + "\n"
    with open(profile_path, "w") as f:
        f.write(new_content)
    changes.append(f"Removed from {profile_path}")
    return changes


def uninstall() -> list[str]:
    changes = []
    changes.extend(_uninstall_bash())
    changes.extend(_uninstall_powershell())
    return changes


def _correct_command(command: str, arguments: list[str]) -> int:
    from sudobot.safety import confirm_action

    available_commands = []
    try:
        from sudobot.commands import discover_commands
        available_commands = discover_commands()
    except Exception:
        pass

    candidates = match_command(command, available_commands) if available_commands else []
    if not candidates:
        print(f"SudoBot: No confident correction for: {command}")
        return 1

    suggested = candidates[0].command
    if candidates[0].command != command:
        print(f"SudoBot: Did you mean `{suggested}`? [y/N]")

    try:
        choice = input().strip().lower()
    except (EOFError, KeyboardInterrupt):
        choice = ""

    if not confirm_action(choice):
        print("SudoBot: Command declined. Nothing executed.")
        return 0

    from sudobot.executor import execute
    try:
        result = execute([suggested] + arguments)
        return result["returncode"]
    except Exception as e:
        print(f"SudoBot: Execution failed: {e}")
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="sudobot",
        description="SudoBot — offline-first CLI typo correction utility",
    )
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--install", action="store_true", help="Install shell integration")
    parser.add_argument("--uninstall", action="store_true", help="Remove shell integration")
    parser.add_argument("command", nargs="?", default=None, help="Command to correct")
    parser.add_argument("arguments", nargs="*", default=[], help="Command arguments")

    args = parser.parse_args()

    if args.version:
        print(f"sudobot {__version__}")
        return 0

    if args.install:
        changes = install()
        for change in changes:
            print(change)
        print("Installation complete.")
        return 0

    if args.uninstall:
        changes = uninstall()
        for change in changes:
            print(change)
        print("Uninstallation complete.")
        return 0

    if args.command:
        return _correct_command(args.command, args.arguments)

    parser.print_help()
    return 0
