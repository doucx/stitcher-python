import sys
from unittest.mock import MagicMock
from typer.testing import CliRunner
from stitcher.cli.main import app
import pytest

runner = CliRunner()

def test_check_non_interactive_flag_disables_handler(monkeypatch):
    """
    Verifies that --non-interactive flag prevents TyperInteractionHandler
    from being instantiated even if in a TTY.
    """
    # Mock TTY to True
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    
    # Mock StitcherApp to see what handler it gets
    mock_app_cls = MagicMock()
    monkeypatch.setattr("stitcher.cli.main.StitcherApp", mock_app_cls)
    
    # Run with flag
    runner.invoke(app, ["check", "--non-interactive"])
    
    # Assert: interaction_handler passed to constructor was None
    args, kwargs = mock_app_cls.call_args
    assert kwargs["interaction_handler"] is None

def test_check_interactive_by_default_in_tty(monkeypatch):
    """
    Verifies that in a TTY, an InteractionHandler is injected by default.
    """
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    
    mock_app_cls = MagicMock()
    monkeypatch.setattr("stitcher.cli.main.StitcherApp", mock_app_cls)
    
    runner.invoke(app, ["check"])
    
    args, kwargs = mock_app_cls.call_args
    assert kwargs["interaction_handler"] is not None
    assert "TyperInteractionHandler" in str(type(kwargs["interaction_handler"]))