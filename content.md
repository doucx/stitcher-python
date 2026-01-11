简要回答
好的，我将作为“人类脚本”，手动对这 22 个失败的测试用例进行批量修复。核心策略是在每个测试的 Arrange 阶段利用 `create_populated_index` 构建真实的索引环境，并确保 `SemanticGraph` 和 `RefactorContext` 能够正确持有这个 `index_store`。

## [WIP] fix: 批量修复 Refactor 测试套件以集成 IndexStore

### 错误分析
随着 Phase 3 架构融合的推进，`SemanticGraph` 和 `RefactorContext` 已演进为依赖 `IndexStore` 提供语义查询服务。现有的测试用例仍在使用旧的构造函数，缺少 `index_store` 参数，导致 `TypeError`。

### 用户需求
批量修复 `stitcher-refactor` 包下的所有集成测试和单元测试，使其符合新的 API 契约。

### 评论
虽然修复数量较多，但模式高度统一。这是架构升级后的必然代价。通过这次修复，所有的重构测试都将运行在真实的 SQLite 索引之上，这不仅修复了报错，还显著提升了测试的真实度和对未来“确定性重构”的保障。

### 目标
1.  对 `packages/stitcher-refactor` 下的 17 个测试文件进行 `patch_file` 操作。
2.  集成测试：使用 `create_populated_index` 初始化真实 DB。
3.  单元测试：使用 `unittest.mock` 注入 Mock 索引。

### 基本原理
对于集成测试，我们遵循“基础设施优先”公理，使用 `test-utils` 提供的工业级工具构建环境。对于单元测试，我们通过 Mock 隔离复杂的 I/O，重点验证 `RefactorContext` 的协调逻辑。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/refactor-suite #task/action/fix-all #task/state/continue

---

### Script

#### Acts 1: 修复 Integration Tests (1/3) - 基础 Bug 复现类

修复 `test_repro_sidecar_fqn.py`, `test_bug_init_relative_import.py`, `test_bug_relative_import_refactor.py`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_repro_sidecar_fqn.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_repro_sidecar_keys_should_remain_short_names_after_directory_move(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_repro_sidecar_keys_should_remain_short_names_after_directory_move(tmp_path):
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_repro_sidecar_fqn.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Load top level to ensure graph coverage
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Load top level to ensure graph coverage
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_bug_init_relative_import.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_bug_relative_import_refactor.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

#### Acts 2: 修复 Integration Tests (2/3) - 核心功能 E2E 类

修复 `test_debug_rename_failure.py`, `test_fail_concurrent_move_and_rename.py`, `test_monorepo_refactor_e2e.py`, `test_monorepo_refactor_with_tests_e2e.py`, `test_move_directory_e2e.py`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~
~~~~~python.old
    # 2. LOAD GRAPH
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("stitcher")

    # 3. EXECUTE REFACTOR
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. LOAD GRAPH
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("stitcher")

    # 3. EXECUTE REFACTOR
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_fail_concurrent_move_and_rename.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    # The new SemanticGraph should automatically find both 'src' dirs
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
~~~~~
~~~~~python.new
    # 2. ACT
    # The new SemanticGraph should automatically find both 'src' dirs
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Verify that all source and test roots were discovered
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Verify that all source and test roots were discovered
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~
~~~~~python.old
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
    # 2. ANALYSIS
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ANALYSIS
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

#### Acts 3: 修复 Integration Tests (3/3) - 目录、文件及命名空间

修复 `test_move_directory_monorepo_e2e.py`, `test_move_file_e2e.py`, `test_move_nested_directory_e2e.py`, `test_rename_namespace_pkg_failure.py`, `test_rename_symbol_definition.py`, `test_rename_symbol_monorepo_e2e.py`, `test_rename_transformer_advanced.py`, `test_semantic_graph.py`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Load the top-level namespace package. Griffe will discover all its parts
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Load the top-level namespace package. Griffe will discover all its parts
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python.old
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
    # 2. Analyze
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. Analyze
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_namespace_pkg_failure.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)

    # Load the namespace package. Griffe should traverse 'stitcher' -> 'core'
    graph.load("stitcher")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)

    # Load the namespace package. Griffe should traverse 'stitcher' -> 'core'
    graph.load("stitcher")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_definition.py
~~~~~
~~~~~python.old
    # 2. ACT: Run the refactoring operation.
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("common")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT: Run the refactoring operation.
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("common")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_definition.py
~~~~~
~~~~~python.old
    # 2. ACT: Run the refactoring operation.
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. ACT: Run the refactoring operation.
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("pkga_lib")
~~~~~
~~~~~python.new
    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("pkga_lib")
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
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
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
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
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~
~~~~~python.old
    # 2. Analyze
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    # 2. Analyze
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    graph.load("main")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_semantic_graph.py
~~~~~
~~~~~python.old
    # 2. Execute: Load into SemanticGraph
    workspace = Workspace(root_path=tmp_path)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
~~~~~
~~~~~python.new
    # 2. Execute: Load into SemanticGraph
    index_store = create_populated_index(tmp_path)
    workspace = Workspace(root_path=tmp_path)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
~~~~~

#### Acts 4: 修复单元测试 (Mock 模式)

修复 `test_rename_operation.py`。注意这里需要同步更新 `mock_graph.find_usages`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    ctx = RefactorContext(
        graph=mock_graph,
        workspace=mock_workspace,
        sidecar_manager=mock_sidecar_manager,
    )

    # 2. Define Test Data
~~~~~
~~~~~python.new
    ctx = RefactorContext(
        graph=mock_graph,
        workspace=mock_workspace,
        sidecar_manager=mock_sidecar_manager,
        index_store=mock_index,
    )

    # 2. Define Test Data
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
            "mypkg.core.OldHelper",
        ),
    ]

    mock_registry.get_usages.return_value = locations

    # Configure the mock graph for the _find_definition_node logic
~~~~~
~~~~~python.new
            "mypkg.core.OldHelper",
        ),
    ]

    mock_graph.find_usages.return_value = locations

    # Configure the mock graph for the _find_definition_node logic
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    # 4. Verify
    # The planner will get usages for the old_fqn and potentially its prefixes.
    # We can check that it was called with the specific FQN.
    mock_registry.get_usages.assert_any_call(old_fqn)

    # We expect 2 code change ops + potentially sidecar ops
~~~~~
~~~~~python.new
    # 4. Verify
    # The planner will get usages for the old_fqn and potentially its prefixes.
    # We can check that it was called with the specific FQN.
    mock_graph.find_usages.assert_any_call(old_fqn)

    # We expect 2 code change ops + potentially sidecar ops
~~~~~

### 下一步建议
我们已经批量完成了所有失败测试的 API 适配。现在的关键步骤是运行这些测试。

根据 Phase 3 的目标，如果这些测试全部通过，说明 `stitcher-refactor` 已经成功地从“自研扫描”切换到了“基于索引查询”模式。如果出现非 `TypeError` 的失败，那很可能是因为 Linker 在某些复杂场景（如 monorepo 跨包链接）下的逻辑还需要微调。

运行测试命令：
`pytest packages/stitcher-refactor/tests`
