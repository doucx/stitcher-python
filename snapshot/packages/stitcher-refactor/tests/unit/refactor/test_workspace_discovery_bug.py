from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_workspace_discovery_with_root_config_and_namespace_packages(tmp_path):
    """
    Reproduction test for a bug where 'stitcher' namespace package is not discovered
    when running in a monorepo structure with a root pyproject.toml and a migration script.
    """
    # 1. Arrange: Simulate the user's environment structure
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory
        # Root level configuration and script
        .with_pyproject(".")
        .with_source("001_rename_message_bus.py", "pass")
        
        # Package 1: stitcher-common (contributes to stitcher namespace)
        .with_pyproject("packages/stitcher-common")
        .with_source(
            "packages/stitcher-common/src/stitcher/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
        )
        .with_source("packages/stitcher-common/src/stitcher/common/__init__.py", "")
        
        # Package 2: stitcher-cli (contributes to stitcher namespace)
        .with_pyproject("packages/stitcher-cli")
        .with_source(
            "packages/stitcher-cli/src/stitcher/__init__.py",
            "__path__ = __import__('pkgutil').extend_path(__path__, __name__)"
        )
        .with_source("packages/stitcher-cli/src/stitcher/cli/__init__.py", "")
        
        # Another package: needle (should be discovered)
        .with_pyproject("packages/pyneedle")
        .with_source("packages/pyneedle/src/needle/__init__.py", "")
        
        .build()
    )

    # 2. Act
    workspace = Workspace(root_path=project_root)
    discovered_packages = list(workspace.import_to_source_dirs.keys())
    
    # Debug output for analysis
    print(f"Discovered packages: {discovered_packages}")

    # 3. Assert
    # The migration script might be discovered as a module (e.g. '001_rename_message_bus')
    # But crucially, 'stitcher' MUST be present.
    assert "stitcher" in workspace.import_to_source_dirs, \
        f"'stitcher' package was not discovered. Found: {discovered_packages}"

    # Verify that 'stitcher' maps to multiple source directories (from common and cli)
    stitcher_sources = workspace.import_to_source_dirs["stitcher"]
    assert len(stitcher_sources) >= 2, \
        f"Expected at least 2 source dirs for 'stitcher', found {len(stitcher_sources)}: {stitcher_sources}"