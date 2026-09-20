# SudoBot

Offline-first CLI typo correction utility. When you mistype a command,
SudoBot suggests the intended command and asks for confirmation before
executing it.

## What it does

SudoBot hooks into your shell via `command_not_found_handle` (Bash) or
a PowerShell error trap. When you type a command that doesn't exist,
SudoBot uses fuzzy matching to suggest a correction. If you confirm,
the corrected command runs with your original arguments preserved.

```bash
$ pyhton3 --version
SudoBot: Did you mean `python3`? [y/N]
y
Python 3.13.0
```

## Supported shells/platforms

- **Bash** (Linux, macOS, Git Bash on Windows) — tested
- **PowerShell** (Windows) — integration logic implemented, not fully E2E verified

## Installation

```bash
pip install sudobot
sudobot --install
```

`sudobot --install` adds small, identifiable blocks to your shell
configuration files:

- **Bash**: adds `source <path>/bash.sh` to `~/.bashrc`
- **PowerShell**: adds `. <path>/powershell.ps1` to `$PROFILE`

No admin/root privileges are required. No daemon is created.
No unrelated files are modified.

## Uninstallation

```bash
sudobot --uninstall
```

Removes only SudoBot's own integration blocks from shell configuration
files. Does not destroy unrelated user configuration.

## CLI usage

```bash
sudobot --version       # Show version
sudobot --install       # Install shell integration
sudobot --uninstall     # Remove shell integration
sudobot <command>       # Correct a typo manually
```

When called directly with a command, SudoBot uses the fuzzy matcher
to find corrections, asks for confirmation, and executes if confirmed.

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pytest tests/ -q
```

## Security model

- No `shell=True` in subprocess execution
- No `eval` or unsafe command parsing
- Explicit user confirmation required before execution
- Arguments preserved exactly; only the executable name is replaced
- No background processes, daemons, or network calls
- No cloud, AI, or ML functionality

## Precision-first philosophy

SudoBot prioritizes precision over recall. It only suggests corrections
when confident. The matcher uses conservative thresholds and recognizes
transpositions, substitutions, and single-character insertions/deletions.

## Known limitations

- **Bash integration**: tested and working in Linux/Docker. Git Bash
  on Windows is supported but not fully E2E verified in this environment.
- **PowerShell integration**: logic implemented, but not fully E2E verified.
- **Shell config**: `sudobot --install` appends to `.bashrc`/`.bash_profile`
  and `$PROFILE`. On non-standard shell configs, manual configuration may
  be needed.
- **Installer paths**: The `--install` command uses the installed package
  location. If you move the package, the integration paths may need
  updating.
