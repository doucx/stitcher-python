简要回答
我将手动对 `stitcher-refactor` 中的所有受影响测试进行批量修复。主要的修复策略是：在集成测试中使用 `create_populated_index` 初始化索引数据库，在单元测试中注入 Mock 的 `IndexStore`。

## [WIP] test: 修复 stitcher-refactor 测试套件以适配 IndexStore

### 用户需求
由于 `SemanticGraph` 和 `RefactorContext` 现在强制依赖 `IndexStore`，需要修补 `stitcher-refactor` 目录下的所有集成和单元测试，使其符合新的构造函数签名和内部逻辑（移除对 `registry` 的直接访问）。

### 评论
这次大规模修复是 Phase 3 的“阵痛期”。通过统一使用 `test-utils` 提供的工具，我们可以确保测试套件在架构融合后依然保持稳健，并能验证重构引擎是否正确地从数据库读取引用。

### 目标
1.  修复 `stitcher-refactor/tests/integration` 下的所有 14 个集成测试。
2.  修复 `stitcher-refactor/tests/unit` 下的所有受影响单元测试。
3.  重构 `test_usage_registry.py`，将其逻辑转向验证基于 DB 的引用查询。

### 基本原理
对于集成测试，我们通过“扫描并填充”来创建一个真实的测试环境；对于单元测试，我们通过 Mock 来隔离数据库依赖，确保测试焦点依然在逻辑转换上。

### 标签
#intent/tooling #flow/ready #priority/high #comp/refactor #comp/tests #scope/core #ai/instruct #task/domain/testing #task/object/test-suite #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 修复基础集成测试 (Bug Repro & Specific Scenarios)

我们将对 4 个处理特定 Bug 的集成测试文件应用补丁。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_bug_init_relative_import.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_module_referenced_by_init_relative_import(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_module_referenced_by_init_relative_import(tmp_path):
~~~~~
~~~~~python.old
    init_path = project_root / "mypkg/__init__.py"

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
    init_path = project_root / "mypkg/__init__.py"

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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_file_updates_relative_imports_and_scaffolds_init(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_file_updates_relative_imports_and_scaffolds_init(tmp_path):
~~~~~
~~~~~python.old
    usage_path = project_root / "mypkg/__init__.py"

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
    usage_path = project_root / "mypkg/__init__.py"

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
packages/stitcher-refactor/tests/integration/test_debug_rename_failure.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
from stitcher.common.transaction import WriteFileOp
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index
from stitcher.common.transaction import WriteFileOp
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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_smoking_gun_concurrent_modifications_lost_edit(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_smoking_gun_concurrent_modifications_lost_edit(tmp_path):
~~~~~
~~~~~python.old
    dest_path = project_root / "mypkg/utils.py"

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
    dest_path = project_root / "mypkg/utils.py"

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

#### Acts 2: 修复 Monorepo 集成测试

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_file_in_monorepo_updates_cross_package_imports(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_file_in_monorepo_updates_cross_package_imports(tmp_path):
~~~~~
~~~~~python.old
    consumer_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"

    # 2. ACT
    # The new SemanticGraph should automatically find both 'src' dirs
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
~~~~~
~~~~~python.new
    consumer_path = project_root / "packages/pkg_b/src/pkgb_app/main.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    # The new SemanticGraph should automatically find both 'src' dirs
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_file_in_monorepo_updates_tests_and_cross_package_imports(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_file_in_monorepo_updates_tests_and_cross_package_imports(tmp_path):
~~~~~
~~~~~python.old
    top_level_test_path = project_root / "tests/integration/test_full_system.py"

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Verify that all source and test roots were discovered
~~~~~
~~~~~python.new
    top_level_test_path = project_root / "tests/integration/test_full_system.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Verify that all source and test roots were discovered
~~~~~
~~~~~python.old
    graph.load("test_core")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    graph.load("test_core")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace,
        graph=graph,
        sidecar_manager=sidecar_manager,
        index_store=index_store,
    )
~~~~~

#### Acts 3: 修复目录和文件移动集成测试

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_directory_updates_all_contents_and_references(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_directory_updates_all_contents_and_references(tmp_path):
~~~~~
~~~~~python.old
    sig_root = project_root / ".stitcher/signatures"

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
    sig_root = project_root / ".stitcher/signatures"

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

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_directory_in_monorepo_updates_cross_package_references(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_directory_in_monorepo_updates_cross_package_references(tmp_path):
~~~~~
~~~~~python.old
    consumer_path = project_root / "cascade-runtime/src/cascade/runtime/app.py"

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    consumer_path = project_root / "cascade-runtime/src/cascade/runtime/app.py"

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_file_flat_layout(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_file_flat_layout(tmp_path):
~~~~~
~~~~~python.old
    new_py = pkg_dir / "new.py"

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
    new_py = pkg_dir / "new.py"

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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_move_deeply_nested_directory_updates_all_references_and_sidecars(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_move_deeply_nested_directory_updates_all_references_and_sidecars(tmp_path):
~~~~~
~~~~~python.old
    app_py_path = project_root / "src/app.py"

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
    app_py_path = project_root / "src/app.py"

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

#### Acts 4: 修复重命名集成测试

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_namespace_pkg_failure.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_rename_symbol_in_namespace_package_structure(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_rename_symbol_in_namespace_package_structure(tmp_path):
~~~~~
~~~~~python.old
    main_file = project_root / "packages/stitcher-core/src/stitcher/core/main.py"

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
    main_file = project_root / "packages/stitcher-core/src/stitcher/core/main.py"

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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_rename_fails_to_update_definition_leading_to_import_error(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_rename_fails_to_update_definition_leading_to_import_error(tmp_path):
~~~~~
~~~~~python.old
    usage_file = project_root / "common/__init__.py"

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
    usage_file = project_root / "common/__init__.py"

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
~~~~~python.old
    definition_file = project_root / "mypkg/core.py"
    usage_file = project_root / "mypkg/app.py"

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
    definition_file = project_root / "mypkg/core.py"
    usage_file = project_root / "mypkg/app.py"

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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_rename_symbol_in_monorepo_updates_all_references_and_sidecars(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_rename_symbol_in_monorepo_updates_all_references_and_sidecars(tmp_path):
~~~~~
~~~~~python.old
    )

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("pkga_lib")
~~~~~
~~~~~python.new
    )

    # 2. ACT
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("pkga_lib")
~~~~~
~~~~~python.old
    graph.load("integration")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~
~~~~~python.new
    graph.load("integration")
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
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_rename_symbol_via_attribute_access(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index


def test_rename_symbol_via_attribute_access(tmp_path):
~~~~~
~~~~~python.old
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
~~~~~python.old
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

#### Acts 5: 修复核心图谱与 Registry 测试

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_semantic_graph.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.workspace import Workspace


def test_semantic_graph_load_package(tmp_path):
~~~~~
~~~~~python.new
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import create_populated_index


def test_semantic_graph_load_package(tmp_path):
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

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_usage_registry.py
~~~~~
~~~~~python
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import create_populated_index

def test_usage_query_via_index(tmp_path):
    """验证 SemanticGraph.find_usages 正确从 Index DB 获取引用。"""
    # 1. ARRANGE
    (tmp_path / "pyproject.toml").write_text("[project]\nname='test-proj'")
    pkg_dir = tmp_path / "mypkg"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    (pkg_dir / "core.py").write_text("class Helper:\n    pass", encoding="utf-8")
    (pkg_dir / "app.py").write_text(
        "from mypkg.core import Helper as H\n\ndef main():\n    obj = H()",
        encoding="utf-8",
    )

    # 2. ACT
    index_store = create_populated_index(tmp_path)
    workspace = Workspace(root_path=tmp_path)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")

    # 3. ASSERT
    # 我们查询 'mypkg.core.Helper'
    usages = graph.find_usages("mypkg.core.Helper")

    # 我们期望找到：
    # 1. app.py 中的导入：'Helper' as H (ReferenceRecord)
    # 2. app.py 中的使用：'H()'
    
    app_usages = [u for u in usages if u.file_path.name == "app.py"]
    assert len(app_usages) >= 2
    
    # 验证位置信息是否正确
    call_usage = next(u for u in app_usages if u.lineno == 4)
    assert call_usage.col_offset == 10 # H()
~~~~~

#### Acts 6: 修复单元测试 (Mock 索引)

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/engine/test_graph.py
~~~~~
~~~~~python.old
def test_semantic_graph_get_module_nested_lookup(tmp_path):
    """
    Verifies that get_module can navigate the module tree to find submodules.
    """
    # 1. ARRANGE: Create a nested package structure
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/utils/__init__.py", "")
        .with_source("mypkg/utils/math.py", "def add(a, b): return a + b")
        .build()
    )

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
~~~~~
~~~~~python.new
from unittest.mock import MagicMock
from stitcher.index.store import IndexStore

def test_semantic_graph_get_module_nested_lookup(tmp_path):
    """
    Verifies that get_module can navigate the module tree to find submodules.
    """
    # 1. ARRANGE: Create a nested package structure
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source("mypkg/utils/__init__.py", "")
        .with_source("mypkg/utils/math.py", "def add(a, b): return a + b")
        .build()
    )

    # 2. ACT
    workspace = Workspace(root_path=project_root)
    mock_index = MagicMock(spec=IndexStore)
    graph = SemanticGraph(workspace=workspace, index_store=mock_index)
    graph.load("mypkg")
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/engine/test_planner.py
~~~~~
~~~~~python.old
def test_planner_collects_intents_from_operations():
    # 1. Arrange
    mock_ctx = Mock(spec=RefactorContext)
    mock_spec = Mock(spec=MigrationSpec)
~~~~~
~~~~~python.new
from stitcher.index.store import IndexStore

def test_planner_collects_intents_from_operations():
    # 1. Arrange
    mock_index = Mock(spec=IndexStore)
    mock_ctx = Mock(spec=RefactorContext)
    mock_ctx.index_store = mock_index
    mock_spec = Mock(spec=MigrationSpec)
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
from stitcher.python.analysis.cst.usage_visitor import UsageRegistry
from stitcher.python.analysis.models import UsageLocation, ReferenceType
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.common.transaction import WriteFileOp
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace


def test_rename_symbol_analyze_orchestration():
    # 1. Setup Mocks
    mock_registry = Mock(spec=UsageRegistry)
    mock_graph = Mock(spec=SemanticGraph)
    mock_graph.registry = mock_registry
~~~~~
~~~~~python.new
from stitcher.index.store import IndexStore
from stitcher.python.analysis.models import UsageLocation, ReferenceType
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.common.transaction import WriteFileOp
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace


def test_rename_symbol_analyze_orchestration():
    # 1. Setup Mocks
    mock_index = Mock(spec=IndexStore)
    mock_graph = Mock(spec=SemanticGraph)
    # mock_graph.registry is gone, the renamer now calls graph.find_usages
~~~~~
~~~~~python.old
    ctx = RefactorContext(
        graph=mock_graph,
        workspace=mock_workspace,
        sidecar_manager=mock_sidecar_manager,
    )
~~~~~
~~~~~python.new
    ctx = RefactorContext(
        graph=mock_graph,
        workspace=mock_workspace,
        sidecar_manager=mock_sidecar_manager,
        index_store=mock_index,
    )
~~~~~
~~~~~python.old
    locations = [
        UsageLocation(
            file_a_path,
            1,
            23,
            1,
            32,
            ReferenceType.IMPORT_PATH,
            "mypkg.core.OldHelper",
        ),
        UsageLocation(
            file_a_path, 3, 6, 3, 15, ReferenceType.SYMBOL, "mypkg.core.OldHelper"
        ),
        UsageLocation(
            file_b_path,
            2,
            27,
            2,
            36,
            ReferenceType.IMPORT_PATH,
            "mypkg.core.OldHelper",
        ),
        UsageLocation(
            file_b_path,
            3,
            11,
            3,
            20,
            ReferenceType.SYMBOL,
            "mypkg.core.OldHelper",
        ),
    ]

    mock_registry.get_usages.return_value = locations
~~~~~
~~~~~python.new
    locations = [
        UsageLocation(
            file_a_path,
            1,
            23,
            1,
            32,
            ReferenceType.IMPORT_PATH,
            "mypkg.core.OldHelper",
        ),
        UsageLocation(
            file_a_path, 3, 6, 3, 15, ReferenceType.SYMBOL, "mypkg.core.OldHelper"
        ),
        UsageLocation(
            file_b_path,
            2,
            27,
            2,
            36,
            ReferenceType.IMPORT_PATH,
            "mypkg.core.OldHelper",
        ),
        UsageLocation(
            file_b_path,
            3,
            11,
            3,
            20,
            ReferenceType.SYMBOL,
            "mypkg.core.OldHelper",
        ),
    ]

    mock_graph.find_usages.return_value = locations
~~~~~

### 下一步建议

我们已经完成了 `stitcher-refactor` 所有内部测试的初步修复。
下一步是：
1.  **运行测试**：验证集成测试是否能正确扫描文件并查询 DB。
2.  **单元测试精修**：如果某些单元测试仍然失败，检查其对 `UsageRegistry` 的残留依赖。
3.  **开始 Application 层修复**：一旦核心库测试通过，修改 `stitcher-application` 中的 `StitcherApp`，使其在执行重构前确保索引是新鲜的。
