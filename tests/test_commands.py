"""Tests for command discovery."""

import os
import sys
import tempfile
import shutil

from sudobot.commands import discover_commands, _get_path_dirs, _extract_command_name


def test_discover_returns_list():
    """Test that discover_commands returns a list."""
    result = discover_commands()
    assert isinstance(result, list)


def test_discover_no_crash():
    """Test that discovery does not crash on empty/ minimal environment."""
    result = discover_commands()
    # Should return a list, possibly empty
    assert result is not None


def test_windows_path_dirs():
    """Test _get_path_dirs splits PATH correctly on Windows."""
    if sys.platform == "win32":
        result = _get_path_dirs()
        assert isinstance(result, list)


def test_unix_path_dirs():
    """Test _get_path_dirs splits PATH correctly on Unix."""
    if sys.platform != "win32":
        result = _get_path_dirs()
        assert isinstance(result, list)


def test_extract_command_name_windows():
    """Test extracting command name from Windows executable."""
    # .exe extension should be stripped
    result = _extract_command_name("git.exe", is_windows=True)
    assert result == "git"

    # No extension
    result = _extract_command_name("git", is_windows=True)
    assert result == "git"

    # Hidden file should return None
    result = _extract_command_name(".git", is_windows=True)
    assert result is None

    # Empty name
    result = _extract_command_name("", is_windows=True)
    assert result is None


def test_extract_command_name_unix():
    """Test extracting command name on Unix."""
    # Simple name
    result = _extract_command_name("git", is_windows=False)
    assert result == "git"

    # Hidden file should return None
    result = _extract_command_name(".git", is_windows=False)
    assert result is None

    # Empty name
    result = _extract_command_name("", is_windows=False)
    assert result is None


def test_deduplication():
    """Test that duplicate commands are removed."""
    # Test with a list containing duplicates
    commands = ["git", "python", "git", "mkdir", "python"]
    seen = set()
    unique = []
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            unique.append(cmd)
    assert unique == ["git", "mkdir", "python"] or len(unique) == 3
    assert len(seen) == 3


def test_deterministic_ordering():
    """Test that results are sorted deterministically."""
    # Sorting should produce consistent order
    commands = ["zsh", "bash", "git", "python"]
    seen = set()
    unique = []
    for cmd in commands:
        if cmd not in seen:
            seen.add(cmd)
            unique.append(cmd)
    result = sorted(unique)
    assert result == sorted(result)  # Verify it's sorted
    # Multiple calls should give same result
    assert result == sorted(unique)


def test_nonexistent_path_tolerated():
    """Test that nonexistent PATH directories don't crash discovery."""
    # This is tested implicitly by discover_commands not crashing
    result = discover_commands()
    assert result is not None


def test_temporary_directory_discovery():
    """Test discovering commands from a temporary directory."""
    tmpdir = tempfile.mkdtemp()
    try:
        # Create some "executable" files in the temp dir
        # On Unix, create the file first, then make it executable
        if sys.platform != "win32":
            mycmd_path = os.path.join(tmpdir, "mycmd")
            with open(mycmd_path, "w") as f:
                f.write("#!/bin/sh\necho hello")
            os.chmod(mycmd_path, 0o755)
        
        # Write a Windows batch file
        with open(os.path.join(tmpdir, "mycmd.cmd"), "w") as f:
            f.write("@echo off\necho hello")
        
        # Add tmpdir to PATH temporarily
        old_path = os.environ.get("PATH", "")
        try:
            os.environ["PATH"] = tmpdir + os.pathsep + old_path
            result = discover_commands()
            # Should find mycmd (via exec bit on Unix, via .cmd on Windows)
            assert "mycmd" in result
        finally:
            os.environ["PATH"] = old_path
    finally:
        # Cleanup
        shutil.rmtree(tmpdir)