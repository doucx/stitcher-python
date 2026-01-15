好的，这是一个非常好的重构任务。使用 Pytest Fixture 替代手动实例化是提升测试代码整洁度和一致性的标准做法。

根据你的要求，我将遍历所有受影响的测试文件，将 `spy_bus = SpyBus()` 替换为从参数注入的 `spy_bus` fixture，并保留 `SpyBus` 的导入以用于类型提示。对于那些在 `with SpyBus().patch(...)` 中直接实例化的场景，我也会将其统一改为 `with spy_bus.patch(...)`。

由于涉及的文件较多，我将按模块顺序生成执行计划。

## [WIP] refactor(test): 统一使用 spy_bus fixture 替代手动实例化

### 用户需求
将测试套件中所有手动创建 `SpyBus()` 实例的代码改为使用 Pytest fixture `spy_bus`。同时保留 `SpyBus` 的导入语句作为类型提示（Type Hinting）。

### 评论
这是一个典型的测试基础设施重构。通过利用已经在根目录 `conftest.py` 中定义好的 `spy_bus` fixture，我们可以简化测试函数的内部逻辑，减少样板代码，并确保测试环境的统一管理。保留导入作为类型提示是符合 Python 现代开发习惯的。

### 目标
1. 遍历 `stitcher-common`、`stitcher-application` 和 `stitcher-cli` 下的所有测试文件。
2. 在测试函数的参数列表中添加 `spy_bus`（如果尚未添加）。
3. 移除函数体内的 `spy_bus = SpyBus()` 语句。
4. 将所有 `SpyBus()` 临时实例化的用法（如在 `with` 语句中）改为使用 `spy_bus` 变量。
5. 统一将局部变量名（如 `spy`）重命名为 `spy_bus` 以保持一致性。
6. 确保 `from stitcher.test_utils import SpyBus` 等导入保留。

### 基本原理
根据 Pytest 的工作原理，当函数参数名与注册的 fixture 名匹配时，Pytest 会自动注入该 fixture 的实例。我们在根目录定义的 `spy_bus` fixture 每次运行测试都会提供一个全新的、干净的 `SpyBus` 对象。将手动实例化改为 fixture 注入，可以让 Pytest 更好地处理 setup/teardown 逻辑，并使测试代码更符合惯用法。

### 标签
#intent/refine #flow/ready #priority/medium #comp/tests #concept/ui #scope/dx #ai/refine #task/domain/testing #task/object/spy-bus-fixture #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 `stitcher-common` 单元测试

~~~~~act
write_file
packages/stitcher-common/tests/unit/test_message_bus.py
~~~~~
~~~~~python
import pytest
import stitcher.common
from stitcher.test_utils import SpyBus
from needle.pointer import L
from needle.operators import DictOperator


def test_bus_forwards_to_renderer_with_spy(monkeypatch, spy_bus):
    # Arrange
    # For this unit test, we still need to control the message source.
    # We patch the operator of the *global singleton* bus.
    operator = DictOperator({"greeting": "Hello {name}"})
    monkeypatch.setattr(stitcher.common.bus, "_operator", operator)

    # Act
    # Use the spy to patch the global bus's rendering mechanism
    with spy_bus.patch(monkeypatch):
        stitcher.common.bus.info(L.greeting, name="World")
        stitcher.common.bus.success(L.greeting, name="Stitcher")

    # Assert
    messages = spy_bus.get_messages()
    assert len(messages) == 2
    assert messages[0] == {
        "level": "info",
        "id": "greeting",
        "params": {"name": "World"},
    }
    assert messages[1] == {
        "level": "success",
        "id": "greeting",
        "params": {"name": "Stitcher"},
    }


def test_bus_identity_fallback_with_spy(monkeypatch, spy_bus):
    # Arrange
    # A DictOperator with a missing key will return None from the operator,
    # forcing the bus to fall back to using the key itself as the template.
    operator = DictOperator({})
    monkeypatch.setattr(stitcher.common.bus, "_operator", operator)

    # Act
    with spy_bus.patch(monkeypatch):
        # We also need to mock the renderer to see the final string
        # Let's verify the spy bus also captures this correctly.
        # The spy captures the ID, not the final rendered string of the fallback.
        # So we should assert the ID was called.
        stitcher.common.bus.info(L.nonexistent.key)

    # Assert
    # The spy captures the *intent*. The intent was to send "nonexistent.key".
    spy_bus.assert_id_called(L.nonexistent.key, level="info")


def test_bus_does_not_fail_without_renderer():
    # Arrange: A bus with a simple DictOperator, no SpyBus, no renderer.
    # The global bus is configured at startup, so we can't easily de-configure it.
    # This test is now less relevant as the SpyBus provides a safe, no-op render.
    # We can confirm the global bus doesn't crash by simply calling it.
    try:
        # Act
        stitcher.common.bus.info("some.id")
    except Exception as e:
        pytest.fail(f"Global MessageBus raised an exception: {e}")
~~~~~

#### Acts 2: 重构 `stitcher-application` 根目录下的回归测试

~~~~~act
write_file
packages/stitcher-application/tests/test_check_regression.py
~~~~~
~~~~~python
from textwrap import dedent
from pathlib import Path
from stitcher.test_utils import create_test_app
from stitcher.test_utils import WorkspaceFactory, SpyBus, get_stored_hashes
from needle.pointer import L


def test_check_persists_updates_in_multi_target_scan(tmp_path: Path, monkeypatch, spy_bus: SpyBus):
    """
    Regression Test: Ensures that 'doc_improvement' updates are persisted for ALL files,
    not just those in the last scanned batch.

    This simulates a bug where 'modules' variable scope in the loop caused early batches
    to be ignored during the execution phase.
    """
    # 1. Setup a workspace with two targets (pkg1 and pkg2)
    # pkg1 will be scanned FIRST. pkg2 SECOND.
    # We will trigger a doc improvement in pkg1.

    factory = WorkspaceFactory(tmp_path)

    # pkg1: Has a function with matching code/doc initially
    factory.with_source(
        "src/pkg1/mod.py",
        """
def func():
    \"\"\"Doc.\"\"\"
    pass
""",
    )
    factory.with_docs(
        "src/pkg1/mod.stitcher.yaml", {"func": "Doc."}
    )  # Initial state matches

    # pkg2: Just a dummy file
    factory.with_source("src/pkg2/mod.py", "def other(): pass")

    # Config: Define two targets
    factory.build()
    (tmp_path / "pyproject.toml").write_text(
        dedent("""
    [project]
    name = "test-proj"
    
    [tool.stitcher.targets.t1]
    scan_paths = ["src/pkg1"]
    
    [tool.stitcher.targets.t2]
    scan_paths = ["src/pkg2"]
    """),
        encoding="utf-8",
    )

    # 2. Initialize signatures (Run init)
    app = create_test_app(tmp_path)
    app.run_init()

    # Verify init happened
    hashes_initial = get_stored_hashes(tmp_path, "src/pkg1/mod.py")
    assert hashes_initial["func"]["baseline_yaml_content_hash"] is not None

    # 3. Modify Docs in YAML (Simulate Doc Improvement)
    # This creates a state: Code Hash matches, YAML Hash differs -> Doc Improvement
    (tmp_path / "src/pkg1/mod.stitcher.yaml").write_text(
        '"func": |-\n  Better Doc.', encoding="utf-8"
    )

    # 4. Run Check
    # This should detect the improvement and update the signature file
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_check()

    # 5. Assertions

    # A. Check that the bus reported the update (Phase 4 reporting works even with the bug)
    spy_bus.assert_id_called(L.check.state.doc_updated)

    # B. Check PERMANENCE (The critical part)
    # If the bug exists, this file was NOT updated because pkg1 was not in the 'modules'
    # list when the loop finished (pkg2 was).
    hashes_after = get_stored_hashes(tmp_path, "src/pkg1/mod.py")

    # The stored hash should now reflect "Better Doc."
    # We don't check the hash value specifically, but it must differ from initial.
    assert (
        hashes_after["func"]["baseline_yaml_content_hash"]
        != hashes_initial["func"]["baseline_yaml_content_hash"]
    )
~~~~~

#### Acts 3: 重构 `stitcher-application` 集成测试

由于文件较多，我将分批进行。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_command.py
~~~~~
~~~~~python
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_check_detects_matrix_states(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'check' correctly identifies all 5 states:
    Missing, Pending, Redundant, Conflict, Extra.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            """
            def func_missing(): pass
            
            def func_pending():
                \"\"\"New Doc\"\"\"
                pass

            def func_redundant():
                \"\"\"Same Doc\"\"\"
                pass

            def func_conflict():
                \"\"\"Code Doc\"\"\"
                pass
            """,
        )
        .with_docs(
            "src/main.stitcher.yaml",
            {
                "__doc__": "Module doc",
                # Missing: func_missing not here
                # Pending: func_pending not here
                "func_redundant": "Same Doc",
                "func_conflict": "YAML Doc",
                "func_extra": "Old Doc",
            },
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False

    # Check for all issue types
    spy_bus.assert_id_called(L.check.issue.missing, level="warning")
    spy_bus.assert_id_called(L.check.issue.redundant, level="warning")

    spy_bus.assert_id_called(L.check.issue.pending, level="error")
    spy_bus.assert_id_called(L.check.issue.conflict, level="error")
    spy_bus.assert_id_called(L.check.issue.extra, level="error")

    # Verify key association
    messages = spy_bus.get_messages()

    def verify_key(msg_id, expected_key):
        msgs = [m for m in messages if m["id"] == str(msg_id)]
        assert any(m["params"]["key"] == expected_key for m in msgs), (
            f"Expected key '{expected_key}' for message '{msg_id}' not found."
        )

    verify_key(L.check.issue.missing, "func_missing")
    verify_key(L.check.issue.pending, "func_pending")
    verify_key(L.check.issue.redundant, "func_redundant")
    verify_key(L.check.issue.conflict, "func_conflict")
    verify_key(L.check.issue.extra, "func_extra")


def test_check_passes_when_synced(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(): pass")
        .with_docs(
            "src/main.stitcher.yaml",
            {"__doc__": "Doc", "func": "Doc"},
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.run.success, level="success")


def test_check_command_detects_circular_dependency(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange
    # Corrected: Using tmp_path to ensure isolation and prevent root pollution
    project_dir = tmp_path / "test_project_circ"
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

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert not success
    spy_bus.assert_id_called(L.check.run.fail, level="error")
    spy_bus.assert_id_called(L.check.architecture.circular_dependency, level="error")

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

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_conflict.py
~~~~~
~~~~~python
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_check_detects_content_conflict(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'check' command fails if docstring content differs
    between the source code and the YAML file.
    """
    # 1. Arrange: Setup a workspace with conflicting docstrings
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Source Code Doc"""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False, "Check should fail when content conflicts."

    # Assert that the specific conflict message was sent as an error
    spy_bus.assert_id_called(L.check.issue.conflict, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")

    # Verify the parameters of the conflict message
    conflict_msg = next(
        (m for m in spy_bus.get_messages() if m["id"] == str(L.check.issue.conflict)),
        None,
    )
    assert conflict_msg is not None
    assert conflict_msg["params"]["key"] == "func"
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_file_tracking.py
~~~~~
~~~~~python
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_check_reports_untracked_with_details(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'check' reports a detailed UNTRACKED message when a new
    file contains public APIs that are missing docstrings.
    """
    # 1. Arrange: A new file with one documented and one undocumented function
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            """
            def func_documented():
                \"\"\"I have a docstring.\"\"\"
                pass

            def func_undocumented():
                pass
            """,
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_check()

    # 3. Assert
    # Assert the detailed header was called
    spy_bus.assert_id_called(L.check.file.untracked_with_details, level="warning")
    # Assert the specific key was listed
    spy_bus.assert_id_called(L.check.issue.untracked_missing_key, level="warning")

    # Verify the correct key was reported
    messages = spy_bus.get_messages()
    missing_key_msg = next(
        (m for m in messages if m["id"] == str(L.check.issue.untracked_missing_key)),
        None,
    )
    assert missing_key_msg is not None
    assert missing_key_msg["params"]["key"] == "func_undocumented"

    # Verify the simple "untracked" message was NOT called
    assert not any(msg["id"] == str(L.check.file.untracked) for msg in messages)


def test_check_reports_simple_untracked_if_all_docs_present(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'check' falls back to the simple UNTRACKED message if
    a new file has content, but all its public APIs already have docstrings
    (i.e., it just needs to be hydrated).
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def new_func():\n    """Docstring present."""')
        .build()
    )

    app = create_test_app(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_check()

    # Assert the simple message was called
    spy_bus.assert_id_called(L.check.file.untracked, level="warning")
    # Assert the detailed message was NOT called
    messages = spy_bus.get_messages()
    assert not any(
        msg["id"] == str(L.check.file.untracked_with_details) for msg in messages
    )


def test_check_is_silent_for_empty_untracked_file(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'check' does NOT report UNTRACKED for an untracked file
    that contains no documentable content (e.g., an empty __init__.py).
    """
    # 1. Arrange: An empty source file with no doc file
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/__init__.py", "# This file is intentionally empty")
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.run.success, level="success")
    messages = spy_bus.get_messages()
    assert not any(msg["id"] == str(L.check.file.untracked) for msg in messages)


def test_check_is_silent_for_boilerplate_untracked_file(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'check' also ignores untracked files that only contain
    boilerplate like __all__ or __path__.
    """
    # 1. Arrange: A source file with only boilerplate, and no doc file
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/namespace/__init__.py",
            """
            __path__ = __import__("pkgutil").extend_path(__path__, __name__)
            __all__ = ["some_module"]
            """,
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.run.success, level="success")
    messages = spy_bus.get_messages()
    assert not any(msg["id"] == str(L.check.file.untracked) for msg in messages)
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_ignores_imports.py
~~~~~
~~~~~python
from needle.pointer import L

from stitcher.test_utils import WorkspaceFactory, SpyBus, create_test_app


def test_check_does_not_report_imports_as_missing_docs(
    workspace_factory: WorkspaceFactory, monkeypatch, spy_bus: SpyBus
):
    """
    Verifies that 'stitcher check' does not incorrectly flag imported symbols
    as missing documentation. It should only flag symbols defined within the
    scanned module.
    """
    # 1. Setup: Create a project with a file that has imports and defined symbols
    ws = (
        workspace_factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/my_pkg/core.py",
            """
import os
import logging
from pathlib import Path
from typing import Optional, List

# This function is defined locally and should be reported as missing docs.
def my_public_function():
    pass

# This class is defined locally and should also be reported.
class MyPublicClass:
    pass
            """,
        )
        .build()
    )

    # 2. Execution: Run the check command
    app = create_test_app(ws)
    with spy_bus.patch(monkeypatch):
        # run_check returns True (success) if there are only warnings.
        success = app.run_check()

    assert success
    # 3. Assertion & Visibility
    messages = spy_bus.get_messages()

    print("\n=== Captured Bus Messages ===")
    for msg in messages:
        print(f"[{msg['level'].upper()}] {msg['id']}: {msg.get('params', {})}")
    print("=============================")

    # Filter for only the 'missing documentation' warnings
    missing_doc_warnings = [
        msg for msg in messages if msg["id"] == str(L.check.issue.missing)
    ]

    # Extract the 'key' (the FQN) from the warning parameters
    reported_keys = {msg["params"]["key"] for msg in missing_doc_warnings}
    print(f"Reported Keys for Missing Docs: {reported_keys}")

    # Assert that our defined symbols ARE reported
    assert "my_public_function" in reported_keys, (
        "Locally defined function missing from report"
    )
    assert "MyPublicClass" in reported_keys, "Locally defined class missing from report"

    # Assert that imported symbols are NOT reported
    imported_symbols = {"os", "logging", "Path", "Optional", "List"}
    for symbol in imported_symbols:
        assert symbol not in reported_keys, (
            f"Imported symbol '{symbol}' was incorrectly reported as missing docs"
        )

    # Verify we found exactly what we expected (local definitions only)
    # Note: If there are other symbols (like __doc__ module level), adjust expectation.
    # The current setup creates a file with a module docstring (implied empty?),
    # but 'missing' check usually skips __doc__.
    # Let's stick to checking our specific targets.
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_ignores_reexports.py
~~~~~
~~~~~python
from needle.pointer import L

from stitcher.test_utils import WorkspaceFactory, SpyBus, create_test_app


def test_check_ignores_reexports_and_imports(
    workspace_factory: WorkspaceFactory, monkeypatch, spy_bus: SpyBus
):
    """
    Verifies that 'stitcher check' correctly ignores:
    1. Symbols re-exported from another module in the same package.
    2. Standard library imports.
    It should only flag symbols physically defined in the file being checked.
    """
    # 1. Setup: Create a project with a re-export structure
    spy_bus = spy_bus
    ws = (
        workspace_factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/my_lib/defs.py",
            """
class MyDefinedClass:
    '''This class has a docstring.'''
    pass
            """,
        )
        .with_source(
            "src/my_lib/__init__.py",
            """
from typing import Dict
from .defs import MyDefinedClass  # This is a re-export

# This function is locally defined and should be reported
def my_local_function():
    pass
            """,
        )
        .build()
    )

    # 2. Execution: Run the check command
    app = create_test_app(ws)
    with spy_bus.patch(monkeypatch):
        app.run_check()

    # 3. Assertion: Verify the output from the bus
    messages = spy_bus.get_messages()

    print("\n=== Captured Bus Messages ===")
    for msg in messages:
        print(f"[{msg['level'].upper()}] {msg['id']}: {msg.get('params', {})}")
    print("=============================")

    missing_doc_warnings = [
        msg for msg in messages if msg["id"] == str(L.check.issue.missing)
    ]

    # The `missing` message only contains the key, not the path. The file-level
    # summary message contains the path. We only need to check the key here.
    reported_keys = {msg["params"]["key"] for msg in missing_doc_warnings}

    # We also check untracked messages, as new symbols will appear here.
    untracked_missing_warnings = [
        msg for msg in messages if msg["id"] == str(L.check.issue.untracked_missing_key)
    ]
    reported_untracked_keys = {
        msg["params"]["key"] for msg in untracked_missing_warnings
    }

    all_reported_keys = reported_keys.union(reported_untracked_keys)

    # Assert that the locally defined function IS reported as missing
    assert "my_local_function" in all_reported_keys, (
        "Local function was not reported as missing."
    )

    # Assert that standard imports and re-exports are NOT reported
    assert "Dict" not in all_reported_keys, (
        "Standard import 'Dict' was incorrectly reported."
    )

    assert "MyDefinedClass" not in all_reported_keys, (
        "Re-exported class 'MyDefinedClass' was incorrectly reported."
    )

    # Assert that the total number of missing doc warnings is exactly 1
    assert len(all_reported_keys) == 1, (
        f"Expected 1 missing doc warning, but found {len(all_reported_keys)}: {all_reported_keys}"
    )
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_interactive_flow.py
~~~~~
~~~~~python
import pytest
import yaml
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction, DocstringIR
from stitcher.test_utils import WorkspaceFactory, SpyBus, get_stored_hashes
from needle.pointer import L


class MockResolutionHandler(InteractionHandler):
    """A handler that returns a pre-defined sequence of actions."""

    def __init__(self, actions: List[ResolutionAction]):
        self.actions = actions
        self.called_with: List[InteractionContext] = []

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        self.called_with = contexts
        # Return the pre-programmed sequence of actions
        return self.actions * len(contexts) if len(self.actions) == 1 else self.actions


def test_check_workflow_mixed_auto_and_interactive(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Ensures that auto-reconciliation and interactive decisions can co-exist
    and are executed correctly in their respective phases.
    """
    factory = WorkspaceFactory(tmp_path)
    # 1. Setup: A module with two functions
    # func_a: will have doc improvement (auto)
    # func_b: will have signature drift (interactive)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/app.py",
            '''
def func_a():
    """Old Doc A."""
    pass
def func_b(x: int):
    """Doc B."""
    pass
''',
        )
        .build()
    )

    app_for_init = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app_for_init.run_init()

    # 2. Trigger Changes
    # Change A: Modify YAML directly (Doc Improvement)
    doc_file = project_root / "src/app.stitcher.yaml"
    doc_file.write_text('func_a: "New Doc A."\nfunc_b: "Doc B."\n', encoding="utf-8")

    # Change B: Modify Source Code (Signature Drift)
    (project_root / "src/app.py").write_text("""
def func_a():
    pass
def func_b(x: str): # int -> str
    pass
""")

    # 3. Define Interactive Decision and inject Handler
    handler = MockResolutionHandler([ResolutionAction.RELINK])
    app = create_test_app(root_path=project_root, interaction_handler=handler)

    # 4. Run Check
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 5. Assertions
    assert success is True
    # Verify Auto-reconcile report for func_a
    doc_updated_msg = next(
        (
            m
            for m in spy_bus.get_messages()
            if m["id"] == str(L.check.state.doc_updated)
        ),
        None,
    )
    assert doc_updated_msg is not None
    assert doc_updated_msg["params"]["key"] == "func_a"

    # Verify Interactive resolution report for func_b
    spy_bus.assert_id_called(L.check.state.relinked, level="success")

    # Verify Hashes are actually updated in storage
    final_hashes = get_stored_hashes(project_root, "src/app.py")

    # func_a should have updated yaml hash
    ir_a = DocstringIR(summary="New Doc A.")
    expected_doc_a_hash = app.doc_manager.compute_ir_hash(ir_a)
    assert final_hashes["func_a"]["baseline_yaml_content_hash"] == expected_doc_a_hash

    # func_b should have updated code hash due to RELINK
    assert "baseline_code_structure_hash" in final_hashes["func_b"]
    assert final_hashes["func_b"]["baseline_code_structure_hash"] is not None


@pytest.fixture
def dangling_doc_workspace(tmp_path):
    """Creates a workspace with a doc file containing an extra key."""
    factory = WorkspaceFactory(tmp_path)
    return (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "def func_a(): pass")
        .with_docs(
            "src/app.stitcher.yaml",
            {"func_a": "Doc A.", "dangling_func": "This one is extra."},
        )
        .build()
    )


def test_check_interactive_purge_removes_dangling_doc(
    dangling_doc_workspace, monkeypatch, spy_bus: SpyBus
):
    """
    Verify that choosing [P]urge correctly removes the dangling entry from the YAML file.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Purge'
    handler = MockResolutionHandler([ResolutionAction.PURGE_DOC])
    app = create_test_app(root_path=dangling_doc_workspace, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True, "Check should succeed after interactive purge."

    # Assert correct context was passed to handler
    assert len(handler.called_with) == 1
    assert handler.called_with[0].fqn == "dangling_func"
    assert handler.called_with[0].violation_type == L.check.issue.extra

    # Assert correct bus message was sent
    spy_bus.assert_id_called(L.check.state.purged, level="success")

    # Assert YAML file was modified
    doc_file = dangling_doc_workspace / "src/app.stitcher.yaml"
    with doc_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "dangling_func" not in data
    assert "func_a" in data

    # A subsequent check should be clean
    app_verify = create_test_app(root_path=dangling_doc_workspace)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_bus.assert_id_called(L.check.run.success)


def test_check_interactive_skip_dangling_doc_fails(dangling_doc_workspace, monkeypatch, spy_bus: SpyBus):
    """
    Verify that skipping a dangling doc conflict results in a check failure.
    """
    # 1. Arrange: Handler simulates choosing 'Skip'
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=dangling_doc_workspace, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")

    # Assert YAML was not changed
    doc_file = dangling_doc_workspace / "src/app.stitcher.yaml"
    with doc_file.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert "dangling_func" in data


def test_check_interactive_purge_deletes_empty_yaml(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verify that if purging the last entry makes the YAML file empty, the file is deleted.
    """
    # 1. Arrange: Workspace with only a dangling doc
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", "")
        .with_docs("src/app.stitcher.yaml", {"dangling": "doc"})
        .build()
    )
    doc_file = project_root / "src/app.stitcher.yaml"
    assert doc_file.exists()

    handler = MockResolutionHandler([ResolutionAction.PURGE_DOC])
    app = create_test_app(root_path=project_root, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True
    spy_bus.assert_id_called(L.check.state.purged, level="success")
    assert not doc_file.exists(), (
        "YAML file should have been deleted after last entry was purged."
    )


# --- Test Suite for Signature Drift ---


@pytest.fixture
def drift_workspace(tmp_path):
    """Creates a workspace with a signature drift conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", 'def func(a: int):\n    """Doc"""\n    ...')
        .build()
    )
    # Run init to create baseline
    app = create_test_app(root_path=project_root)
    app.run_init()
    # Introduce drift
    (project_root / "src/app.py").write_text("def func(a: str): ...")
    return project_root


def test_check_interactive_relink_fixes_drift(drift_workspace, monkeypatch, spy_bus: SpyBus):
    handler = MockResolutionHandler([ResolutionAction.RELINK])
    app = create_test_app(root_path=drift_workspace, interaction_handler=handler)

    initial_hashes = get_stored_hashes(drift_workspace, "src/app.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is True

    spy_bus.assert_id_called(L.check.state.relinked, level="success")

    final_hashes = get_stored_hashes(drift_workspace, "src/app.py")
    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        != initial_hashes["func"]["baseline_code_structure_hash"]
    )

    # Verify that a subsequent check is clean
    app_verify = create_test_app(root_path=drift_workspace)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_bus.assert_id_called(L.check.run.success)


def test_check_interactive_skip_drift_fails_check(drift_workspace, monkeypatch, spy_bus: SpyBus):
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=drift_workspace, interaction_handler=handler)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is False

    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


# --- Test Suite for Co-Evolution ---


@pytest.fixture
def co_evolution_workspace(tmp_path):
    """Creates a workspace with a co-evolution conflict."""
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", 'def func(a: int):\n    """Old Doc"""\n    ...')
        .build()
    )
    app = create_test_app(root_path=project_root)
    app.run_init()
    # Introduce co-evolution
    (project_root / "src/app.py").write_text("def func(a: str): ...")
    (project_root / "src/app.stitcher.yaml").write_text('func: "New Doc"')
    return project_root


def test_check_interactive_reconcile_fixes_co_evolution(
    co_evolution_workspace, monkeypatch, spy_bus: SpyBus
):
    handler = MockResolutionHandler([ResolutionAction.RECONCILE])
    app = create_test_app(root_path=co_evolution_workspace, interaction_handler=handler)

    initial_hashes = get_stored_hashes(co_evolution_workspace, "src/app.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is True

    spy_bus.assert_id_called(L.check.state.reconciled, level="success")

    final_hashes = get_stored_hashes(co_evolution_workspace, "src/app.py")
    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        != initial_hashes["func"]["baseline_code_structure_hash"]
    )
    assert (
        final_hashes["func"]["baseline_yaml_content_hash"]
        != initial_hashes["func"]["baseline_yaml_content_hash"]
    )

    # Verify that a subsequent check is clean
    app_verify = create_test_app(root_path=co_evolution_workspace)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app_verify.run_check() is True
    spy_bus.assert_id_called(L.check.run.success)


def test_check_interactive_skip_co_evolution_fails_check(
    co_evolution_workspace, monkeypatch, spy_bus: SpyBus
):
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=co_evolution_workspace, interaction_handler=handler)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        assert app.run_check() is False

    spy_bus.assert_id_called(L.check.state.co_evolution, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_policy.py
~~~~~
~~~~~python
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_private_members_allowed_in_yaml(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Policy Test: Private members present in YAML should NOT trigger EXTRA error
    if they exist in the code. They are 'allowed extras'.
    """
    # 1. Arrange: Code with private members and corresponding docs
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/core.py",
            """
            class Internal:
                def _hidden(self): pass
            def _helper(): pass
            """,
        )
        .with_docs(
            "src/core.stitcher.yaml",
            {
                "Internal": "Public class doc",  # Public, checked normally
                "Internal._hidden": "Private method doc",  # Private, allowed
                "_helper": "Private func doc",  # Private, allowed
            },
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    # Should be perfectly clean (True) because private docs are allowed
    assert success is True

    # Ensure NO errors or warnings about extras/missing
    messages = spy_bus.get_messages()
    errors = [m for m in messages if m["level"] == "error"]
    warnings = [m for m in messages if m["level"] == "warning"]

    assert not errors, f"Found unexpected errors: {errors}"
    assert not warnings, f"Found unexpected warnings: {warnings}"

    spy_bus.assert_id_called(L.check.run.success, level="success")


def test_ghost_keys_trigger_extra_error(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Policy Test: Keys in YAML that do not exist in code (even privately)
    MUST trigger EXTRA error.
    """
    # 1. Arrange: Docs pointing to non-existent code
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/ghost.py", "def real(): pass")
        .with_docs(
            "src/ghost.stitcher.yaml",
            {
                "real": "Exists",
                "ghost_func": "Does not exist",
                "_ghost_private": "Does not exist either",
            },
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is False

    # We expect EXTRA errors for both ghost keys
    spy_bus.assert_id_called(L.check.issue.extra, level="error")
    print(spy_bus.get_messages())

    # Verify specific keys
    extra_msgs = [
        m for m in spy_bus.get_messages() if m["id"] == str(L.check.issue.extra)
    ]
    keys = sorted([m["params"]["key"] for m in extra_msgs])
    assert keys == ["_ghost_private", "ghost_func"]


def test_public_missing_triggers_warning_only(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Policy Test: Missing docs for public API should be WARNING, not ERROR.
    Exit code should be success (True).
    """
    # 1. Arrange: Public code without docs
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/lib.py", "def public_api(): pass")
        # Create an empty doc file to ensure the file is tracked
        .with_docs("src/lib.stitcher.yaml", {"__doc__": "Module doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    # 3. Assert
    assert success is True  # Not blocking

    spy_bus.assert_id_called(L.check.issue.missing, level="warning")
    spy_bus.assert_id_called(L.check.run.success_with_warnings, level="success")
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_signatures.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def _assert_no_errors(spy_bus):
    errors = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not errors, f"Unexpected errors: {errors}"


def test_check_detects_signature_change(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    End-to-End test verifying that modifying a function signature
    triggers a check failure/warning.
    """
    factory = WorkspaceFactory(tmp_path)
    initial_code = dedent("""
    def process(value: int) -> int:
        \"\"\"Process an integer.\"\"\"
        return value * 2
    """).strip()

    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/processor.py", initial_code)
        .build()
    )

    app = create_test_app(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    _assert_no_errors(spy_bus)
    # run_init is an alias for pump --reconcile, so it emits pump messages
    spy_bus.assert_id_called(L.pump.run.complete, level="success")

    # Modify Code: Change signature AND remove docstring
    modified_code = dedent("""
    def process(value: str) -> int:
        return len(value) * 2
    """).strip()
    (project_root / "src/processor.py").write_text(modified_code, encoding="utf-8")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")


def test_generate_does_not_update_signatures(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verify that running 'generate' is now pure and DOES NOT update the signature baseline.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """doc"""\n    ...')
        .build()
    )
    app = create_test_app(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    (project_root / "src/main.py").write_text("def func(a: str): ...")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_from_config()

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    assert not success, "Check passed, but it should have failed."
    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")


def test_check_with_force_relink_reconciles_changes(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verify the complete workflow of reconciling signature changes with `check --force-relink`.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func(a: int):\n    """Doc."""\n    ...')
        .build()
    )
    app = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # Modify: Change signature, remove doc to be clean
    (project_root / "src/main.py").write_text("def func(a: str):\n    ...")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success_reconcile = app.run_check(force_relink=True)

    assert success_reconcile is True, "Check with --force-relink failed"
    spy_bus.assert_id_called(L.check.state.relinked, level="success")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success_verify = app.run_check()

    assert success_verify is True, "Verification check failed after reconciliation"
    spy_bus.assert_id_called(L.check.run.success, level="success")
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_check_state_machine.py
~~~~~
~~~~~python
from stitcher.spec import DocstringIR
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory, get_stored_hashes


def _assert_no_errors_or_warnings(spy_bus: SpyBus):
    errors = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    warnings = [m for m in spy_bus.get_messages() if m["level"] == "warning"]
    assert not errors, f"Unexpected errors: {errors}"
    assert not warnings, f"Unexpected warnings: {warnings}"


def test_state_synchronized(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    State 1: Synchronized - Code and docs match stored hashes.
    Expected: Silent pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/module.py", 'def func(a: int):\n    """Docstring."""\n    pass'
        )
        .build()
    )
    app = create_test_app(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # Remove docstring to achieve 'Synchronized' state without redundant warnings
    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    assert success is True
    _assert_no_errors_or_warnings(spy_bus)
    spy_bus.assert_id_called(L.check.run.success, level="success")


def test_state_doc_improvement_auto_reconciled(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    State 2: Documentation Improvement.
    Expected: INFO message, auto-reconcile doc hash, pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: int):\n    pass")

    # Modify YAML
    doc_file = project_root / "src/module.stitcher.yaml"
    new_doc_content = "New Doc."
    doc_file.write_text(
        f'__doc__: "Module Doc"\nfunc: "{new_doc_content}"\n', encoding="utf-8"
    )

    initial_hashes = get_stored_hashes(project_root, "src/module.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    assert success is True
    # Assert Semantic ID for doc update
    spy_bus.assert_id_called(L.check.state.doc_updated, level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = get_stored_hashes(project_root, "src/module.py")
    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        == initial_hashes["func"]["baseline_code_structure_hash"]
    )

    expected_hash = app.doc_manager.compute_ir_hash(
        DocstringIR(summary=new_doc_content)
    )
    assert final_hashes["func"]["baseline_yaml_content_hash"] == expected_hash


def test_state_signature_drift_error(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    State 3: Signature Drift.
    Expected: ERROR message, check fails.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Doc."""\n    pass')
        .build()
    )
    app = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_signature_drift_force_relink(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    State 3 (Resolved): Signature Drift with force_relink.
    Expected: SUCCESS message, update signature hash, pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Doc."""\n    pass')
        .build()
    )
    app = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    initial_hashes = get_stored_hashes(project_root, "src/module.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check(force_relink=True)

    assert success is True
    spy_bus.assert_id_called(L.check.state.relinked, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = get_stored_hashes(project_root, "src/module.py")

    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        != initial_hashes["func"]["baseline_code_structure_hash"]
    )
    assert (
        final_hashes["func"]["baseline_yaml_content_hash"]
        == initial_hashes["func"]["baseline_yaml_content_hash"]
    )


def test_state_co_evolution_error(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    State 4: Co-evolution.
    Expected: ERROR message, check fails.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    doc_file = project_root / "src/module.stitcher.yaml"
    doc_file.write_text(
        '__doc__: "Module Doc"\nfunc: "New YAML Doc."\n', encoding="utf-8"
    )

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check()

    assert success is False
    spy_bus.assert_id_called(L.check.state.co_evolution, level="error")
    spy_bus.assert_id_called(L.check.run.fail, level="error")


def test_state_co_evolution_reconcile(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    State 4 (Resolved): Co-evolution with reconcile.
    Expected: SUCCESS message, update both hashes, pass.
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/module.py", 'def func(a: int):\n    """Old Doc."""\n    pass')
        .build()
    )
    app = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    (project_root / "src/module.py").write_text("def func(a: str):\n    pass")

    doc_file = project_root / "src/module.stitcher.yaml"
    new_doc_content = "New YAML Doc."
    doc_file.write_text(
        f'__doc__: "Module Doc"\nfunc: "{new_doc_content}"\n', encoding="utf-8"
    )

    initial_hashes = get_stored_hashes(project_root, "src/module.py")

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        success = app.run_check(reconcile=True)

    assert success is True
    spy_bus.assert_id_called(L.check.state.reconciled, level="success")
    spy_bus.assert_id_called(L.check.run.success, level="success")

    final_hashes = get_stored_hashes(project_root, "src/module.py")
    assert (
        final_hashes["func"]["baseline_code_structure_hash"]
        != initial_hashes["func"]["baseline_code_structure_hash"]
    )
    assert (
        final_hashes["func"]["baseline_yaml_content_hash"]
        != initial_hashes["func"]["baseline_yaml_content_hash"]
    )

    expected_doc_hash = app.doc_manager.compute_ir_hash(
        DocstringIR(summary=new_doc_content)
    )
    assert final_hashes["func"]["baseline_yaml_content_hash"] == expected_doc_hash
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_end_to_end.py
~~~~~
~~~~~python
import sys

from stitcher.test_utils import create_test_app
from stitcher.workspace import StitcherConfig
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory
from stitcher.common.transaction import TransactionManager


def test_app_scan_and_generate_single_file(tmp_path, monkeypatch, spy_bus: SpyBus):
    factory = WorkspaceFactory(tmp_path)
    project_root = factory.with_source(
        "greet.py",
        """
            def greet(name: str) -> str:
                \"\"\"Returns a greeting.\"\"\"
                return f"Hello, {name}!"
            """,
    ).build()

    app = create_test_app(root_path=project_root)
    tm = TransactionManager(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        # Directly call the service's generate method to test generation logic in isolation.
        source_file = project_root / "greet.py"
        module = app.scanner.scan_files([source_file])[0]
        app.stubgen_service.generate([module], StitcherConfig(), tm)
        tm.commit()

    spy_bus.assert_id_called(L.generate.file.success, level="success")

    error_messages = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not error_messages, f"Found unexpected error messages: {error_messages}"

    assert (project_root / "greet.pyi").exists()


def test_app_run_from_config_with_source_files(tmp_path, monkeypatch, spy_bus: SpyBus):
    # Recreating the structure previously held in tests/fixtures/sample_project
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src/app"]})
        .with_source(
            "src/app/main.py",
            """
            def start():
                \"\"\"Starts the application.\"\"\"
                pass
            """,
        )
        .with_source(
            "src/app/utils/helpers.py",
            """
            def assist():
                \"\"\"Provides assistance.\"\"\"
                pass
            """,
        )
        # This file should remain untouched/unscanned
        .with_source("tests/test_helpers.py", "def test_assist(): pass")
        .build()
    )

    app = create_test_app(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_from_config()

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    success_messages = [m for m in spy_bus.get_messages() if m["level"] == "success"]
    # 2 files generated (main.py, helpers.py), 1 run complete message
    assert len(success_messages) == 4


def test_app_run_multi_target(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that StitcherApp correctly handles multiple targets defined in pyproject.toml.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)

    # Manually injecting multi-target config into pyproject.toml via raw content
    # because WorkspaceFactory.with_config currently assumes simple [tool.stitcher] structure.
    # We'll just overwrite pyproject.toml at the end or use with_source for it.

    project_root = (
        factory.with_source("src/pkg_a/main.py", "def func_a(): ...")
        .with_source("src/pkg_b/main.py", "def func_b(): ...")
        .build()
    )

    # Overwrite pyproject.toml with multi-target config
    (project_root / "pyproject.toml").write_text(
        """
[project]
name = "monorepo"

[tool.stitcher.targets.pkg_a]
scan_paths = ["src/pkg_a"]
stub_path = "typings/pkg_a"

[tool.stitcher.targets.pkg_b]
scan_paths = ["src/pkg_b"]
stub_path = "typings/pkg_b"
        """,
        encoding="utf-8",
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_from_config()

    # 3. Assert
    # Check physical files
    # Note: Stitcher preserves the package structure relative to 'src'.
    # So 'src/pkg_a/main.py' becomes 'pkg_a/main.pyi' inside the stub output directory.
    assert (project_root / "typings/pkg_a/pkg_a/main.pyi").exists()
    assert (project_root / "typings/pkg_b/pkg_b/main.pyi").exists()

    # Check bus messages
    # We expect "Processing target: ..." messages
    messages = spy_bus.get_messages()
    processing_msgs = [
        m for m in messages if m["id"] == str(L.generate.target.processing)
    ]
    assert len(processing_msgs) == 2

    target_names = {m["params"]["name"] for m in processing_msgs}
    assert target_names == {"pkg_a", "pkg_b"}

    spy_bus.assert_id_called(L.generate.run.complete, level="success")


def test_app_generates_stubs_for_plugins_and_sources(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange: Setup a workspace with both source code and a plugin definition
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def static_func(): ...")
        # Define the plugin source code in a separate package within the workspace
        .with_source(
            "plugin_pkg/main.py",
            """
            def dynamic_util() -> bool:
                \"\"\"A dynamically discovered utility.\"\"\"
                return True
            """,
        )
        .with_source("plugin_pkg/__init__.py", "")
        # Register the plugin via entry points
        .with_entry_points(
            "stitcher.plugins", {"dynamic.utils": "plugin_pkg.main:dynamic_util"}
        )
        .build()
    )

    # Add the workspace root to sys.path so the plugin can be imported
    sys.path.insert(0, str(project_root))

    try:
        app = create_test_app(root_path=project_root)

        # 2. Act
        with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
            app.run_from_config()

        # 3. Assert
        # Assert stubs were created
        assert (project_root / "src" / "main.pyi").exists()
        assert (project_root / "dynamic" / "utils.pyi").exists()
        # Intermediate __init__.pyi should be created for the virtual module
        assert (project_root / "dynamic" / "__init__.pyi").exists()

        # Assert bus messages
        spy_bus.assert_id_called(L.generate.file.success, level="success")
        spy_bus.assert_id_called(L.generate.run.complete, level="success")

        success_messages = [
            m for m in spy_bus.get_messages() if m["level"] == "success"
        ]
        # 3 files generated (src/main, dynamic/utils, dynamic/__init__), 1 run complete
        assert len(success_messages) == 5

    finally:
        # Cleanup sys.path
        sys.path.pop(0)
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_init_command.py
~~~~~
~~~~~python
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_init_extracts_docs_to_yaml(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange: Use the factory to build the project
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            """
            def my_func():
                \"\"\"This is a docstring.\"\"\"
                pass
            """,
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # 3. Assert
    expected_yaml = project_root / "src/main.stitcher.yaml"
    assert expected_yaml.exists()

    content = expected_yaml.read_text()
    # Check for block style. ruamel.yaml is smart and won't quote simple keys.
    assert "my_func: |-" in content
    assert "  This is a docstring." in content

    # Updated assertions for Pump behavior
    # L.init.file.created -> L.pump.file.success (since keys were updated)
    spy_bus.assert_id_called(L.pump.file.success, level="success")
    spy_bus.assert_id_called(L.pump.run.complete, level="success")


def test_init_skips_files_without_docs(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def no_doc(): pass")
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_init()

    # 3. Assert - Pump returns No Changes info
    spy_bus.assert_id_called(L.pump.run.no_changes, level="info")
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py
~~~~~
~~~~~python
from stitcher.test_utils import (
    create_test_app,
    SpyBus,
    WorkspaceFactory,
    get_stored_hashes,
)
from needle.pointer import L


def test_init_respects_existing_sidecar_baseline(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    验证 init 不会破坏已存在的 Sidecar 基线。
    场景：
    - 源码中函数 f 的 doc 为 "Source Doc"
    - Sidecar 文件中 f 的内容为 "Sidecar Doc"
    - 执行 init 后，lock 文件中的基线哈希应当对应 "Sidecar Doc"
    """
    factory = WorkspaceFactory(tmp_path)
    # 准备环境
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/lib.py", 'def f():\n    """Source Doc"""\n    pass')
        .with_docs("src/lib.stitcher.yaml", {"f": "Sidecar Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 执行 init (现在等于 pump --reconcile)
    with spy_bus.patch(monkeypatch):
        app.run_init()

    # 获取 Lock 文件中记录的哈希
    hashes = get_stored_hashes(project_root, "src/lib.py")
    stored_yaml_hash = hashes.get("f", {}).get("baseline_yaml_content_hash")

    # 计算预期哈希（Sidecar 的内容）
    doc_manager = app.doc_manager
    ir = doc_manager.serializer.from_view_data("Sidecar Doc")
    expected_hash = doc_manager.compute_ir_hash(ir)

    # 验证 pump --reconcile 正确保留了 Sidecar 内容作为基线
    assert stored_yaml_hash == expected_hash, (
        f"Expected baseline to match Sidecar Doc ({expected_hash}), but got {stored_yaml_hash}"
    )

    # 验证输出消息（应该包含 Reconciled 信息）
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")


def test_index_stats_should_distinguish_sidecars(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    验证索引统计信息应当区分 Sidecar 文件。
    """
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/lib.py", 'def f():\n    """Doc"""\n    pass')
        .with_docs("src/lib.stitcher.yaml", {"f": "Doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    with spy_bus.patch(monkeypatch):
        app.run_index_build()

    # 验证消息中是否包含 sidecars 统计字段
    messages = spy_bus.get_messages()
    index_complete_msg = next(
        m for m in messages if m["id"] == str(L.index.run.complete)
    )

    assert "sidecars" in index_complete_msg["params"], (
        "Index summary should include sidecar count"
    )
    assert index_complete_msg["params"]["sidecars"] == 1
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_lifecycle_commands.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_strip_command_removes_docstrings(tmp_path, monkeypatch, spy_bus: SpyBus):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    initial_code = dedent("""
    \"\"\"Module doc.\"\"\"
    def func():
        \"\"\"Func doc.\"\"\"
        pass
    """)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, initial_code)
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_strip()

    # Assert
    final_code = (project_root / source_path).read_text()
    assert '"""' not in final_code
    assert "def func():" in final_code
    assert "pass" in final_code

    spy_bus.assert_id_called(L.strip.file.success)
    spy_bus.assert_id_called(L.strip.run.complete)


def test_inject_command_injects_docstrings(tmp_path, monkeypatch, spy_bus: SpyBus):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    initial_code = "def func(): pass"
    docs_data = {"func": "Injected docstring."}

    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, initial_code)
        .with_docs("src/main.stitcher.yaml", docs_data)
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_inject()

    # Assert
    final_code = (project_root / source_path).read_text()
    assert '"""Injected docstring."""' in final_code

    spy_bus.assert_id_called(L.inject.file.success)
    spy_bus.assert_id_called(L.inject.run.complete)


def test_strip_command_removes_attribute_docstrings(tmp_path, monkeypatch, spy_bus: SpyBus):
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    initial_code = dedent("""
    from dataclasses import dataclass

    @dataclass
    class MyData:
        attr: str
        \"\"\"Attr doc.\"\"\"
    """)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, initial_code)
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_strip()

    # Assert
    final_code = (project_root / source_path).read_text()
    assert '"""Attr doc."""' not in final_code
    assert "attr: str" in final_code  # Ensure the attribute itself was not removed

    spy_bus.assert_id_called(L.strip.file.success)
    spy_bus.assert_id_called(L.strip.run.complete)
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_parser_robustness.py
~~~~~
~~~~~python
from stitcher.test_utils import WorkspaceFactory, create_test_app, SpyBus
from needle.pointer import L


def test_check_fails_gracefully_on_local_import(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that when the parser raises an exception during scanning,
    the application handles it gracefully:
    1. Catches the exception.
    2. Logs a generic error.
    3. Ensures the overall command fails (returns False).
    """
    # GIVEN a project with a source file
    ws = WorkspaceFactory(tmp_path)
    ws.with_config({"scan_paths": ["src/pkg"]})
    ws.with_source("src/pkg/__init__.py", "")
    ws.with_source(
        "src/pkg/core.py",
        """
        def foo():
            pass
        """,
    )
    ws.build()

    # Create the app
    app = create_test_app(tmp_path)

    # SETUP: Mock the parser to simulate a crash on specific file
    # In Zero-IO mode, parsing happens in the Indexer via PythonAdapter
    # We need to find the correct parser instance to mock.

    from stitcher.lang.python.adapter import PythonAdapter

    python_adapter = app.file_indexer.adapters[".py"]
    # Verify we got the adapter and it's the concrete type we expect
    assert isinstance(python_adapter, PythonAdapter)

    real_parse = python_adapter.parser.parse

    def failing_parse(source_code, file_path=""):
        if "core.py" in str(file_path):
            raise ValueError("Simulated parser crash for testing")
        return real_parse(source_code, file_path)

    monkeypatch.setattr(python_adapter.parser, "parse", failing_parse)

    # WHEN we run the check command
    with spy_bus.patch(monkeypatch):
        success = app.run_check()

    # THEN the command should fail
    assert not success, "Command should return False when parser fails"

    # AND report a generic error
    spy_bus.assert_id_called(L.error.generic, level="error")

    messages = spy_bus.get_messages()
    error_msg = next(
        (m for m in messages if m["id"] == str(L.error.generic)),
        None,
    )
    assert error_msg is not None
    assert "Simulated parser crash" in str(error_msg["params"].get("error", ""))
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_pump_command.py
~~~~~
~~~~~python
import yaml
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_pump_adds_new_docs_to_yaml(tmp_path, monkeypatch, spy_bus: SpyBus):
    """Scenario 1: Normal Pumping"""
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """New doc."""\n    pass')
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.file.success, level="success")
    spy_bus.assert_id_called(L.pump.run.complete, level="success")

    doc_path = project_root / "src/main.stitcher.yaml"
    assert doc_path.exists()
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "New doc."


def test_pump_fails_on_conflict(tmp_path, monkeypatch, spy_bus: SpyBus):
    """Scenario 2: Conflict Detection"""
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code doc."""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # Assert
    assert result.success is False
    spy_bus.assert_id_called(L.pump.error.conflict, level="error")
    spy_bus.assert_id_called(L.pump.run.conflict, level="error")

    # Verify YAML was NOT changed
    doc_path = project_root / "src/main.stitcher.yaml"
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "YAML doc"


def test_pump_force_overwrites_conflict(tmp_path, monkeypatch, spy_bus: SpyBus):
    """Scenario 3: Force Overwrite"""
    # Arrange (same as conflict test)
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code doc."""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump(force=True)

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.file.success, level="success")

    # Verify YAML was changed
    doc_path = project_root / "src/main.stitcher.yaml"
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "Code doc."


def test_pump_with_strip_removes_source_doc(tmp_path, monkeypatch, spy_bus: SpyBus):
    """Scenario 4: Strip Integration"""
    # Arrange
    factory = WorkspaceFactory(tmp_path)
    source_path = "src/main.py"
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source(source_path, 'def func():\n    """New doc."""\n    pass')
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump(strip=True)

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.file.success)
    spy_bus.assert_id_called(L.strip.file.success)
    spy_bus.assert_id_called(L.strip.run.complete)

    # Verify source was stripped
    final_code = (project_root / source_path).read_text()
    assert '"""' not in final_code


def test_pump_reconcile_ignores_source_conflict(tmp_path, monkeypatch, spy_bus: SpyBus):
    """Scenario 5: Reconcile (YAML-first) Mode"""
    # Arrange (same as conflict test)
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code doc."""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML doc"})
        .build()
    )

    app = create_test_app(root_path=project_root)

    # Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump(reconcile=True)

    # Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")

    # Verify no errors were raised
    error_msgs = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not error_msgs

    # Verify YAML was NOT changed
    doc_path = project_root / "src/main.stitcher.yaml"
    with doc_path.open("r") as f:
        data = yaml.safe_load(f)
        assert data["func"] == "YAML doc"
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_pump_interactive_flow.py
~~~~~
~~~~~python
import pytest
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L


class MockResolutionHandler(InteractionHandler):
    """A handler that returns a pre-defined sequence of actions for testing."""

    def __init__(self, actions: List[ResolutionAction]):
        self.actions = actions
        self.called_with: List[InteractionContext] = []

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        self.called_with = contexts
        # Return the same action for all conflicts if only one is provided
        if len(self.actions) == 1:
            return self.actions * len(contexts)
        return self.actions


@pytest.fixture
def conflicting_workspace(tmp_path):
    """Creates a workspace with a doc content conflict."""
    factory = WorkspaceFactory(tmp_path)
    return (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/app.py", 'def func():\n    """Code Doc"""')
        .with_docs("src/app.stitcher.yaml", {"func": "YAML Doc"})
        .build()
    )


def test_pump_interactive_overwrite(spy_bus: SpyBus, conflicting_workspace, monkeypatch):
    """
    Verify that choosing [F]orce-hydrate (HYDRATE_OVERWRITE) correctly
    updates the YAML file with the content from the source code.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Force-hydrate'
    handler = MockResolutionHandler([ResolutionAction.HYDRATE_OVERWRITE])
    app = create_test_app(root_path=conflicting_workspace, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is True, (
        "Pumping should succeed after interactive resolution."
    )
    spy_bus.assert_id_called(L.pump.file.success, level="success")

    # Verify file content was updated
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "Code Doc" in content
    assert "YAML Doc" not in content


def test_pump_interactive_reconcile(conflicting_workspace, monkeypatch, spy_bus: SpyBus):
    """
    Verify that choosing [R]econcile (HYDRATE_KEEP_EXISTING) preserves
    the existing content in the YAML file.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Reconcile'
    handler = MockResolutionHandler([ResolutionAction.HYDRATE_KEEP_EXISTING])
    app = create_test_app(root_path=conflicting_workspace, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is True
    spy_bus.assert_id_called(L.pump.info.reconciled, level="info")
    spy_bus.assert_id_called(L.pump.run.no_changes, level="info")

    # Verify file content was NOT changed
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "YAML Doc" in content
    assert "Code Doc" not in content


def test_pump_interactive_skip_leads_to_failure(conflicting_workspace, monkeypatch, spy_bus: SpyBus):
    """
    Verify that choosing [S]kip leaves the conflict unresolved and causes
    the command to fail.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Skip'
    handler = MockResolutionHandler([ResolutionAction.SKIP])
    app = create_test_app(root_path=conflicting_workspace, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is False, "Pumping should fail if conflicts are skipped."
    spy_bus.assert_id_called(L.pump.error.conflict, level="error")
    spy_bus.assert_id_called(L.pump.run.conflict, level="error")

    # Verify file content was NOT changed
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "YAML Doc" in content


def test_pump_interactive_abort_stops_process(conflicting_workspace, monkeypatch, spy_bus: SpyBus):
    """
    Verify that choosing [A]bort stops the pumping and fails the command.
    """
    # 1. Arrange: Inject a handler that simulates choosing 'Abort'
    handler = MockResolutionHandler([ResolutionAction.ABORT])
    app = create_test_app(root_path=conflicting_workspace, interaction_handler=handler)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is False
    # Assert that the correct semantic 'aborted' message was sent.
    spy_bus.assert_id_called(L.pump.run.aborted, level="error")

    # Verify file content was NOT changed
    doc_file = conflicting_workspace / "src/app.stitcher.yaml"
    content = doc_file.read_text(encoding="utf-8")
    assert "YAML Doc" in content
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_pump_test_files.py
~~~~~
~~~~~python
import yaml
from stitcher.test_utils import create_test_app
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_pump_can_extract_from_test_files(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Regression Test: Verifies that stitcher does NOT ignore files starting with 'test_'
    or living in a 'tests' directory, provided they are explicitly included in scan_paths.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["tests"]})
        .with_source(
            "tests/test_logic.py",
            '''
def test_something():
    """This is a docstring in a test file."""
    pass
''',
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = app.run_pump()

    # 3. Assert
    assert result.success is True

    # It should report success for the file
    spy_bus.assert_id_called(L.pump.file.success, level="success")

    # Verify the yaml file was created and content is correct
    yaml_path = project_root / "tests/test_logic.stitcher.yaml"
    assert yaml_path.exists(), "The .stitcher.yaml file for the test was not created."

    with yaml_path.open() as f:
        data = yaml.safe_load(f)
        assert data["test_something"] == "This is a docstring in a test file."
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_stub_package.py
~~~~~
~~~~~python
import sys

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from stitcher.test_utils import SpyBus, WorkspaceFactory


def test_generate_with_stub_package_creates_correct_structure(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    End-to-end test for the PEP 561 stub package generation mode.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config(
            {
                "scan_paths": ["src/my_app"],
                "stub_package": "stubs",  # <-- Enable stub package mode
            }
        )
        # Define the main project's name, which is used for the stub package name
        .with_project_name("my-test-project")
        .with_source(
            "src/my_app/main.py",
            """
            def run() -> None:
                \"\"\"Main entry point.\"\"\"
                pass
            """,
        )
        .build()
    )

    app = create_test_app(root_path=project_root)

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_from_config()

    # 3. Assert
    # --- Assert File System Structure ---
    stub_pkg_path = project_root / "stubs"
    assert stub_pkg_path.is_dir()

    stub_pyproject = stub_pkg_path / "pyproject.toml"
    assert stub_pyproject.is_file()

    src_path = stub_pkg_path / "src"
    assert src_path.is_dir()

    # PEP 561: Source directory should be named <package>-stubs
    pyi_file = src_path / "my_app-stubs" / "main.pyi"
    assert pyi_file.is_file()
    assert "def run() -> None:" in pyi_file.read_text()

    py_typed_marker = src_path / "my_app-stubs" / "py.typed"
    assert py_typed_marker.is_file()

    # --- Assert pyproject.toml Content ---
    with stub_pyproject.open("rb") as f:
        stub_config = tomllib.load(f)
    assert stub_config["project"]["name"] == "my-test-project-stubs"

    # Assert new Hatchling configuration is present and correct
    hatch_config = stub_config["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert hatch_config["packages"] == ["src/my_app-stubs"]

    # --- Assert Bus Messages ---
    spy_bus.assert_id_called(L.generate.stub_pkg.scaffold)
    spy_bus.assert_id_called(L.generate.stub_pkg.success)
    spy_bus.assert_id_called(L.generate.file.success)
    spy_bus.assert_id_called(L.generate.run.complete)
~~~~~

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_viewdiff_flow.py
~~~~~
~~~~~python
from typing import List
from stitcher.test_utils import create_test_app
from stitcher.spec.interaction import InteractionHandler, InteractionContext
from stitcher.spec import ResolutionAction
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L


class CapturingHandler(InteractionHandler):
    """A handler that captures the contexts passed to it and returns SKIP."""

    def __init__(self):
        self.captured_contexts: List[InteractionContext] = []

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        self.captured_contexts.extend(contexts)
        return [ResolutionAction.SKIP] * len(contexts)


def test_check_generates_signature_diff(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that when a signature changes, 'check' generates a unified diff
    and passes it in the InteractionContext.
    """
    # 1. Arrange: Init project with baseline
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", "def func(a: int): ...")
        .build()
    )

    # Run init to save baseline signature and TEXT
    app_init = create_test_app(root_path=project_root)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app_init.run_init()

    # 2. Modify code to cause signature drift
    (project_root / "src/main.py").write_text("def func(a: str): ...", encoding="utf-8")

    # 3. Run check with capturing handler
    handler = CapturingHandler()
    app_check = create_test_app(root_path=project_root, interaction_handler=handler)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app_check.run_check()

    # 4. Assert
    assert len(handler.captured_contexts) == 1
    ctx = handler.captured_contexts[0]

    assert ctx.violation_type == L.check.state.signature_drift
    assert ctx.signature_diff is not None

    # Check for unified diff markers
    assert "--- baseline" in ctx.signature_diff
    assert "+++ current" in ctx.signature_diff
    assert "-def func(a: int):" in ctx.signature_diff
    assert "+def func(a: str):" in ctx.signature_diff


def test_pump_generates_doc_diff(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that when doc content conflicts, 'pump' generates a unified diff
    and passes it in the InteractionContext.
    """
    # 1. Arrange: Project with conflicting docs
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_config({"scan_paths": ["src"]})
        .with_source("src/main.py", 'def func():\n    """Code Doc"""\n    pass')
        .with_docs("src/main.stitcher.yaml", {"func": "YAML Doc"})
        .build()
    )

    # 2. Run pump with capturing handler
    handler = CapturingHandler()
    app_pump = create_test_app(root_path=project_root, interaction_handler=handler)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app_pump.run_pump()

    # 3. Assert
    assert len(handler.captured_contexts) == 1
    ctx = handler.captured_contexts[0]

    assert ctx.violation_type == L.check.issue.conflict
    assert ctx.doc_diff is not None

    # Check for unified diff markers
    assert "--- yaml" in ctx.doc_diff
    assert "+++ code" in ctx.doc_diff
    assert "-YAML Doc" in ctx.doc_diff
    assert "+Code Doc" in ctx.doc_diff
~~~~~

#### Acts 4: 重构 `stitcher-cli` 集成测试

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_error_handling.py
~~~~~
~~~~~python
from typer.testing import CliRunner

from stitcher.cli.main import app
from stitcher.test_utils import SpyBus
from needle.pointer import L


def test_command_fails_gracefully_outside_workspace(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that running a command outside a valid workspace
    (no .git, no pyproject.toml) fails with a user-friendly error.
    """
    # Arrange: Create a directory that is NOT a valid workspace root.
    invalid_workspace = tmp_path / "not_a_project"
    subdir = invalid_workspace / "some_dir"
    subdir.mkdir(parents=True)

    # Change into the subdirectory to simulate running from a nested location
    monkeypatch.chdir(subdir)

    runner = CliRunner()

    # Act
    with spy_bus.patch(monkeypatch):
        result = runner.invoke(app, ["check"], catch_exceptions=False)

    # Assert
    assert result.exit_code == 1, "Command should exit with failure code"

    # Assert the correct, user-friendly error message was emitted
    spy_bus.assert_id_called(L.error.workspace.not_found, level="error")

    # Verify the message contains the path from where the command was run
    error_msg = next(
        (
            m
            for m in spy_bus.get_messages()
            if m["id"] == str(L.error.workspace.not_found)
        ),
        None,
    )
    assert error_msg is not None
    assert str(subdir) in error_msg["params"]["path"]
~~~~~

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_fidelity_principles.py
~~~~~
~~~~~python
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
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
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


def test_check_does_not_reformat_file_on_success(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that a successful `check` run does NOT reformat or reorder
    a .stitcher.yaml file that has custom, non-alphabetical key order.
    """
    # 1. ARRANGE
    # Create a workspace, run `init`, and then `strip` to get a truly
    # clean state (docs only in YAML).
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
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

    # Step 1.1: Create initial docs
    init_result = runner.invoke(app, ["init"], catch_exceptions=False)
    assert init_result.exit_code == 0

    # Step 1.2: Strip source to avoid "redundant" warnings
    # We pass "y\n" to auto-confirm the interactive prompt.
    strip_result = runner.invoke(app, ["strip"], input="y\n", catch_exceptions=False)
    assert strip_result.exit_code == 0

    # Step 1.3: Now, manually reorder the generated YAML to be non-standard
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
    with spy_bus.patch(monkeypatch):
        check_result = runner.invoke(app, ["check"], catch_exceptions=False)

    # 3. ASSERT
    assert check_result.exit_code == 0, check_result.stdout

    # Assert that the check reported true success (no warnings)
    spy_bus.assert_id_called(L.check.run.success)

    # The critical assertion: the file content must not have changed.
    content_after = yaml_path.read_text()
    assert content_before == content_after, (
        "Check command incorrectly reformatted the YAML file."
    )
~~~~~

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_loglevel_option.py
~~~~~
~~~~~python
from typer.testing import CliRunner

from stitcher.cli.main import app
from stitcher.test_utils import SpyBus
from needle.pointer import L, SemanticPointer

runner = CliRunner()


def assert_id_not_called(spy_bus: SpyBus, msg_id: SemanticPointer):
    """Helper to assert that a specific message ID was NOT called."""
    key = str(msg_id)
    for msg in spy_bus.get_messages():
        if msg["id"] == key:
            raise AssertionError(f"Message with ID '{key}' was unexpectedly sent.")


def test_loglevel_default_is_info(workspace_factory, monkeypatch, spy_bus: SpyBus):
    """Verifies the default loglevel (info) shows INFO and above, but not DEBUG."""
    workspace_factory.with_config({"scan_paths": ["src"]}).build()

    with spy_bus.patch(monkeypatch):
        result = runner.invoke(app, ["check"], catch_exceptions=False)

    assert result.exit_code == 0
    spy_bus.assert_id_called(L.index.run.start, level="info")
    spy_bus.assert_id_called(L.check.run.success, level="success")
    assert_id_not_called(spy_bus, L.debug.log.scan_path)


def test_loglevel_warning_hides_info_and_success(workspace_factory, monkeypatch, spy_bus: SpyBus):
    """Verifies --loglevel warning hides lower level messages."""
    # Setup a project with an untracked file, which triggers a WARNING
    workspace_factory.with_config({"scan_paths": ["src"]}).with_source(
        "src/main.py", "def func(): pass"
    ).build()

    with spy_bus.patch(monkeypatch):
        result = runner.invoke(
            app, ["--loglevel", "warning", "check"], catch_exceptions=False
        )

    # A warning does not cause a failure exit code
    assert result.exit_code == 0
    # INFO and the final SUCCESS summary should be hidden
    assert_id_not_called(spy_bus, L.index.run.start)
    assert_id_not_called(spy_bus, L.check.run.success)
    assert_id_not_called(spy_bus, L.check.run.success_with_warnings)

    # However, the specific WARNING messages should be visible.
    spy_bus.assert_id_called(L.check.file.warn, level="warning")
    spy_bus.assert_id_called(L.check.file.untracked_with_details, level="warning")


def test_loglevel_debug_shows_debug_messages(workspace_factory, monkeypatch, spy_bus: SpyBus):
    """Verifies --loglevel debug shows verbose debug messages."""
    workspace_factory.with_config({"scan_paths": ["src"]}).build()

    with spy_bus.patch(monkeypatch):
        result = runner.invoke(
            app, ["--loglevel", "debug", "check"], catch_exceptions=False
        )

    assert result.exit_code == 0
    spy_bus.assert_id_called(L.debug.log.scan_path, level="debug")
    spy_bus.assert_id_called(L.index.run.start, level="info")


def test_loglevel_error_shows_only_errors(workspace_factory, monkeypatch, spy_bus: SpyBus):
    """Verifies --loglevel error hides everything except errors."""
    # Setup a project with signature drift (ERROR) and an untracked file (WARNING)
    ws = workspace_factory.with_config({"scan_paths": ["src"]})
    ws.with_source("src/main.py", 'def func(a: int): """doc"""')
    ws.build()
    runner.invoke(app, ["init"], catch_exceptions=False)
    # Introduce signature drift
    (ws.root_path / "src/main.py").write_text('def func(a: str): """doc"""')
    # Add an untracked file to ensure its warning is suppressed
    (ws.root_path / "src/untracked.py").write_text("pass")

    with spy_bus.patch(monkeypatch):
        result = runner.invoke(
            app, ["--loglevel", "error", "check"], catch_exceptions=False
        )

    assert result.exit_code == 1
    # INFO, SUCCESS, WARNING messages should be hidden
    assert_id_not_called(spy_bus, L.index.run.start)
    assert_id_not_called(spy_bus, L.check.run.success)
    assert_id_not_called(spy_bus, L.check.file.untracked)

    # ERROR messages should be visible
    spy_bus.assert_id_called(L.check.run.fail, level="error")
    spy_bus.assert_id_called(L.check.state.signature_drift, level="error")
~~~~~

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py
~~~~~
~~~~~python
from typer.testing import CliRunner
from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L
from unittest.mock import MagicMock
from stitcher.cli.handlers import TyperInteractionHandler


def test_pump_prompts_for_strip_when_redundant(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that when 'pump' extracts docstrings (making source docs redundant),
    it prompts the user to strip them, and performs the strip if confirmed.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    # Create a file with a docstring that will be extracted
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            '''
def func():
    """This docstring should become redundant."""
    pass
''',
        )
        .build()
    )

    runner = CliRunner()

    # FORCE INTERACTIVE MODE:
    # Instead of fighting with sys.stdin.isatty(), we directly mock the factory
    # to return a real handler. This ensures pump_command sees 'handler' as truthy.
    # We use a dummy renderer because we rely on CliRunner's input injection, not the renderer's prompt logic.
    dummy_handler = TyperInteractionHandler(renderer=MagicMock())

    # We mock the factory function imported inside pump.py
    monkeypatch.setattr(
        "stitcher.cli.commands.pump.make_interaction_handler",
        lambda **kwargs: dummy_handler,
    )

    # 2. Act
    # Run pump without --strip, but provide 'y' to the potential prompt
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        # We need to change cwd so the CLI picks up the pyproject.toml
        monkeypatch.chdir(project_root)
        result = runner.invoke(app, ["pump"], input="y\n")

    # 3. Assert
    assert result.exit_code == 0

    # Critical Assertion:
    # If the prompt appeared and worked, 'run_strip' should have been called,
    # and it should have emitted a success message via the bus.
    # If this fails, it means the CLI never prompted or never executed the strip.
    spy_bus.assert_id_called(L.strip.run.complete, level="success")

    # Verify physical file content (docstring should be gone)
    content = (project_root / "src/main.py").read_text()
    assert '"""' not in content
    assert "pass" in content


def test_pump_with_strip_flag_executes_strip(tmp_path, monkeypatch, spy_bus: SpyBus):
    """
    Verifies that 'pump --strip' directly triggers a strip operation and
    emits the correct completion signal. This test bypasses interactive prompts.
    """
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.init_git()
        .with_config({"scan_paths": ["src"]})
        .with_source(
            "src/main.py",
            '''
def func():
    """This docstring should be stripped."""
    pass
''',
        )
        .build()
    )

    runner = CliRunner()

    # 2. Act
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        monkeypatch.chdir(project_root)
        result = runner.invoke(app, ["pump", "--strip"])

    # 3. Assert
    assert result.exit_code == 0, f"CLI command failed: {result.stdout}"

    # Assert that the strip operation was completed
    spy_bus.assert_id_called(L.strip.run.complete, level="success")

    # Verify physical file content
    content = (project_root / "src/main.py").read_text()
    assert '"""' not in content
~~~~~

~~~~~act
write_file
packages/stitcher-cli/tests/integration/test_refactor_command.py
~~~~~
~~~~~python
from typer.testing import CliRunner

from stitcher.cli.main import app
from stitcher.test_utils import WorkspaceFactory, SpyBus
from needle.pointer import L

runner = CliRunner()


def test_refactor_apply_e2e(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange: Create a project and a migration script
    factory = WorkspaceFactory(tmp_path)
    # Project with a symbol to be renamed
    (
        factory.init_git()
        .with_project_name("mypkg")
        .with_config({"scan_paths": ["src"]})
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

    # 2. Act
    monkeypatch.chdir(tmp_path)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = runner.invoke(
            app,
            ["refactor", "apply", str(migration_script), "--yes"],
            catch_exceptions=False,
        )

    # 3. Assert
    assert result.exit_code == 0, result.stdout
    spy_bus.assert_id_called(L.refactor.run.success)

    # Verify file changes
    core_py = tmp_path / "src/mypkg/core.py"
    app_py = tmp_path / "src/mypkg/app.py"
    assert "class New: pass" in core_py.read_text()
    assert "from mypkg.core import New" in app_py.read_text()


def test_refactor_apply_dry_run(tmp_path, monkeypatch, spy_bus: SpyBus):
    # 1. Arrange
    factory = WorkspaceFactory(tmp_path)
    (
        factory.init_git()
        .with_project_name("mypkg")
        .with_config({"scan_paths": ["src"]})
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

    # 2. Act
    monkeypatch.chdir(tmp_path)
    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        result = runner.invoke(
            app,
            ["refactor", "apply", str(migration_script), "--dry-run"],
            catch_exceptions=False,
        )

    # 3. Assert
    assert result.exit_code == 0, result.stdout
    spy_bus.assert_id_called(L.refactor.run.preview_header)

    # Assert success message was NOT called
    success_id = str(L.refactor.run.success)
    called_ids = [msg["id"] for msg in spy_bus.get_messages()]
    assert success_id not in called_ids

    # Verify NO file changes
    core_py = tmp_path / "src/mypkg/core.py"
    assert "class Old: pass" in core_py.read_text()
    assert "class New: pass" not in core_py.read_text()
~~~~~

### 下一步建议
我们已经完成了对所有现有测试文件的重构，统一使用了 `spy_bus` fixture。

由于这是一个大规模的测试代码重构，建议执行以下操作：
1. **全量测试验证**: 运行 `pytest` 确保所有测试依然通过，特别是验证 `SpyBus` 相关的断言是否正确执行。
2. **清理**: 检查是否还有漏网之鱼（虽然根据 `rg` 结果已经全量覆盖）。
3. **提交**: 如果测试通过，我将生成 `[COMMIT]` 计划。
