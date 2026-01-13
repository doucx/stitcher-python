import pytest
from typer.testing import CliRunner
from textwrap import dedent

from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L

runner = CliRunner()


def test_pump_update_preserves_fidelity(tmp_path, monkeypatch):
    """
    Verifies the UPDATE path of the SidecarAdapter via `pump`.
    Ensures that when updating an existing file, custom key order and
    comments are preserved, and new keys are appended.
    """
    # 1. ARRANGE
    # Create a workspace with an existing, custom-formatted .stitcher.yaml
    # and a new function in the source code to be pumped.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            """
            def z_func():
                \"\"\"Doc for Z\"\"\"
                pass

            def a_func():
                \"\"\"Doc for A\"\"\"
                pass

            def new_func():
                \"\"\"Doc for New\"\"\"
                pass
            """,
        )
        .with_raw_file(
            "src/main.stitcher.yaml",
            """
            # My special comment, must be preserved.
            z_func: |-
              Doc for Z
            a_func: |-
              Doc for A
            """,
        )
        .build()
    )
    monkeypatch.chdir(project_root)

    # 2. ACT
    result = runner.invoke(app, ["pump"], catch_exceptions=False)

    # 3. ASSERT
    assert result.exit_code == 0, result.stdout

    content = (project_root / "src/main.stitcher.yaml").read_text()

    # Assert comment is preserved
    assert "# My special comment, must be preserved." in content

    # Assert original key order is preserved and new key is appended
    z_pos = content.find("z_func:")
    a_pos = content.find("a_func:")
    new_pos = content.find("new_func:")

    assert z_pos != -1 and a_pos != -1 and new_pos != -1
    assert z_pos < a_pos < new_pos, "Key order was not preserved/appended correctly."

    # Assert content is correct
    assert "Doc for New" in content


def test_check_does_not_reformat_file_on_success(tmp_path, monkeypatch):
    """
    Verifies that a successful `check` run does NOT reformat or reorder
    a .stitcher.yaml file that has custom, non-alphabetical key order.
    """
    # 1. ARRANGE
    # Create a workspace and run `init` to get a fully consistent state
    # (code, docs, signatures).
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            """
            def z_func():
                \"\"\"Doc for Z\"\"\"
                pass
            def a_func():
                \"\"\"Doc for A\"\"\"
                pass
            """,
        )
        .build()
    )
    monkeypatch.chdir(project_root)
    init_result = runner.invoke(app, ["init"], catch_exceptions=False)
    assert init_result.exit_code == 0

    # Now, manually reorder the generated YAML to be non-standard
    yaml_path = project_root / "src/main.stitcher.yaml"
    reordered_content = dedent(
        """
        z_func: |-
          Doc for Z
        a_func: |-
          Doc for A
        """
    ).lstrip()
    yaml_path.write_text(reordered_content)
    content_before = yaml_path.read_text()

    # 2. ACT
    spy_bus = SpyBus()
    with spy_bus.patch(monkeypatch):
        check_result = runner.invoke(app, ["check"], catch_exceptions=False)

    # 3. ASSERT
    assert check_result.exit_code == 0, check_result.stdout

    # Assert that the check reported success (no real violations found)
    spy_bus.assert_id_called(L.check.run.success)

    # The critical assertion: the file content must not have changed.
    content_after = yaml_path.read_text()
    assert content_before == content_after, "Check command incorrectly reformatted the YAML file."