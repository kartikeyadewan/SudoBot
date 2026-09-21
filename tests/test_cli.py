"""Tests for CLI dispatch precedence.

Flags that belong to the target invocation (e.g. `--version` in
`sudobot pyhton --version`) must travel with the mistyped command into
the correction path. Bare flags without a positional command keep their
existing behavior.
"""

import sys

import pytest

from sudobot import cli


def _run_main(monkeypatch, capsys, argv):
    monkeypatch.setattr(sys, "argv", ["sudobot"] + argv)
    code = cli.main()
    return code, capsys.readouterr().out


def test_bare_version_flag(monkeypatch, capsys):
    """`sudobot --version` still prints the SudoBot version."""
    code, out = _run_main(monkeypatch, capsys, ["--version"])
    assert code == 0
    assert out.strip() == f"sudobot {cli.__version__}"


def test_command_takes_precedence_over_version_flag(
    monkeypatch, capsys
):
    """`sudobot pyhton --version` corrects instead of printing our version."""
    import sudobot.commands

    monkeypatch.setattr(
        sudobot.commands, "discover_commands", lambda: ["python", "pip"]
    )
    monkeypatch.setattr("builtins.input", lambda: "n")
    code, out = _run_main(monkeypatch, capsys, ["pyhton", "--version"])
    assert code == 0
    assert "Did you mean `python`" in out
    assert "Command declined" in out


def test_correction_receives_all_arguments(monkeypatch, capsys):
    """Arguments after the command reach the executor unchanged."""
    import sudobot.commands
    import sudobot.executor

    seen = {}

    def fake_execute(argv):
        seen["argv"] = argv
        return {"returncode": 0, "stdout": "", "stderr": ""}

    monkeypatch.setattr(
        sudobot.commands, "discover_commands", lambda: ["python"]
    )
    monkeypatch.setattr(sudobot.executor, "execute", fake_execute)
    monkeypatch.setattr("builtins.input", lambda: "y")
    code, out = _run_main(monkeypatch, capsys, ["pyhton", "--version"])
    assert code == 0
    assert seen["argv"] == ["python", "--version"]


def test_executed_output_is_shown(monkeypatch, capsys):
    """Accepting a correction shows the executed command's output."""
    import sudobot.commands
    import sudobot.executor

    def fake_execute(argv):
        assert argv == ["python", "--version"]
        return {"returncode": 0, "stdout": "Python 3.x.y\n", "stderr": ""}

    monkeypatch.setattr(
        sudobot.commands, "discover_commands", lambda: ["python"]
    )
    monkeypatch.setattr(sudobot.executor, "execute", fake_execute)
    monkeypatch.setattr("builtins.input", lambda: "y")
    code, out = _run_main(monkeypatch, capsys, ["pyhton", "--version"])
    assert code == 0
    assert "Python 3.x.y" in out


def test_no_args_prints_help(monkeypatch, capsys):
    """Bare `sudobot` still prints help."""
    code, out = _run_main(monkeypatch, capsys, [])
    assert code == 0
    assert "usage" in out
