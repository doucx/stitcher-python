from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
from pathlib import Path


def test_workspace_discovery_handles_mixed_packages_and_artifacts(tmp_path: Path):
    """
    Verifies that Workspace discovery correctly identifies various package types
    (regular, namespace) while explicitly ignoring common non-code directories
    (build artifacts, VCS, venv, etc.).
    """
    # 1. Arrange: Create a complex workspace with valid packages and junk dirs
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory
        .with_pyproject(".")
        # A regular package with __init__.py
        .with_source("src/my_pkg_regular/__init__.py", "")
        # A PEP 420 namespace package (no __init__.py)
        .with_source("src/my_pkg_namespace/sub_pkg/__init__.py", "")
        # A regular top-level module
        .with_source("top_level_module.py", "")
        # Common junk/artifact directories that should be ignored
        .with_raw_file(".git/config", "")
        .with_raw_file(".venv/pyvenv.cfg", "")
        .with_raw_file("build/lib/some_file", "")
        .with_raw_file("dist/wheel_file.whl", "")
        .with_raw_file("my_project.egg-info/entry_points.txt", "")
        .with_raw_file(".pytest_cache/README.md", "")
        .build()
    )

    # 2. Act
    workspace = Workspace(root_path=project_root)
    discovered_packages = list(workspace.import_to_source_dirs.keys())

    # 3. Assert
    # A. Assert that all VALID packages and modules are found
    assert "my_pkg_regular" in discovered_packages
    assert "my_pkg_namespace" in discovered_packages
    assert "top_level_module" in discovered_packages

    # B. Assert that all INVALID directories are IGNORED
    assert ".git" not in discovered_packages
    assert ".venv" not in discovered_packages
    assert "build" not in discovered_packages
    assert "dist" not in discovered_packages
    assert "my_project.egg-info" not in discovered_packages
    assert ".pytest_cache" not in discovered_packages