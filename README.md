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

The recommended way to install SudoBot is from
[GitHub Releases](https://github.com/kartikeyadewan/SudoBot/releases).
Standalone executables are currently built for **x86_64/amd64** only and
need no Python installation.

**Windows** (PowerShell):

1. Download `SudoBot-0.1.0-windows-x64.exe`.
2. Place it somewhere on your `PATH` (optionally rename it to
   `sudobot.exe`).
3. Optionally run `sudobot --install` to enable the PowerShell
   integration.

**Linux** (binary):

```bash
chmod +x sudobot-0.1.0-linux-x86_64
sudo mv sudobot-0.1.0-linux-x86_64 /usr/local/bin/sudobot
sudobot --install   # Bash integration
```

**Linux** (AppImage):

```bash
chmod +x SudoBot-0.1.0-x86_64.AppImage
./SudoBot-0.1.0-x86_64.AppImage --version
```

Verify any download with the published `SHA256SUMS` file:

```bash
sha256sum -c SHA256SUMS
```

`sudobot --install` adds small, identifiable blocks to your shell
configuration files:

- **Bash**: adds `source <path>/bash.sh` to `~/.bashrc`
- **PowerShell**: adds `. <path>/powershell.ps1` to `$PROFILE`

No admin/root privileges are required. No daemon is created.
No unrelated files are modified.

> **Note**: the standalone executables are single-file bundles. Running
> `sudobot --install` from one installs its integration scripts to a
> stable per-user location with the executable path baked in —
> `~/.local/share/sudobot/` on Linux
> (`$XDG_DATA_HOME/sudobot/` if set) and `%LOCALAPPDATA%\SudoBot\` on
> Windows — so shell configs never point at temporary extraction
> directories. `sudobot --uninstall` removes both the config blocks and
> those installed copies. If you move the executable afterwards, re-run
> `sudobot --install`.

**Optional Python installation** (requires Python 3.10+):

```bash
pip install sudobot
sudobot --install
```

> PyPI availability may vary while automated publishing is being set up.
> See [Release and Publishing](#release-and-publishing) below.

**Distro packages**: files under `packaging/debian/`, `packaging/rpm/`,
and `packaging/arch/` are packaging groundwork only. SudoBot is not
currently installable from apt, dnf, pacman, Homebrew, or similar
repositories.

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

## Release and Publishing

Releases are created by pushing a version tag (e.g. `v0.1.0`).

```bash
git tag -a v0.1.0 -m "SudoBot v0.1.0"
git push origin v0.1.0
```

When a `v*` tag is pushed, GitHub Actions automatically:

1. **Builds** the package (`python -m build`)
2. **Runs tests** (`pytest tests/ -q`)
3. **Validates** the distribution (`python -m twine check dist/*`)
4. **Publishes** to PyPI using Trusted Publishing (OIDC)

### How Trusted Publishing works

- The GitHub Actions workflow uses `pypa/gh-action-pypi-publish@release/v1`
- Authentication is via GitHub's OIDC identity token (`permissions: id-token: write`)
- No long-lived PyPI API tokens are stored as secrets
- The workflow runs in an environment named `pypi` configured on PyPI

### Prerequisites for PyPI publication

A **Trusted Publisher** must be configured on PyPI:

- **Owner**: `kartikeyadewan`
- **Repository**: `SudoBot`
- **Workflow**: `.github/workflows/publish.yml`
- **Environment**: `pypi`

This configuration is done manually on the [PyPI Trusted Publishers](https://pypi.org/manage/account/publishing/) page. Without it, the publish job will fail.

> **Important**: Publishing has NOT yet been configured or tested.
> Do not assume `pip install sudobot` works from PyPI until the
> Trusted Publisher is configured and a manual publication succeeds.

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
