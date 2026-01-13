import pytest
from typer.testing import CliRunner

from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory

runner = CliRunner()


@pytest.fixture
def workspace_factory(tmp_path, monkeypatch):
    factory = WorkspaceFactory(tmp_path).init_git()
    monkeypatch.chdir(tmp_path)
    return factory


def test_loglevel_default_is_info(workspace_factory):
    """Verifies the default loglevel shows INFO and above, but not DEBUG."""
    workspace_factory.with_config({"scan_paths": ["src"]}).with_source(
        "src/main.py", 'def func(): """doc"""'
    ).build()

    runner.invoke(app, ["init"], catch_exceptions=False)
    result = runner.invoke(app, ["check"], catch_exceptions=False)

    assert result.exit_code == 0
    # L.index.run.start is INFO, L.check.run.success is SUCCESS
    assert "Starting incremental index build..." in result.stdout
    assert "Check passed successfully." in result.stdout
    # L.debug.log.scan_path is DEBUG
    assert "Scanning path" not in result.stdout


def test_loglevel_warning_hides_info_and_success(workspace_factory):
    """Verifies --loglevel warning hides lower level messages."""
    # Setup a project with an untracked file, which triggers a WARNING
    workspace_factory.with_config({"scan_paths": ["src"]}).with_source(
        "src/main.py", "def func(): pass"
    ).build()

    result = runner.invoke(
        app, ["--loglevel", "warning", "check"], catch_exceptions=False
    )

    assert result.exit_code == 1
    # INFO and SUCCESS messages should be hidden
    assert "Starting incremental index build..." not in result.stdout
    assert "Check passed successfully." not in result.stdout
    assert "Check passed with" in result.stdout  # The warning summary
    # L.check.file.untracked is WARNING
    assert "Untracked (no .stitcher.yaml file found" in result.stdout


def test_loglevel_debug_shows_debug_messages(workspace_factory):
    """Verifies --loglevel debug shows verbose debug messages."""
    workspace_factory.with_config({"scan_paths": ["src"]}).with_source(
        "src/main.py", "def func(): pass"
    ).build()

    result = runner.invoke(
        app, ["--loglevel", "debug", "check"], catch_exceptions=False
    )

    assert result.exit_code == 1
    # L.debug.log.scan_path is DEBUG
    assert "Scanning path" in result.stdout
    assert "src" in result.stdout


def test_loglevel_error_shows_only_errors(workspace_factory):
    """Verifies --loglevel error hides everything except errors."""
    # Setup a project with signature drift (ERROR) and an untracked file (WARNING)
    ws = workspace_factory.with_config({"scan_paths": ["src"]})
    ws.with_source("src/main.py", 'def func(a: int): """doc"""')
    ws.build()
    runner.invoke(app, ["init"], catch_exceptions=False)
    # Introduce signature drift
    (ws.root_path / "src/main.py").write_text('def func(a: str): """doc"""')
    # Add an untracked file
    (ws.root_path / "src/untracked.py").write_text("pass")

    result = runner.invoke(
        app, ["--loglevel", "error", "check"], catch_exceptions=False
    )

    assert result.exit_code == 1
    # INFO, SUCCESS, WARNING messages should be hidden
    assert "Starting incremental index build..." not in result.stdout
    assert "Check passed" not in result.stdout
    assert "Untracked" not in result.stdout
    # ERROR messages should be visible
    assert "Check failed for" in result.stdout
    assert "[SIG DRIFT]" in result.stdout