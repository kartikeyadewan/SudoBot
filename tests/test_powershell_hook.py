"""Regression tests for the PowerShell command-not-found integration.

The hook uses $ExecutionContext.InvokeCommand.CommandNotFoundAction because
profile-scope `trap` blocks do not intercept interactive
CommandNotFoundException errors in Windows PowerShell 5.1.

Content tests run on every platform. Live engine tests run only where a
Windows PowerShell 5.1 binary is available.
"""

import os
import shutil
import subprocess

import pytest

INTEGRATIONS = os.path.join(os.path.dirname(__file__), "..", "src", "sudobot", "integrations")
FROZEN_PS1 = os.path.abspath(os.path.join(INTEGRATIONS, "powershell-frozen.ps1"))
SOURCE_PS1 = os.path.abspath(os.path.join(INTEGRATIONS, "powershell.ps1"))

_PWSH_CANDIDATES = [
    r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
    shutil.which("powershell"),
    shutil.which("pwsh"),
]


def _powershell_exe():
    for candidate in _PWSH_CANDIDATES:
        if candidate and os.path.exists(candidate):
            return candidate
    return None


POWERSHELL = _powershell_exe()
needs_powershell = pytest.mark.skipif(
    POWERSHELL is None, reason="Windows PowerShell not available"
)


def _run_ps(snippet, timeout=120):
    result = subprocess.run(
        [POWERSHELL, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", snippet],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result


def _read(path):
    with open(path) as f:
        return f.read()


@pytest.mark.parametrize("script", [FROZEN_PS1, SOURCE_PS1])
def test_uses_command_not_found_action(script):
    """Both hooks must use the engine lookup hook, not trap."""
    content = _read(script)
    assert "CommandNotFoundAction" in content
    assert "trap {" not in content


def test_frozen_template_placeholders():
    """Frozen hook delegates to a baked-in stable exe path."""
    import re

    content = _read(FROZEN_PS1)
    assert "@@SUDOBOT_EXE@@" in content
    assert "$global:SudoBotExe" in content
    code = re.sub(r"<#.*?#>", "", content, flags=re.DOTALL)
    for line in code.splitlines():
        if line.strip().startswith("#"):
            continue
        assert "_MEI" not in line


def test_both_hooks_parse_argv_with_psparser():
    """Both hooks share the PSParser-based argv fidelity logic."""
    for script in (FROZEN_PS1, SOURCE_PS1):
        content = _read(script)
        assert "Get-SudoBotArgv" in content
        assert "PSParser" in content


@needs_powershell
def test_argv_parsing_live(tmp_path):
    """Real 5.1: name plus all arguments are extracted exactly."""
    snippet = (
        ". '%s'; " % FROZEN_PS1
        + "$a = Get-SudoBotArgv -CommandName 'pyhton' -CommandLine 'pyhton --version'; "
        + "Write-Output ('ARGC=' + $a.Count); "
        + "Write-Output ('ARG0=' + $a[0]); "
        + "Write-Output ('ARG1=' + $a[1]); "
        + "$b = Get-SudoBotArgv -CommandName 'pyhton' -CommandLine 'pyhton \"a b\" 42'; "
        + "Write-Output ('B=' + ($b -join '|'))"
    )
    result = _run_ps(snippet)
    assert "ARGC=2" in result.stdout
    assert "ARG0=pyhton" in result.stdout
    assert "ARG1=--version" in result.stdout
    assert "B=pyhton|a b|42" in result.stdout


@needs_powershell
def test_verb_probe_is_skipped_live():
    """Real 5.1: engine `get-<name>` probes must not invoke the handler."""
    snippet = (
        ". '%s'; " % FROZEN_PS1
        + "$r = Get-SudoBotArgv -CommandName 'get-pyhton' -CommandLine 'pyhton --version'; "
        + "Write-Output ('PROBE-NULL=' + ($null -eq $r))"
    )
    result = _run_ps(snippet)
    assert "PROBE-NULL=True" in result.stdout


@needs_powershell
def test_handler_invokes_exe_with_full_argv_live(tmp_path):
    """Real 5.1: invoking the registered action calls the exe with name+args."""
    log = tmp_path / "args.log"
    fake_exe = tmp_path / "fakeexe.cmd"
    fake_exe.write_text("@echo %%* >> \"%s\"\n" % log)
    # Drive the REAL engine: run a genuinely unknown command. The
    # CommandLine source is stubbed to interactive-like content because
    # non-interactive hosts leave the event property empty.
    snippet = (
        ". '%s'; " % FROZEN_PS1
        + "$global:SudoBotExe = '%s'; " % fake_exe
        + "function Get-SudoBotCommandLine { param($EventArgs) return 'pyhton_xyz_123 --version' }; "
        + "pyhton_xyz_123 --version; "
        + "Write-Output 'ENGINE-DONE'"
    )
    result = _run_ps(snippet)
    assert "ENGINE-DONE" in result.stdout
    assert "not recognized" not in result.stdout
    assert "CommandNotFoundException" not in result.stdout
    assert log.exists()
    lines = [line.strip() for line in log.read_text().splitlines()]
    # The real invocation must arrive as intact arguments; a scalar
    # splatted with @ would arrive character-by-character instead.
    assert "pyhton_xyz_123 --version" in lines
    assert "get-pyhton_xyz_123" not in log.read_text()


@needs_powershell
def test_single_element_argv_not_char_split_live(tmp_path):
    """Real 5.1: a bare-name fallback must arrive as one intact argument."""
    log = tmp_path / "args.log"
    fake_exe = tmp_path / "fakeexe.cmd"
    fake_exe.write_text("@echo %%* >> \"%s\"\n" % log)
    snippet = (
        ". '%s'; " % FROZEN_PS1
        + "$global:SudoBotExe = '%s'; " % fake_exe
        + "function Get-SudoBotCommandLine { param($EventArgs) return '' }; "
        + "pyhton_xyz_123 --version; Write-Output 'ENGINE-DONE'"
    )
    result = _run_ps(snippet)
    assert "ENGINE-DONE" in result.stdout
    assert log.exists()
    lines = [line.strip() for line in log.read_text().splitlines()]
    assert "pyhton_xyz_123" in lines


@needs_powershell
def test_probable_probe_without_line_is_skipped_live():
    """Real 5.1: `get-*` with no inspectable line is treated as a probe."""
    snippet = (
        ". '%s'; " % FROZEN_PS1
        + "$r = Get-SudoBotArgv -CommandName 'get-pyhton' -CommandLine ''; "
        + "Write-Output ('PROBE-SKIP=' + ($null -eq $r))"
    )
    result = _run_ps(snippet)
    assert "PROBE-SKIP=True" in result.stdout


@needs_powershell
def test_non_lookup_errors_do_not_fire_live():
    """Real 5.1: unrelated errors and nonzero exits stay silent."""
    snippet = (
        "$global:count = 0; "
        + "$ExecutionContext.InvokeCommand.CommandNotFoundAction = { param($n, $e) $global:count++; $e.StopSearch = $true }; "
        + "Get-Item 'NoSuchPath_xyz_123' 2>$null; "
        + "Write-Error 'boom' -ErrorAction SilentlyContinue; "
        + "Write-Output ('COUNT=' + $global:count)"
    )
    result = _run_ps(snippet)
    assert "COUNT=0" in result.stdout
