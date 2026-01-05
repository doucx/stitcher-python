好的，我明白了。 `stitcher-refactor` 包中的 API 发生了变更，导致 `SemanticGraph` 和 `RefactorContext` 的初始化方式不再兼容，进而引发了大量的测试失败。

我的任务是修复所有这些测试，使其与新的 API 签名保持一致。

## [WIP] fix: 修复重构引擎测试套件以适配新的 API

### 错误分析

测试套件的失败主要源于两个相关的 API 变更：

1.  **`SemanticGraph.__init__` 变更**: `SemanticGraph` 的构造函数不再接受 `root_path` 参数，而是要求传入一个 `Workspace` 对象。所有直接使用 `SemanticGraph(root_path=...)` 的测试因此失败。
2.  **`RefactorContext.__init__` 变更**: `RefactorContext` 数据类现在要求在构造时必须提供 `workspace`、`graph` 和 `sidecar_manager` 三个参数。所有只提供 `graph` 的测试因此失败。

### 用户需求

用户要求修复所有因上述 API 变更而失败的测试用例。

### 评论

这是一个典型的由于核心组件接口重构而导致的级联测试失败场景。修复方案是统一的：在每个测试用例中，遵循新的对象构造顺序，即先创建 `Workspace` 和 `SidecarManager`，然后用它们来构造 `SemanticGraph` 和 `RefactorContext`。

### 目标

1.  修改所有集成测试，以正确的方式初始化 `Workspace`, `SemanticGraph`, `SidecarManager`, 和 `RefactorContext`。
2.  修改单元测试 `test_rename_symbol_analyze_orchestration`，为其提供 `RefactorContext` 所需的 `workspace` 和 `sidecar_manager` 的 Mock 对象。
3.  确保整个测试套件恢复通过状态。

### 基本原理

我将遵循“组合优于继承”的原则，在每个测试的 `Arrange` 或 `Act` 阶段，按照依赖顺序显式地创建所需的服务对象 (`Workspace`, `SidecarManager`)，并将它们注入到依赖它们的对象中 (`SemanticGraph`, `RefactorContext`)。对于单元测试，我将使用 `unittest.mock.Mock` 来提供这些依赖，并对其进行适当配置以隔离被测单元。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/test-suite #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复 `test_monorepo_refactor_e2e.py`

首先，更新导入语句，然后修改测试主体以正确创建 `Workspace`, `SemanticGraph` 和 `RefactorContext`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_e2e.py
~~~~~
~~~~~python.old
    # The new SemanticGraph should automatically find both 'src' dirs
    graph = SemanticGraph(root_path=project_root)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths

    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    ctx = RefactorContext(graph=graph)

    op = MoveFileOperation(src_path, dest_path)
~~~~~
~~~~~python.new
    # The new SemanticGraph should automatically find both 'src' dirs
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths

    # Load all packages
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    op = MoveFileOperation(src_path, dest_path)
~~~~~

#### Acts 2: 修复 `test_monorepo_refactor_with_tests_e2e.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_monorepo_refactor_with_tests_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    graph = SemanticGraph(root_path=project_root)
    # Verify that all source and test roots were discovered
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_a/tests" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths
    assert project_root / "tests" in graph.search_paths

    # Load all relevant modules
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    graph.load("integration")
    # Also load the test module from pkg_a
    graph.load("test_core")

    ctx = RefactorContext(graph=graph)
    op = MoveFileOperation(src_path, dest_path)
~~~~~
~~~~~python.new
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    # Verify that all source and test roots were discovered
    assert project_root / "packages/pkg_a/src" in graph.search_paths
    assert project_root / "packages/pkg_a/tests" in graph.search_paths
    assert project_root / "packages/pkg_b/src" in graph.search_paths
    assert project_root / "tests" in graph.search_paths

    # Load all relevant modules
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    graph.load("integration")
    # Also load the test module from pkg_a
    graph.load("test_core")

    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
    op = MoveFileOperation(src_path, dest_path)
~~~~~

#### Acts 3: 修复 `test_move_directory_e2e.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
    # 2. ANALYSIS
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    graph.load("app")
    ctx = RefactorContext(graph=graph)

    op = MoveDirectoryOperation(core_dir, services_dir)
~~~~~
~~~~~python.new
    # 2. ANALYSIS
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    graph.load("app")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    op = MoveDirectoryOperation(core_dir, services_dir)
~~~~~

#### Acts 4: 修复 `test_move_file_e2e.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager, MoveFileOp
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_file_e2e.py
~~~~~
~~~~~python.old
    # 2. Analyze
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    ctx = RefactorContext(graph=graph)
    op = MoveFileOperation(old_py, new_py)
~~~~~
~~~~~python.new
    # 2. Analyze
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
    op = MoveFileOperation(old_py, new_py)
~~~~~

#### Acts 5: 修复 `test_move_nested_directory_e2e.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import (
    DeleteDirectoryOp,
    MoveFileOp,
    TransactionManager,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import (
    DeleteDirectoryOp,
    MoveFileOp,
    TransactionManager,
)
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_nested_directory_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    graph = SemanticGraph(root_path=project_root)
    # We load 'cascade' and 'app' to build the full semantic picture
    graph.load("cascade")
    graph.load("app")
    ctx = RefactorContext(graph=graph)

    op = MoveDirectoryOperation(src_dir_to_move, dest_dir)
~~~~~
~~~~~python.new
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

    op = MoveDirectoryOperation(src_dir_to_move, dest_dir)
~~~~~

#### Acts 6: 修复 `test_rename_e2e.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
    # 2. Analysis Phase
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    ctx = RefactorContext(graph=graph)
~~~~~
~~~~~python.new
    # 2. Analysis Phase
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~

#### Acts 7: 修复 `test_rename_symbol_monorepo_e2e.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.transaction import TransactionManager
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_symbol_monorepo_e2e.py
~~~~~
~~~~~python.old
    # 2. ACT
    graph = SemanticGraph(root_path=project_root)
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    graph.load("test_core")
    graph.load("integration")
    ctx = RefactorContext(graph=graph)
~~~~~
~~~~~python.new
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("pkga_lib")
    graph.load("pkgb_app")
    graph.load("test_core")
    graph.load("integration")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )
~~~~~

#### Acts 8: 修复 `test_rename_transformer_advanced.py`

应用相同的修复模式。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_transformer_advanced.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
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
    graph = SemanticGraph(root_path=project_root)
    graph.load("mypkg")
    graph.load("main")
    ctx = RefactorContext(graph=graph)
~~~~~
~~~~~python.new
def test_rename_symbol_via_attribute_access(tmp_path):
    # 1. Setup
    project_root = (
        WorkspaceFactory(tmp_path)
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

#### Acts 9: 修复 `test_rename_operation.py`

最后，修复单元测试，为其提供所需的 Mock 对象。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
from unittest.mock import Mock
from pathlib import Path
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph, UsageRegistry, UsageLocation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.engine.transaction import WriteFileOp
~~~~~
~~~~~python.new
from unittest.mock import Mock
from pathlib import Path
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.graph import SemanticGraph, UsageRegistry, UsageLocation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.engine.transaction import WriteFileOp
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    # Let's use a real tmp_path for reading files to simplify mocking Path.read_text
    # We will create fake files that the operation can read.
    tmp_path = Path("/tmp/fake_project")  # conceptual
    mock_graph.root_path = tmp_path

    ctx = RefactorContext(graph=mock_graph)

    # 2. Define Test Data
~~~~~
~~~~~python.new
    # Let's use a real tmp_path for reading files to simplify mocking Path.read_text
    # We will create fake files that the operation can read.
    tmp_path = Path("/tmp/fake_project")  # conceptual
    mock_graph.root_path = tmp_path

    mock_workspace = Mock(spec=Workspace)
    mock_sidecar_manager = Mock(spec=SidecarManager)
    # Prevent sidecar logic from running in this unit test
    mock_sidecar_manager.get_doc_path.return_value.exists.return_value = False
    mock_sidecar_manager.get_signature_path.return_value.exists.return_value = False

    ctx = RefactorContext(
        graph=mock_graph,
        workspace=mock_workspace,
        sidecar_manager=mock_sidecar_manager,
    )

    # 2. Define Test Data
~~~~~

### 下一步建议

所有已知的测试失败都已修复。建议您现在运行 `pytest packages/stitcher-refactor` 来验证修复是否成功。如果通过，我们可以将这些变更提交到版本控制中。
