from pathlib import Path
from stitcher.app import StitcherApp
from stitcher.test_utils import WorkspaceFactory, VenvHarness


def test_pyright_resolves_types_from_stubs(
    tmp_path: Path, isolated_env: VenvHarness
):
    """
    Verifies that Pyright (the engine for VSCode's Pylance) can successfully
    resolve types from a generated stub package, simulating the IDE experience.
    """
    # 1. Arrange: Create a source project to generate stubs for.
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_project_name("ide-proxy-proj")
        .with_config({"scan_paths": ["src/ide_proxy"], "stub_package": "stubs"})
        .with_source(
            "src/ide_proxy/models.py",
            """
            class ProxyModel:
                def get_id(self) -> int:
                    return 1
            """,
        )
        .build()
    )

    # 2. Act: Generate the stub package from the source project.
    app = StitcherApp(root_path=project_root)
    app.run_from_config()
    stub_pkg_path = project_root / "stubs"
    assert (
        stub_pkg_path / "src/ide_proxy-stubs/models.pyi"
    ).exists(), "Stub .pyi file was not generated."

    # 3. Act: Install the generated stubs into the isolated venv.
    isolated_env.install(str(stub_pkg_path))

    # 4. Act: Create a client script that consumes the code.
    client_script = tmp_path / "client.py"
    client_script.write_text(
        """
from ide_proxy.models import ProxyModel

# If stubs are working, pyright will know ProxyModel and its methods.
instance = ProxyModel()
reveal_type(instance.get_id())
"""
    )

    # 5. Act: Run pyright inside the isolated environment.
    result = isolated_env.run_pyright_check(client_script)

    # 6. Assert
    assert (
        result.returncode == 0
    ), f"Pyright failed with errors:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"

    # Verify Pyright's output confirms successful type analysis.
    assert (
        "0 errors" in result.stdout
    ), f"Pyright reported errors:\n{result.stdout}"
    assert (
        'Type of "instance.get_id()" is "int"' in result.stdout
    ), f"Pyright did not resolve the return type correctly.\nOutput:\n{result.stdout}"