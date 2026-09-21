"""Tests for the stable standalone install path.

Frozen (PyInstaller onefile) builds extract bundled files into a temporary
_MEI* directory on every launch. Shell configs must therefore never
reference _MEI paths. These tests simulate frozen execution and verify that
--install renders integration scripts with the stable executable baked in.
"""

import os
import sys

import pytest

from sudobot import cli


@pytest.fixture()
def sandbox_home(tmp_path, monkeypatch):
    """Redirect all home/config locations into a temp dir."""
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    monkeypatch.setenv("XDG_DATA_HOME", str(home / ".local" / "share"))
    monkeypatch.setenv("LOCALAPPDATA", str(home / "AppData" / "Local"))
    # Keep any relative-path writes (e.g. the literal $PROFILE fallback)
    # inside temp space instead of the repo checkout.
    monkeypatch.chdir(tmp_path)
    return home


@pytest.fixture()
def fake_frozen(monkeypatch, tmp_path):
    """Simulate a frozen onefile executable at a stable path."""
    fake_mei = tmp_path / "_MEI12345"
    fake_mei.mkdir()
    real_integrations = os.path.join(
        os.path.dirname(cli.__file__), "integrations"
    )
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(fake_mei), raising=False)
    monkeypatch.setattr(
        cli, "_get_integrations_dir", lambda: real_integrations
    )
    monkeypatch.setattr(
        sys, "executable", str(tmp_path / "sudobot"), raising=False
    )
    yield tmp_path
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.delattr(sys, "_MEIPASS", raising=False)


def test_frozen_install_uses_stable_paths(sandbox_home, fake_frozen, monkeypatch):
    """Frozen --install must register stable paths, never _MEI paths."""
    monkeypatch.setattr(sys, "platform", "linux")
    changes = cli.install()
    assert changes

    stable_dir = os.path.join(
        str(sandbox_home), ".local", "share", "sudobot"
    )
    for name in ("bash-frozen.sh", "powershell-frozen.ps1"):
        path = os.path.join(stable_dir, name)
        assert os.path.exists(path)
        with open(path) as f:
            content = f.read()
        assert cli.EXE_PLACEHOLDER not in content
        assert str(fake_frozen / "sudobot") in content
        # No executable path baked into the script may point at _MEI;
        # comment text mentioning _MEI is fine.
        for line in content.splitlines():
            if "SUDOBOT_EXE" in line or "SudoBotExe" in line:
                assert "_MEI" not in line

    for cfg in (".bashrc", ".bash_profile", ".profile"):
        with open(sandbox_home / cfg) as f:
            cfg_content = f.read()
        assert "_MEI" not in cfg_content
        assert stable_dir in cfg_content


def test_frozen_install_windows_location(sandbox_home, fake_frozen, monkeypatch):
    """Frozen --install on Windows uses %LOCALAPPDATA%\\SudoBot."""
    monkeypatch.setattr(sys, "platform", "win32")
    cli.install()
    expected = (
        sandbox_home / "AppData" / "Local" / "SudoBot" / "powershell-frozen.ps1"
    )
    assert expected.exists()
    text = expected.read_text()
    assert cli.EXE_PLACEHOLDER not in text
    for line in text.splitlines():
        if "SudoBotExe" in line:
            assert "_MEI" not in line


def test_frozen_uninstall_removes_stable_copies(
    sandbox_home, fake_frozen, monkeypatch
):
    """Uninstall removes rendered copies and config blocks."""
    monkeypatch.setattr(sys, "platform", "linux")
    cli.install()
    changes = cli.uninstall()
    assert changes

    stable_dir = os.path.join(
        str(sandbox_home), ".local", "share", "sudobot"
    )
    assert not os.path.exists(stable_dir)
    for cfg in (".bashrc", ".bash_profile", ".profile"):
        with open(sandbox_home / cfg) as f:
            assert "# SudoBot bash integration" not in f.read()


def test_temp_paths_are_refused():
    """Any path containing _MEI must be rejected for registration."""
    with pytest.raises(RuntimeError):
        cli._refuse_temp_path("/tmp/_MEI12345/sudobot/integrations/bash.sh")


def test_source_install_unchanged(sandbox_home, monkeypatch):
    """Non-frozen installs keep referencing the package files directly."""
    monkeypatch.delattr(sys, "frozen", raising=False)
    monkeypatch.setattr(sys, "platform", "linux")
    cli.install()
    with open(sandbox_home / ".bashrc") as f:
        content = f.read()
    assert os.path.join(os.path.dirname(cli.__file__), "integrations") in content
    assert "bash-frozen.sh" not in content
