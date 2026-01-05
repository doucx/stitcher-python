from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_find_code_dirs_in_monorepo_package(tmp_path):
    """
    Tests that _find_code_dirs correctly identifies the 'src' directory
    within a standard monorepo sub-package, instead of incorrectly identifying
    the package root as a flat layout.
    """
    # 1. Arrange: Create a structure mimicking 'packages/stitcher-common'
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory
        # This pyproject.toml is at the sub-package root
        .with_pyproject("packages/stitcher-common")
        .with_source("packages/stitcher-common/src/stitcher/__init__.py", "")
        .build()
    )

    # The package root for the purpose of the test is the directory
    # containing the pyproject.toml file.
    pkg_root = project_root / "packages/stitcher-common"
    expected_src_dir = pkg_root / "src"

    # Instantiate Workspace to get access to the method under test
    # We pass the overall project_root to the Workspace constructor
    workspace = Workspace(root_path=project_root)

    # 2. Act
    # We are testing the private method directly to isolate the logic.
    found_dirs = workspace._find_code_dirs(pkg_root)

    # 3. Assert
    assert expected_src_dir in found_dirs, \
        f"The 'src' directory was not found. Found dirs: {found_dirs}"
    
    # Also assert that the package root itself was NOT added, as it's not a flat layout.
    assert pkg_root not in found_dirs, \
        f"The package root was incorrectly identified as a code dir. Found: {found_dirs}"
