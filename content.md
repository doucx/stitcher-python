好的，我已经分析了代码库。在集成测试中一致使用 `workspace_factory` 插件（fixture）是符合 **HFEA v1.0** 协议中“基础设施优先”和“架构不可腐蚀性”原则的。通过消除手动实例化，我们确保了测试环境生命周期管理的统一，并减少了冗余代码。

以下是执行此重构的计划。

## [WIP] refactor: 在集成测试中统一使用 workspace_factory 插件

### 用户需求
将项目中手动实例化 `WorkspaceFactory(root_path=tmp_path)` 的集成测试重构为直接使用 Pytest 提供的 `workspace_factory` 插件。

### 评论
这是一个重要的开发者体验（DX）改进。通过将 `WorkspaceFactory` 的生命周期委托给 Pytest 插件，我们不仅简化了测试代码，还确保了所有集成测试都遵循相同的临时目录清理和环境配置逻辑。

### 目标
1. 识别并定位手动实例化 `WorkspaceFactory` 的测试函数。
2. 修改函数签名以接受 `workspace_factory` 插件。
3. 移除函数体内的手动实例化逻辑。
4. 确保受影响的路径计算逻辑（如 `pkg_a_root`）通过工厂的属性或返回值正确获得。

### 基本原理
根据 `stitcher-test-utils` 的设计，`workspace_factory` 插件已经在 `conftest.py` 中被定义为返回一个预配置了 `tmp_path` 的 `WorkspaceFactory` 实例。因此，在测试中再次手动创建它是重复且易错的。通过重构，我们利用了插件的依赖注入特性。

### 标签
#intent/refine #flow/ready #priority/medium #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/workspace-factory-fixture #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 `stitcher-application` 的集成测试

我们将修改 `test_check_ignores_reexports.py`，移除 `tmp_path` 并改用 `workspace_factory`。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_ignores_reexports.py
~~~~~
~~~~~python.old
def test_check_ignores_reexports_and_imports(tmp_path: Path, monkeypatch):
    """
    Verifies that 'stitcher check' correctly ignores:
    1. Symbols re-exported from another module in the same package.
    2. Standard library imports.
    It should only flag symbols physically defined in the file being checked.
    """
    # 1. Setup: Create a project with a re-export structure
    workspace_factory = WorkspaceFactory(tmp_path)
    spy_bus = SpyBus()
~~~~~
~~~~~python.new
def test_check_ignores_reexports_and_imports(workspace_factory: WorkspaceFactory, monkeypatch):
    """
    Verifies that 'stitcher check' correctly ignores:
    1. Symbols re-exported from another module in the same package.
    2. Standard library imports.
    It should only flag symbols physically defined in the file being checked.
    """
    # 1. Setup: Create a project with a re-export structure
    spy_bus = SpyBus()
~~~~~

#### Acts 2: 重构 `stitcher-refactor` 的集成测试

我们将修改 `test_refactor_move_updates_suri_in_signatures.py`。为了使代码更简洁，我们将 `pkg_a_root` 的定义移动到 `workspace_factory.build()` 之后，利用其返回的路径。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_refactor_move_updates_suri_in_signatures.py
~~~~~
~~~~~python.old
def test_move_file_operation_updates_suri_in_lockfile(tmp_path: Path):
    pkg_a_root = tmp_path / "packages" / "pkg-a"
    workspace_factory = WorkspaceFactory(root_path=tmp_path)
    workspace_root = (
        workspace_factory.with_config({"scan_paths": ["packages/pkg-a/src"]})
        .with_pyproject("packages/pkg-a")
        .with_source(
            "packages/pkg-a/src/my_app/logic.py",
            'def do_something():\n    """Doc"""\n    pass',
        )
        .build()
    )
~~~~~
~~~~~python.new
def test_move_file_operation_updates_suri_in_lockfile(workspace_factory: WorkspaceFactory):
    workspace_root = (
        workspace_factory.with_config({"scan_paths": ["packages/pkg-a/src"]})
        .with_pyproject("packages/pkg-a")
        .with_source(
            "packages/pkg-a/src/my_app/logic.py",
            'def do_something():\n    """Doc"""\n    pass',
        )
        .build()
    )
    pkg_a_root = workspace_root / "packages" / "pkg-a"
~~~~~

### 下一步建议
- **运行测试**: 执行 `pytest packages/stitcher-application/tests/integration packages/stitcher-refactor/tests/integration` 以验证重构是否成功且未破坏功能。
- **全局检查**: 如果项目中还存在类似的测试文件（目前分析中已涵盖主要部分），应继续应用此模式。
- **提交变更**: 在验证通过后，将这些改动作为一个 `refactor(tests)` 提交。
