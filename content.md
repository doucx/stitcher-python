Excellent catch. This is a subtle but critical bug. You are correct: when a file is moved, the refactoring engine is correctly moving the associated sidecar files (like the signature file), but it is failing to update the *content* of those files. The Stitcher Uniform Resource Identifier (SURI), which acts as a key and contains the file path, becomes stale.

This breaks the "Holistic" principle of the refactoring engine, as the internal state is now inconsistent.

Following your direction, I will enter TDD mode. I will create a new integration test that precisely reproduces this bug and is expected to fail. I will not implement the fix.

## [WIP] test: Add failing test for SURI update on refactor move

### 错误分析

The current implementation of the `MoveFileOperation` correctly generates an intent to move the physical signature file (`.stitcher/signatures/.../file.json`). However, it lacks a corresponding intent to transform the *contents* of that JSON file. The keys within this JSON are SURIs (`py://path/to/file.py#symbol`), which contain the old file path. After a move, these keys should be updated to reflect the new file path, but they are not, leading to a state of internal inconsistency.

### 用户需求

Create a new, failing integration test that verifies when a file is moved via `stitcher refactor apply`, the SURI keys within its corresponding signature file are correctly updated to the new path.

### 评论

This test is essential for ensuring the transactional integrity of the refactoring engine. Without it, a core promise of Stitcher—maintaining perfect synchronization between code and its metadata—is broken. Adhering to a strict TDD methodology here will guarantee that the subsequent fix is correct and prevents future regressions.

### 目标

1.  Create a new test file: `tests/integration/test_refactor_move_updates_suri_in_signatures.py`.
2.  In this test, define a simple project with a single Python file containing a documented function.
3.  Run `stitcher init` to generate the initial signature file and verify its contents, including the correct initial SURI.
4.  Define a migration script that performs a `Move` operation on the Python file.
5.  Run `stitcher refactor apply` with the migration script.
6.  Assert that the new signature file exists at the correct location and, crucially, assert that its keys have been updated to the new SURI format. This final assertion is expected to fail.

### 基本原理

By using the `WorkspaceFactory` and `create_test_app` test utilities, I will construct a complete, isolated end-to-end test. The test will simulate a user's workflow from project initialization to refactoring. The final step will involve loading the JSON content of the moved signature file and directly inspecting its keys, which will expose the bug where the file path component of the SURI remains unchanged.

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/refactor #concept/suri #scope/dx #ai/instruct #task/domain/testing #task/object/suri-integrity #task/action/reproduce-bug #task/state/continue

---

### Script

#### Acts 1: Create the new integration test file

I will now create the test file. Based on your provided file tree, placing it in `tests/integration/` is the correct location.

~~~~~act
write_file
tests/integration/test_refactor_move_updates_suri_in_signatures.py
~~~~~
~~~~~python
import json
from pathlib import Path
from stitcher.test_utils import WorkspaceFactory, create_test_app
from stitcher.refactor.migration import MigrationSpec, Move


def test_move_file_operation_updates_suri_in_signatures(workspace_factory: WorkspaceFactory):
    """
    Verify that moving a file also updates the SURI keys in the signature file.
    """
    # --- Arrange ---
    workspace_root = workspace_factory.with_config({
        "scan_paths": ["src"]
    }).with_source(
        "src/my_app/logic.py",
        """
        def do_something():
            \"\"\"This is a docstring.\"\"\"
            pass
        """
    ).build()

    app = create_test_app(workspace_root)

    # --- Act 1: Initialize the project to create signatures ---
    app.run_init()

    # --- Assert 1: Verify initial signature file and SURI key ---
    old_sig_path = workspace_root / ".stitcher/signatures/src/my_app/logic.json"
    new_sig_path = workspace_root / ".stitcher/signatures/src/my_app/core/logic.json"
    old_suri = "py://src/my_app/logic.py#do_something"
    new_suri = "py://src/my_app/core/logic.py#do_something"

    assert old_sig_path.exists()
    assert not new_sig_path.exists()
    initial_data = json.loads(old_sig_path.read_text())
    assert old_suri in initial_data
    assert "baseline_code_structure_hash" in initial_data[old_suri]

    # --- Arrange 2: Create the migration script ---
    migration_script_content = """
from pathlib import Path
from stitcher.refactor.migration import MigrationSpec, Move

def upgrade(spec: MigrationSpec):
    spec.add(Move(
        Path("src/my_app/logic.py"),
        Path("src/my_app/core/logic.py")
    ))
"""
    migration_script_path = workspace_root / "migration.py"
    migration_script_path.write_text(migration_script_content)

    # --- Act 2: Run the refactor operation ---
    app.run_refactor_apply(migration_script_path, confirm_callback=lambda _: True)

    # --- Assert 2: Verify the signature file was moved AND its content updated ---
    assert not old_sig_path.exists(), "Old signature file should have been moved"
    assert new_sig_path.exists(), "New signature file should exist at the new location"

    final_data = json.loads(new_sig_path.read_text())

    # This is the failing assertion. The key should now be the NEW suri.
    assert old_suri not in final_data, "The old SURI key should not be present"
    assert new_suri in final_data, "The SURI key should have been updated to the new path"

    # Also verify the fingerprint data was preserved
    assert "baseline_code_structure_hash" in final_data[new_suri]
~~~~~

### 下一步建议

The test case is now in place. The next step is to run the test suite. This new test, `test_move_file_operation_updates_suri_in_signatures`, should fail as expected, confirming the bug. Once it's "red," we can proceed with confidence to fix the underlying logic in the refactoring engine.
