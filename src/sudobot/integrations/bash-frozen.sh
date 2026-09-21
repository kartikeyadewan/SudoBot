#!/usr/bin/env bash
#
# SudoBot Bash integration — standalone executable variant.
#
# Installed by `sudobot --install` (from a PyInstaller standalone build)
# into a stable per-user location. SUDOBOT_EXE below is baked in at install
# time and MUST be the stable SudoBot executable — never a PyInstaller
# temporary _MEI extraction path.
#
# When sourced into a Bash session, this defines command_not_found_handle(),
# which delegates to the stable executable. The executable itself performs
# fuzzy matching, confirmation, and execution. Session-only effect.

SUDOBOT_EXE="@@SUDOBOT_EXE@@"

command_not_found_handle() {
    local failed_cmd="$1"
    if [ $# -gt 0 ]; then
        shift
    fi
    if [ -z "$failed_cmd" ]; then
        return 0
    fi
    "$SUDOBOT_EXE" "$failed_cmd" "$@"
    return 0
}
