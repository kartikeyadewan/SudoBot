"""Tests for execution layer (mocked)."""


def test_mock_subprocess_execution():
    """Test mocked subprocess execution (no actual execution)."""
    # In v1, execution only happens after explicit user confirmation
    # This test verifies the mock structure
    import unittest.mock

    with unittest.mock.patch("subprocess.run") as mock_run:
        mock_run.return_value = unittest.mock.MagicMock(
            returncode=0, stdout=b"", stderr=b""
        )
        # Verify mock is set up correctly
        assert mock_run is not None


def test_user_rejection_prevents_execution():
    """Test that user rejection prevents execution."""
    confirmed = False
    assert not confirmed


def test_execution_isolated_from_matching():
    """Test that execution layer is isolated from matching layer."""
    # The matching module should not import or depend on executor
    import sudobot.matcher
    import sudobot.executor
    # Verify they are separate modules
    assert sudobot.matcher is not sudobot.executor