好的，分析完成。`AttributeError` 的根本原因是我在上一步重构 `SidecarManager` 时，只改变了它的 `__init__` 方法（从接收 `root_path` 到接收 `workspace` 对象），却没有同步更新所有调用它的测试文件。

这是一个典型的、因重构不彻底而导致的连锁失败。根据 `HFEA` 的“回归驱动开发”和“异味即缺陷”原则，我们必须修复所有这些不一致的调用点，以强制执行新的、正确的架构约定。

我将生成一个计划，逐一修复 `rg` 命令找到的所有不正确的 `SidecarManager` 实例化代码。

## [WIP] fix: 在整个测试套件中强制使用 Workspace 对象初始化 SidecarManager

### 错误分析
`SidecarManager.__init__` 的签名已从 `(self, root_path: Path)` 更改为 `(self, workspace: Workspace)`。然而，大量的集成测试文件仍然在使用旧的 `SidecarManager(root_path=project_root)` 方式进行实例化。这导致一个 `Path` 对象被错误地赋给了 `self.workspace` 属性。当后续代码尝试访问 `self.workspace.root_path` 时，由于 `Path` 对象没有 `root_path` 属性，从而引发了 `AttributeError`。

### 用户需求
修复所有 `SidecarManager` 的实例化，使其符合新的构造函数签名，从而解决 `AttributeError` 并让测试通过。

### 评论
这是一个必要的清理步骤，旨在确保整个代码库与新的架构设计保持一致。通过修复这些调用点，我们能巩固 `Workspace` 作为处理路径和项目布局的“真理单一来源”(SSoT) 的地位。

### 目标
1.  定位所有使用 `SidecarManager(root_path=...)` 语法的测试文件。
2.  将这些调用修改为 `SidecarManager(workspace=...)`。
3.  在必要时，创建 `Workspace` 对象以传递给构造函数。

### 基本原理
大多数受影响的集成测试已经创建了一个 `Workspace` 对象用于 `RefactorContext`。因此，修复措施主要是将这个已存在的 `workspace` 对象传递给 `SidecarManager`。对于少数没有 `Workspace` 对象的测试，我们将即时创建一个，以满足新的 API 契约。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #comp/tests #scope/dx #ai/instruct #task/domain/architecture #task/object/sidecar-manager #task/action/enforce-contract #task/state/continue

---

### Script

#### Acts 1: 修复 `stitcher-refactor` 测试中的 SidecarManager 实例化

我们将根据 `rg` 的输出，逐一修复 `stitcher-refactor` 包内的所有测试文件。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_bug_init_relative_import.py
~~~~~
~~~~~python.old
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("mypkg")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_definition.py
~~~~~
~~~~~python.old
    graph.load("common")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("common")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_definition.py
~~~~~
~~~~~python.old
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("mypkg")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_namespace_pkg_failure.py
~~~~~
~~~~~python.old
    # Load the namespace package. Griffe should traverse 'stitcher' -> 'core'
    graph.load("stitcher")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    # Load the namespace package. Griffe should traverse 'stitcher' -> 'core'
    graph.load("stitcher")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_fail_concurrent_move_and_rename.py
~~~~~
~~~~~python.old
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("mypkg")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_bug_relative_import_refactor.py
~~~~~
~~~~~python.old
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("mypkg")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~
~~~~~python.old
def test_rename_symbol_via_attribute_access(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldHelper: pass")
        .with_source(
            "main.py",
            """
            import mypkg.core

            h = mypkg.core.OldHelper()
            """,
        )
        .build()
    )

    # 2. Analyze
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
def test_rename_symbol_via_attribute_access(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
        .with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/core.py", "class OldHelper: pass")
        .with_source(
            "main.py",
            """
            import mypkg.core

            h = mypkg.core.OldHelper()
            """,
        )
        .build()
    )

    # 2. Analyze
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~
~~~~~python.old
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~
~~~~~python.old
    graph.load("integration")
    # Also load the test module from pkg_a
    graph.load("test_core")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    graph.load("integration")
    # Also load the test module from pkg_a
    graph.load("test_core")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_repro_sidecar_fqn.py
~~~~~
~~~~~python.old
    # Load top level to ensure graph coverage
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~
~~~~~python.new
    # Load top level to ensure graph coverage
    graph.load("mypkg")

    sidecar_manager = SidecarManager(workspace=workspace)
    ctx = RefactorContext(
        workspace=workspace,
~~~~~

#### Acts 2: 修复 `stitcher-application` 中的 SidecarManager 实例化

这个在 `runners` 模块中，需要创建 `Workspace` 对象。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python.old
            sidecar_manager = SidecarManager(self.root_path)
~~~~~
~~~~~python.new
            sidecar_manager = SidecarManager(workspace)
~~~~~

### 下一步建议
我们已经完成了对所有 `SidecarManager` 实例化点的修复。现在，整个代码库都应该遵循了新的架构约定。

请重新运行完整的测试套件。我预计之前与 `refactor` 相关的 `AttributeError` 和其他连锁失败都已解决。
