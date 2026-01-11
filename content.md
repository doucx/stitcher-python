You are absolutely correct. My apologies. The test failed due to a missing fixture, which points to a deeper issue in the test architecture. Your suggestion to centralize this in `stitcher-test-utils` is the ideal monorepo solution, aligning perfectly with the `d3-principle-pytest-monorepo-architecture`. A local `conftest.py` would solve the problem for one package but would violate the DRY principle for the project as a whole.

I will rectify this by promoting `stitcher-test-utils` to a proper pytest plugin. This will make the `workspace_factory` and `spy_bus` fixtures automatically available to all test suites in the monorepo, creating a more robust and maintainable testing foundation.

## [WIP] refactor: Centralize test fixtures into a discoverable plugin

### 用户需求

The test `test_check_does_not_report_imports_as_missing_docs` failed because the `workspace_factory` fixture was not found. This fixture needs to be provided to the test suite in a centralized, reusable manner.

### 评论

This is an essential architectural improvement. By defining shared fixtures in a `test-utils` package and exposing them as a pytest plugin via `entry_points`, we ensure that all packages in the monorepo have consistent access to the same testing infrastructure. This is the correct, "Regular Army" standard for a project of this structure.

### 目标

1.  Create a new `fixtures.py` file within `stitcher-test-utils` to house the implementations of shared pytest fixtures.
2.  Define the `workspace_factory` fixture, which provides an instance of `WorkspaceFactory`, a core testing utility.
3.  Define a `spy_bus` fixture to provide a `SpyBus` instance, another common requirement for testing command outputs.
4.  Modify the `pyproject.toml` of `stitcher-test-utils` to declare an entry point under the `pytest11` group. This officially registers the package as a pytest plugin, making its fixtures discoverable project-wide.

### 基本原理

According to the `d3-principle-pytest-monorepo-architecture`, shared testing infrastructure must be centralized to avoid duplication and ensure consistency. By adding a `pytest11` entry point to `stitcher-test-utils/pyproject.toml`, we instruct pytest to treat this package as a plugin. During test collection, pytest will automatically discover any functions decorated with `@pytest.fixture` within the specified module (`stitcher.test_utils.fixtures`), making them available to any test file in the project without needing explicit imports or local `conftest.py` files.

### 标签

#intent/refine #intent/tooling #flow/ready #priority/high #comp/tests #comp/build #scope/dx #task/domain/testing #task/object/check-command #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Create centralized fixture definitions

First, I'll create the `fixtures.py` file inside the `stitcher-test-utils` package and define the `workspace_factory` and `spy_bus` fixtures there.

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/fixtures.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from .workspace import WorkspaceFactory
from .bus import SpyBus


@pytest.fixture
def workspace_factory(tmp_path: Path) -> WorkspaceFactory:
    """Provides a factory to create isolated test workspaces."""
    return WorkspaceFactory(tmp_path)


@pytest.fixture
def spy_bus() -> SpyBus:
    """Provides a SpyBus instance to intercept and inspect bus messages."""
    return SpyBus()
~~~~~

#### Acts 2: Register `test-utils` as a pytest plugin

Next, I'll modify the `pyproject.toml` of `stitcher-test-utils` to add the `pytest11` entry point, making the fixtures above discoverable.

~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "stitcher-test-utils"
version = "0.1.0"
description = "Internal testing utilities for the Stitcher project."
requires-python = ">=3.10"
dependencies = [
    "pyneedle",
    "PyYAML",
    "tomli-w",
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
    "stitcher-workspace",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~
~~~~~toml.new
[project]
name = "stitcher-test-utils"
version = "0.1.0"
description = "Internal testing utilities for the Stitcher project."
requires-python = ">=3.10"
dependencies = [
    "pyneedle",
    "PyYAML",
    "tomli-w",
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
    "stitcher-workspace",
]

[project.entry-points."pytest11"]
stitcher = "stitcher.test_utils.fixtures"

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~

### 下一步建议

With the test infrastructure now correctly configured, the fixtures `workspace_factory` and `spy_bus` will be globally available. I will now re-run the test I previously created (`test_check_ignores_imports.py`). It should now proceed past the fixture discovery stage and fail at the assertion level, which will confirm that the `check` command's logic is indeed flawed as we originally diagnosed. After that, I will proceed to fix the implementation.
