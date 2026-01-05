You are right to point out these new failures. The root cause is a misconfigured test environment in `test_refactor_command.py`. The tests manually create a confusing project structure where the `pyproject.toml` is moved away from its source code. This prevents the `Workspace` discovery mechanism from finding the `mypkg` package, resulting in zero refactoring operations being planned. Consequently, the command finishes without emitting the expected "success" or "preview" messages, causing the `SpyBus` assertions to fail.

I will generate a plan to fix this by refactoring the test setups to create a standard and discoverable `src`-layout project.

## [WIP] fix(cli): Correct workspace setup in refactor command tests

### 错误分析

The two failing tests, `test_refactor_apply_e2e` and `test_refactor_apply_dry_run`, share a common root cause: an invalid test workspace setup.

1.  The test code uses `WorkspaceFactory` to create source files under a `src/` directory at the project root (`tmp_path/src/mypkg/...`).
2.  It then manually creates a `packages/pkg_a` directory and moves the project's `pyproject.toml` into it.
3.  This disconnects the project configuration from its source code. When the `refactor_command` runs, its `Workspace` instance finds the `pyproject.toml` but cannot locate the associated source files in the expected relative locations (like `packages/pkg_a/src`).
4.  As a result, no packages are discovered, the semantic graph is empty, and the `Planner` generates zero file operations.
5.  The command exits early after emitting a `refactor.run.no_ops` message, so the expected `refactor.run.success` (in the E2E test) or `refactor.run.preview_header` (in the dry-run test) messages are never sent, causing the `SpyBus` assertions to fail.

### 用户需求

Fix the failing integration tests for the `stitcher refactor apply` command.

### 评论

This is a critical fix. The tests, as they were, were not correctly exercising the refactoring engine's discovery and planning logic. By correcting the workspace setup to a standard `src` layout, we not only fix the tests but also ensure that we are properly validating the command's end-to-end functionality in a realistic project structure.

### 目标

1.  Modify both `test_refactor_apply_e2e` and `test_refactor_apply_dry_run` in `test_refactor_command.py`.
2.  Remove the brittle and incorrect manual creation of the `packages` directory and the subsequent `pyproject.toml` move.
3.  Adjust the `WorkspaceFactory` setup to create a valid `src`-layout project by adding the necessary `src/mypkg/__init__.py` and relying on the factory to correctly place a root `pyproject.toml`.

### 基本原理

We will use two `patch_file` operations to replace the entire flawed workspace arrangement block in each test. The new arrangement will use the `WorkspaceFactory` to build a clean, standard project structure that the `Workspace` class is designed to discover correctly. This eliminates the manual file operations and makes the test setup more declarative and robust.

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #comp/cli #concept/config #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Correct the workspace setup in `test_refactor_apply_e2e`

We will replace the entire arrangement block with a corrected version that builds a proper `src`-layout project.

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
    # Project with a symbol to be renamed
    (
        factory.with_project_name("mypkg")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
        .with_source("pyproject.toml", "[project]\nname='mypkg'")  # For discovery
    ).build()
    # Migration script
    migration_script_content = """
from stitcher.refactor.migration import MigrationSpec, Rename
def upgrade(spec: MigrationSpec):
    spec.add(Rename("mypkg.core.Old", "mypkg.core.New"))
"""
    migration_script = tmp_path / "001_rename.py"
    migration_script.write_text(migration_script_content)

    # We need a fake "packages" structure for discovery to work
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages/pkg_a").mkdir()
    (tmp_path / "pyproject.toml").rename(tmp_path / "packages/pkg_a/pyproject.toml")
~~~~~
~~~~~python.new
    # Project with a symbol to be renamed
    (
        factory.with_project_name("mypkg")
        .with_source("src/mypkg/__init__.py", "")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
    ).build()
    # Migration script
    migration_script_content = """
from stitcher.refactor.migration import MigrationSpec, Rename
def upgrade(spec: MigrationSpec):
    spec.add(Rename("mypkg.core.Old", "mypkg.core.New"))
"""
    migration_script = tmp_path / "001_rename.py"
    migration_script.write_text(migration_script_content)
~~~~~

#### Acts 2: Correct the workspace setup in `test_refactor_apply_dry_run`

Similarly, we will replace the arrangement block in the dry-run test.

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python.old
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    (
        factory.with_project_name("mypkg")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
        .with_source("pyproject.toml", "[project]\nname='mypkg'")
    ).build()
    migration_script_content = """
from stitcher.refactor.migration import MigrationSpec, Rename
def upgrade(spec: MigrationSpec):
    spec.add(Rename("mypkg.core.Old", "mypkg.core.New"))
"""
    migration_script = tmp_path / "001_rename.py"
    migration_script.write_text(migration_script_content)
    (tmp_path / "packages").mkdir()
    (tmp_path / "packages/pkg_a").mkdir()
    (tmp_path / "pyproject.toml").rename(tmp_path / "packages/pkg_a/pyproject.toml")
~~~~~
~~~~~python.new
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    (
        factory.with_project_name("mypkg")
        .with_source("src/mypkg/__init__.py", "")
        .with_source("src/mypkg/core.py", "class Old: pass")
        .with_source("src/mypkg/app.py", "from mypkg.core import Old")
    ).build()
    migration_script_content = """
from stitcher.refactor.migration import MigrationSpec, Rename
def upgrade(spec: MigrationSpec):
    spec.add(Rename("mypkg.core.Old", "mypkg.core.New"))
"""
    migration_script = tmp_path / "001_rename.py"
    migration_script.write_text(migration_script_content)
~~~~~

### 下一步建议

The test setups have been corrected. Please execute this plan and then run the test suite again. With a valid project structure, the refactoring engine should now correctly discover the packages, plan the operations, and emit the appropriate messages, allowing the tests to pass.
