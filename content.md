You are absolutely right. My apologies. I introduced an inconsistency by using a fixture pattern (`spy_bus: SpyBus`) in the new test, while the existing tests in that file use manual instantiation. This is a clear violation of engineering principles—specifically, maintaining consistency within a module. I also missed the crucial step of actually patching the bus with `monkeypatch`.

Thank you for catching this. I will now generate a plan to correct this error immediately.

## [WIP] fix: Correct SpyBus usage in circular dependency integration test

### 错误分析

The test `test_check_command_detects_circular_dependency` failed because it incorrectly declared `spy_bus` as a fixture in its signature, which does not exist. The established pattern in `test_check_command.py` is to manually instantiate `SpyBus` and then use the `monkeypatch` fixture to apply it. My implementation deviated from this pattern and also failed to wrap the `app.run_check()` call in the necessary `spy_bus.patch()` context manager.

### 用户需求

The user requires the failing test to be fixed by adhering to the established testing patterns within the file: manually creating the `SpyBus` instance and using `monkeypatch` to activate it.

### 评论

This is a straightforward but important correction. Maintaining consistent testing patterns is crucial for the readability and maintainability of the test suite. This fix restores that consistency and ensures the test correctly spies on the message bus.

### 目标

1.  Modify the signature of `test_check_command_detects_circular_dependency` to remove the `spy_bus` parameter and add the `monkeypatch` parameter.
2.  Add the necessary import for `pathlib.Path`.
3.  Inside the test, instantiate `SpyBus` manually.
4.  Wrap the call to `app.run_check()` in a `with spy_bus.patch(...)` block to ensure messages are captured.

### 基本原理

We will use two `patch_file` operations. The first will add the missing `from pathlib import Path` import statement. The second will perform a targeted replacement of the entire failing test function with its corrected version. This ensures the fix is atomic and complete.

### 标签

#intent/fix #flow/ready #priority/critical #comp/application #comp/tests #scope/dx #ai/instruct #task/domain/analysis #task/object/architecture-engine #task/action/integration #task/state/continue

---

### Script

#### Acts 1: Add Missing Import

The new test uses `pathlib.Path` but the import was not added. We'll add it now.

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_command.py
~~~~~
~~~~~python.old
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory
~~~~~
~~~~~python.new
from pathlib import Path
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory
~~~~~

#### Acts 2: Correct the Test Function

Now we replace the incorrect test function with the corrected version that manually instantiates and patches the `SpyBus`.

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_command.py
~~~~~
~~~~~python.old
def test_check_command_detects_circular_dependency(spy_bus: SpyBus):
    # 1. Arrange
    with WorkspaceFactory(Path.cwd() / "test_project_circ") as wf:
        wf.with_pyproject("packages/pkg-a")
        wf.with_config(
            {
                "scan_paths": ["packages/pkg-a/src"],
            }
        )
        wf.with_source(
            "packages/pkg-a/src/pkg_a/mod_a.py",
            """
            from pkg_a.mod_b import B
            class A: pass
            """,
        )
        wf.with_source(
            "packages/pkg-a/src/pkg_a/mod_b.py",
            """
            from pkg_a.mod_c import C
            class B: pass
            """,
        )
        wf.with_source(
            "packages/pkg-a/src/pkg_a/mod_c.py",
            """
            from pkg_a.mod_a import A
            class C: pass
            """,
        )
        project_root = wf.build()
        app = create_test_app(project_root)

        # 2. Act
        success = app.run_check()

        # 3. Assert
        assert not success
        spy_bus.assert_id_called(L.check.run.fail, level="error")
        spy_bus.assert_id_called(
            L.check.architecture.circular_dependency, level="error"
        )

        # Check the message context
        messages = spy_bus.get_messages()
        arch_msg = next(
            (
                m
                for m in messages
                if m["id"] == str(L.check.architecture.circular_dependency)
            ),
            None,
        )
        assert arch_msg is not None
        assert "cycle" in arch_msg["params"]
        cycle_str = arch_msg["params"]["cycle"]
        assert "packages/pkg-a/src/pkg_a/mod_a.py" in cycle_str
        assert "packages/pkg-a/src/pkg_a/mod_b.py" in cycle_str
        assert "packages/pkg-a/src/pkg_a/mod_c.py" in cycle_str
~~~~~
~~~~~python.new
def test_check_command_detects_circular_dependency(monkeypatch):
    # 1. Arrange
    # Note: Using tmp_path from pytest fixture would be better, but sticking to cwd
    # to minimize changes from the original intent. Let's create a unique dir.
    project_dir = Path.cwd() / "test_project_circ"
    factory = WorkspaceFactory(project_dir)
    factory.with_pyproject("packages/pkg-a")
    factory.with_config(
        {
            "scan_paths": ["packages/pkg-a/src"],
        }
    )
    factory.with_source(
        "packages/pkg-a/src/pkg_a/mod_a.py",
        """
        from pkg_a.mod_b import B
        class A: pass
        """,
    )
    factory.with_source(
        "packages/pkg-a/src/pkg_a/mod_b.py",
        """
        from pkg_a.mod_c import C
        class B: pass
        """,
    )
    factory.with_source(
        "packages/pkg-a/src/pkg_a/mod_c.py",
        """
        from pkg_a.mod_a import A
        class C: pass
        """,
    )
    project_root = factory.build()
    app = create_test_app(project_root)
    spy_bus = SpyBus()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert not success
    spy_bus.assert_id_called(L.check.run.fail, level="error")
    spy_bus.assert_id_called(
        L.check.architecture.circular_dependency, level="error"
    )

    # Check the message context
    messages = spy_bus.get_messages()
    arch_msg = next(
        (
            m
            for m in messages
            if m["id"] == str(L.check.architecture.circular_dependency)
        ),
        None,
    )
    assert arch_msg is not None
    assert "cycle" in arch_msg["params"]
    cycle_str = arch_msg["params"]["cycle"]
    assert "packages/pkg-a/src/pkg_a/mod_a.py" in cycle_str
    assert "packages/pkg-a/src/pkg_a/mod_b.py" in cycle_str
    assert "packages/pkg-a/src/pkg_a/mod_c.py" in cycle_str
~~~~~

### 下一步建议

The test suite should now be consistent and passing. We have successfully completed all steps of the **Phase 2: Graph Capability** roadmap. The `stitcher check` command is now empowered with architectural analysis, starting with circular dependency detection.

This is a logical point to consolidate our work. I recommend creating a `[COMMIT]` plan to formally save this entire feature. If you agree, I will prepare a plan that includes `git add` and `git commit` actions for all the files we've created and modified during this phase.
