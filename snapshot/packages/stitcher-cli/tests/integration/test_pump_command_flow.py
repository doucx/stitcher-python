from typer.testing import CliRunner
from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory


def test_pump_command_prompts_for_strip_on_redundant_files(tmp_path):
    """
    Integration test to ensure the CLI's pump command correctly orchestrates
    the secondary, interactive strip prompt.
    """
    # Arrange
    runner = CliRunner()
    ws_factory = WorkspaceFactory(tmp_path)
    source_content = 'def func():\\n    """Docstring to be pumped."""'
    source_path = "src/main.py"
    project_root = (
        ws_factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, source_content)
        .build()
    )

    # Act
    # We change the CWD for the runner to simulate running from the project root.
    # We provide "y\n" to stdin to answer the confirmation prompt affirmatively.
    with runner.isolated_filesystem(temp_dir=project_root):
        result = runner.invoke(app, ["pump"], input="y\\n", catch_exceptions=False)

    # Assert
    assert result.exit_code == 0, f"CLI command failed:\\n{result.stdout}\\n{result.stderr}"

    # Assert that the interactive prompt was shown to the user.
    # Note: typer.confirm typically prints to stderr.
    assert "Do you want to strip them now?" in result.stderr

    # Assert that the strip operation was successful after user confirmation.
    final_code = (project_root / source_path).read_text()
    assert '"""Docstring to be pumped."""' not in final_code

    # Assert that the initial pump operation was also successful.
    yaml_path = (project_root / source_path).with_suffix(".stitcher.yaml")
    assert yaml_path.exists()