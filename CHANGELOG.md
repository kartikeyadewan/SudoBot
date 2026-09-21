# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] — 2026-09-21

### Fixed

- **PowerShell command-not-found interception** — replaced the
  ineffective profile-scope `trap` block with the session-global
  `$ExecutionContext.InvokeCommand.CommandNotFoundAction` lookup hook,
  which is the mechanism that actually intercepts interactive
  `CommandNotFoundException` errors in Windows PowerShell 5.1.
- **Full argument preservation** — the failed invocation is tokenized
  and the complete argv (command plus all arguments) is forwarded, so
  `pyhton --version` corrects to `python --version`.
- **Native output handling** — corrected-command stdout/stderr is shown
  to the user instead of being swallowed.
- **CLI dispatch** — a leading positional command now takes precedence
  over flag parsing, so target-command flags are never mistaken for
  SudoBot's own options.

No other behavioral changes. Versions bumped to 0.1.2 across the Python
package and distro packaging metadata.

## [0.1.1] — 2026-09-21

### Fixed

- **Windows standalone EXE PowerShell installer** — `sudobot --install`
  no longer passes the literal string `$PROFILE` to Python (which Python
  cannot expand and which failed with `PermissionError`). The installer
  now resolves the current user's real PowerShell profile natively
  (`~/Documents/WindowsPowerShell/...`, preferring an existing
  PowerShell 7 profile when present) and creates the profile directory
  if needed, so normal non-admin installation works.

No other behavioral changes. Versions bumped to 0.1.1 across the Python
package and distro packaging metadata.

## [0.1.0] — 2026-09-20

### Release Candidate / Initial Public Release Candidate

#### Added

- **Dynamic command discovery** via `sudobot.commands.discover_commands()` scanning PATH
- **Conservative fuzzy matching** using RapidFuzz with configurable confidence thresholds
- **Transposition detection** — recognizes swapped adjacent characters (e.g. `pyhton` → `python`)
- **Substitution detection** — recognizes single-character substitutions (e.g. `pythun` → `python`)
- **Single-character insertion detection** — recognizes added characters (e.g. `pythonn` → `python`)
- **Single-character deletion detection** — recognizes removed characters (e.g. `lss` → `ls`)
- **Safe argv-based execution** via `sudobot.executor.execute()` without `shell=True`
- **Explicit y/N confirmation** via `sudobot.safety.confirm_action()` before any execution
- **Argument preservation** — only the executable name is replaced; original arguments preserved
- **Bash integration** — `command_not_found_handle` via `src/sudobot/integrations/bash.sh`
- **PowerShell integration** — error trap via `src/sudobot/integrations/powershell.ps1`
- **CLI install/uninstall** — `sudobot --install`, `sudobot --uninstall`, `sudobot --version`, `sudobot --help`
- **Python packaging** — `pyproject.toml` with setuptools build backend, `src/` layout
- **DEB packaging** — `packaging/debian/` with control, copyright, and rules files
- **RPM packaging** — `packaging/rpm/sudobot.spec`
- **Arch packaging** — `packaging/arch/PKGBUILD` and `packaging/arch/sudobot.install`

#### Test Status

- **81/81 tests passing**
- Matcher tests: 47/47 passing
- Commands tests: 10/10 passing
- Executor tests: 3/3 passing
- PowerShell integration tests: 17/17 passing
- Safety tests: 3/3 passing

#### Build Status

- `python -m build` succeeds
- Wheel (`sudobot-0.1.0-py3-none-any.whl`) built
- Source distribution (`sudobot-0.1.0.tar.gz`) built
- No deprecation warnings

#### Known Limitations

- **Linux E2E** has not been verified in the current environment
- **PowerShell interactive shell interception** has not been fully verified
- **Native package builds** (DEB, RPM, Arch) have not yet been tested on target distro environments
- `sudobot --install` uses installed package location; moving the package may require path updates
- Non-standard shell configs may require manual integration configuration

#### What Is NOT Published Yet

- PyPI: package prepared, not yet published
- Debian: package definition prepared, not yet published
- RPM: package definition prepared, not yet published
- Arch: PKGBUILD prepared, not yet published

## Roadmap

- Publish to PyPI
- Publish to Debian, Fedora, Arch
- E2E verification on Linux Docker
- PowerShell interactive shell interception verification
- Native package build testing on target distros

## Contributing

See README.md for development setup and contribution guidelines.
