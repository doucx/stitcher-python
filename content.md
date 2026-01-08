好的，我来修复这个测试。

## [WIP] fix(tests): 适配事务系统重构导致的测试失败

### 错误分析

在将 `GenerateRunner` 等核心组件重构为使用 `TransactionManager` 后，`GenerateRunner.run_batch` 方法的签名发生了变化，增加了一个必需的 `tm` (TransactionManager 实例) 参数。

测试用例 `test_app_scan_and_generate_single_file` 直接调用了 `app.generate_runner.run_batch`，但没有提供这个新的 `tm` 参数，从而导致 `TypeError`。

此外，由于文件写入逻辑已移至 `TransactionManager.commit()`，该测试仅调用 `run_batch` 是不够的，它只注册了文件操作意图，并未实际执行。为了使测试能够验证文件是否真的被创建，必须在调用 `run_batch` 后显式调用 `tm.commit()`。

### 用户需求

修复因 `GenerateRunner.run_batch` 签名变更而失败的集成测试 `test_app_scan_and_generate_single_file`。

### 评论

这是一个预料之中的测试失败，它验证了我们的重构确实改变了组件间的契约。修复这个测试不仅能解决当前的 CI 问题，还能通过引入对 `TransactionManager` 的显式使用，使测试用例更好地反映重构后的系统架构。同时，我也将增强该测试，使其不仅检查日志消息，还断言物理文件确实被成功创建，提高了测试的覆盖率和健壮性。

### 目标

1.  修改 `packages/stitcher-application/tests/integration/test_end_to_end.py`。
2.  在 `test_app_scan_and_generate_single_file` 测试中，创建一个 `TransactionManager` 实例。
3.  将此实例传递给 `app.generate_runner.run_batch` 调用。
4.  在调用后，执行 `tm.commit()` 以应用文件变更。
5.  增加一个 `assert` 语句，验证 `.pyi` 文件是否被成功创建。

### 基本原理

对于直接测试 Runner 的集成测试，我们需要手动模拟 `StitcherApp` 的行为：即在调用 Runner 的 `run_batch` 方法之前创建 `TransactionManager`，并在之后调用 `commit`。这确保了测试环境与实际运行时的控制流程保持一致。对于那些调用 `app.run_*` 方法的测试，则不需要修改，因为 `TransactionManager` 的生命周期管理已经封装在 `StitcherApp` 内部。

### 标签

#intent/fix #flow/ready #priority/high
#comp/application #comp/tests #scope/core
#ai/instruct
#task/domain/architecture #task/object/transaction-system #task/action/integration #task/state/continue #task/status/active

---

### Script

#### Acts 1: 修复并增强集成测试

我将使用 `write_file` 完整更新测试文件。此更新包含三项改动：
1.  导入 `TransactionManager`。
2.  在 `test_app_scan_and_generate_single_file` 中实例化 `TransactionManager` 并更新对 `run_batch` 的调用。
3.  在该测试中增加对生成文件的存在性断言。

~~~~~act
write_file
packages/stitcher-application/tests/integration/test_end_to_end.py
~~~~~
~~~~~python
import sys

from stitcher.test_utils import create_test_app
from stitcher.config import StitcherConfig
from needle.pointer import L
from stitcher.test_utils import SpyBus, WorkspaceFactory
from stitcher.common.transaction import TransactionManager


def test_app_scan_and_generate_single_file(tmp_path, monkeypatch):
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
    spy_bus = SpyBus()
    tm = TransactionManager(root_path=project_root)

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        # Directly call the runner's batch processing method to test generation logic in isolation.
        source_file = project_root / "greet.py"
        module = app.scanner.scan_files([source_file])[0]
        app.generate_runner.run_batch([module], StitcherConfig(), tm)
        tm.commit()

    spy_bus.assert_id_called(L.generate.file.success, level="success")

    error_messages = [m for m in spy_bus.get_messages() if m["level"] == "error"]
    assert not error_messages, f"Found unexpected error messages: {error_messages}"

    assert (project_root / "greet.pyi").exists()


def test_app_run_from_config_with_source_files(tmp_path, monkeypatch):
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
    spy_bus = SpyBus()

    with spy_bus.patch(monkeypatch, "stitcher.common.bus"):
        app.run_from_config()

    spy_bus.assert_id_called(L.generate.file.success, level="success")
    spy_bus.assert_id_called(L.generate.run.complete, level="success")

    success_messages = [m for m in spy_bus.get_messages() if m["level"] == "success"]
    # 2 files generated (main.py, helpers.py), 1 run complete message
    assert len(success_messages) == 3


def test_app_run_multi_target(tmp_path, monkeypatch):
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
    spy_bus = SpyBus()

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


def test_app_generates_stubs_for_plugins_and_sources(tmp_path, monkeypatch):
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
        spy_bus = SpyBus()

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
        assert len(success_messages) == 4

    finally:
        # Cleanup sys.path
        sys.path.pop(0)
~~~~~

### 下一步建议

测试已修复。现在我们可以安全地继续推进重构路线图中的下一步：在 CLI 层面为受影响的命令（`generate`, `pump`, `strip`, `inject`）添加 `--dry-run` 选项，并将该选项的值传递给 `StitcherApp`。
