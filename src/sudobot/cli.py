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
    # When bundled as a standalone executable (PyInstaller), data files
    # live under sys._MEIPASS. Otherwise use the package directory.
    base = getattr(sys, "_MEIPASS", None)
    if base is not None:
        return os.path.join(base, "sudobot", "integrations")
    return os.path.join(os.path.dirname(__file__), "integrations")


def _get_bash_script_path() -> str:
    return os.path.join(_get_integrations_dir(), "bash.sh")


def _get_powershell_script_path() -> str:
    return os.path.join(_get_integrations_dir(), "powershell.ps1")


# --- Standalone (PyInstaller) stable install locations ---------------------
#
# A onefile executable extracts bundled files into a temporary _MEI*
# directory on every launch, so shell configs must NEVER reference paths
# inside it. For frozen builds, --install renders integration scripts with
# the stable executable path baked in and stores them persistently:
#   Linux:   ${XDG_DATA_HOME:-~/.local/share}/sudobot/
#   Windows: %LOCALAPPDATA%\SudoBot\
# Source/pip installs keep referencing the package files directly.

EXE_PLACEHOLDER = "@@SUDOBOT_EXE@@"
FROZEN_BASH_SCRIPT = "bash-frozen.sh"
FROZEN_POWERSHELL_SCRIPT = "powershell-frozen.ps1"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _stable_data_dir() -> str:
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(
            os.path.expanduser("~"), "AppData", "Local"
        )
        return os.path.join(base, "SudoBot")
    xdg = os.environ.get("XDG_DATA_HOME") or os.path.join(
        os.path.expanduser("~"), ".local", "share"
    )
    return os.path.join(xdg, "sudobot")


def _refuse_temp_path(path: str) -> str:
    """Guard: integrated script/executable paths must never live in _MEI*."""
    if "_MEI" in path:
        raise RuntimeError(
            "Refusing to register temporary PyInstaller path: " + path
        )
    return path


def _render_frozen_script(template_name: str, exe_path: str) -> str:
    template_path = os.path.join(_get_integrations_dir(), template_name)
    with open(template_path) as f:
        content = f.read()
    if EXE_PLACEHOLDER not in content:
        raise RuntimeError(
            "Integration template missing placeholder: " + template_path
        )
    return content.replace(EXE_PLACEHOLDER, exe_path)


def _install_frozen_script(template_name: str, installed_name: str) -> str:
    """Render a frozen integration script into the stable data dir.

    Returns the stable script path to register in shell configs.
    """
    exe_path = _refuse_temp_path(sys.executable)
    stable_dir = _stable_data_dir()
    os.makedirs(stable_dir, exist_ok=True)
    dest = _refuse_temp_path(os.path.join(stable_dir, installed_name))
    with open(dest, "w", newline="\n") as f:
        f.write(_render_frozen_script(template_name, exe_path))
    return dest


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
    # NOTE: $PROFILE is a PowerShell automatic variable. Python's
    # os.path.expandvars() only understands %NAME% syntax on Windows,
    # so it would return the literal string "$PROFILE" and file writes
    # would fail. Resolve the profile location natively instead:
    #   Windows PowerShell 5.1: ~/Documents/WindowsPowerShell/...
    #   PowerShell 7+:          ~/Documents/PowerShell/...
    # Prefer an edition whose profile already exists; otherwise default
    # to the 5.1 location shipped with Windows. No admin rights needed.
    documents = os.path.join(os.path.expanduser("~"), "Documents")
    candidates = [
        os.path.join(
            documents, "WindowsPowerShell", "Microsoft.PowerShell_profile.ps1"
        ),
        os.path.join(
            documents, "PowerShell", "Microsoft.PowerShell_profile.ps1"
        ),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return candidates[0]


def _install_bash() -> list[str]:
    if _is_frozen():
        bash_script = _install_frozen_script("bash-frozen.sh", FROZEN_BASH_SCRIPT)
    else:
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
    if _is_frozen():
        ps_script = _install_frozen_script(
            "powershell-frozen.ps1", FROZEN_POWERSHELL_SCRIPT
        )
    else:
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
        parent = os.path.dirname(profile_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
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


def _remove_stable_copies() -> list[str]:
    """Delete integration scripts previously rendered into the stable dir.

    Only removes the exact filenames SudoBot itself creates.
    """
    changes = []
    stable_dir = _stable_data_dir()
    for name in (FROZEN_BASH_SCRIPT, FROZEN_POWERSHELL_SCRIPT):
        path = os.path.join(stable_dir, name)
        try:
            os.remove(path)
            changes.append(f"Removed {path}")
        except FileNotFoundError:
            pass
        except OSError:
            pass
    try:
        os.rmdir(stable_dir)  # succeeds only when empty
    except OSError:
        pass
    return changes


def uninstall() -> list[str]:
    changes = []
    changes.extend(_uninstall_bash())
    changes.extend(_uninstall_powershell())
    changes.extend(_remove_stable_copies())
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


if __name__ == "__main__":
    raise SystemExit(main())
