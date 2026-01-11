检测到大量测试因缺少 `IndexStore` 依赖而失败。这是架构融合（Phase 3）引入的破坏性变更：`SemanticGraph` 和 `RefactorContext` 现在强制要求连接到索引数据库，但测试夹具尚未适配。

我们将分两步解决：
1.  **基础设施升级**：更新 `stitcher-test-utils`，添加 `stitcher-index` 依赖，并提供一个标准化的 `create_populated_index` 辅助函数。
2.  **测试修复**：批量修补集成测试，使其在初始化 `SemanticGraph` 之前先构建并填充索引。
3.  **CLI 诊断**：读取 CLI 入口代码，以便后续修复 E2E 测试。

## [WIP] fix: 升级测试基础设施以适配 IndexStore

### 错误分析
`TypeError: SemanticGraph.__init__() missing 1 required positional argument: 'index_store'` 表明测试代码手动实例化了图谱对象，但未传递新引入的 `index_store` 参数。

### 用户需求
1.  在 `stitcher-test-utils` 中提供便捷的索引创建工具。
2.  修复因缺少参数而崩溃的集成测试。

### 目标
1.  修改 `packages/stitcher-test-utils/pyproject.toml` 添加依赖。
2.  修改 `packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py` 添加 `create_populated_index`。
3.  修复 `stitcher-cli` 和 `stitcher-refactor` 中的关键集成测试。
4.  读取 `stitcher-cli` 源码以准备修复 CLI 运行器。

### 基本原理
通过在 `test-utils` 中封装索引初始化逻辑（创建 DB、注册适配器、扫描），我们保持了测试代码的整洁，并确保所有测试都运行在标准的、预填充的索引环境之上。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #comp/test-utils #scope/core #ai/instruct #task/domain/testing #task/object/test-harness #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 Test Utils 依赖

添加 `stitcher-index` 以便在辅助函数中使用。

~~~~~act
patch_file
packages/stitcher-test-utils/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "pyneedle",
    "PyYAML",
    "tomli-w",
    "stitcher-application",
    "stitcher-python-adapter",
]
~~~~~
~~~~~toml.new
dependencies = [
    "pyneedle",
    "PyYAML",
    "tomli-w",
    "stitcher-application",
    "stitcher-python-adapter",
    "stitcher-index",
]
~~~~~

#### Acts 2: 添加 create_populated_index 辅助函数

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~
~~~~~python.old
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler
from stitcher.adapter.python import (
    PythonTransformer,
    PythonFingerprintStrategy,
)

from stitcher.adapter.python.griffe_parser import GriffePythonParser


def create_test_app(
~~~~~
~~~~~python.new
from stitcher.app import StitcherApp
from stitcher.app.protocols import InteractionHandler
from stitcher.adapter.python import (
    PythonTransformer,
    PythonFingerprintStrategy,
)

from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.scanner import WorkspaceScanner
from stitcher.adapter.python.index_adapter import PythonAdapter


def create_populated_index(root_path: Path) -> IndexStore:
    """Creates a temporary IndexStore and performs a full scan."""
    db_path = root_path / ".stitcher" / "index" / "index.db"
    
    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    store = IndexStore(db_manager)
    
    scanner = WorkspaceScanner(root_path, store)
    scanner.register_adapter(".py", PythonAdapter(root_path))
    scanner.scan()
    
    return store


def create_test_app(
~~~~~

#### Acts 3: 修复 CLI 集成测试 (Internals)

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_internals.py
~~~~~
~~~~~python.old
from pathlib import Path

from stitcher.test_utils import WorkspaceFactory
from stitcher.config import load_config_from_path
from stitcher.refactor.workspace import Workspace
from stitcher.refactor.engine import SemanticGraph


def test_graph_can_find_symbol_after_workspace_refactor(tmp_path: Path):
~~~~~
~~~~~python.new
from pathlib import Path

from stitcher.test_utils import WorkspaceFactory, create_populated_index
from stitcher.config import load_config_from_path
from stitcher.refactor.workspace import Workspace
from stitcher.refactor.engine import SemanticGraph


def test_graph_can_find_symbol_after_workspace_refactor(tmp_path: Path):
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/tests/integration/test_refactor_internals.py
~~~~~
~~~~~python.old
    configs, _ = load_config_from_path(tmp_path)
    assert configs, "Config should be loaded"
    config = configs[0]

    workspace = Workspace(root_path=tmp_path, config=config)
    graph = SemanticGraph(workspace)

    # The key action performed by RefactorRunner
    pkg_names = list(workspace.import_to_source_dirs.keys())
~~~~~
~~~~~python.new
    configs, _ = load_config_from_path(tmp_path)
    assert configs, "Config should be loaded"
    config = configs[0]

    # Create and populate index
    index_store = create_populated_index(tmp_path)

    workspace = Workspace(root_path=tmp_path, config=config)
    graph = SemanticGraph(workspace, index_store)

    # The key action performed by RefactorRunner
    pkg_names = list(workspace.import_to_source_dirs.keys())
~~~~~

#### Acts 4: 修复 Refactor 集成测试 (Rename E2E)

这是一个典型的测试模式，其他测试类似。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.common.transaction import TransactionManager, WriteFileOp
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.common.transaction import TransactionManager, WriteFileOp
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory, create_populated_index
~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_rename_e2e.py
~~~~~
~~~~~python.old
    # 2. Analysis Phase
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    # 3. Planning Phase
~~~~~
~~~~~python.new
    # 2. Analysis Phase
    index_store = create_populated_index(project_root)
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace, index_store=index_store)
    graph.load("mypkg")
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager, index_store=index_store
    )

    # 3. Planning Phase
~~~~~

#### Acts 5: 读取 CLI 源码

为了修复 `test_refactor_command.py`，我们需要修改 CLI 的命令处理函数。

~~~~~act
read_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~

### 下一步建议
1.  **应用 CLI 修复**：根据读取到的 CLI 源码，修改 `refactor.py`，使其在构建 Context 时创建并传入 `IndexStore`。
2.  **批量修复剩余测试**：继续使用 `create_populated_index` 模式修复剩余的 20+ 个失败的测试用例。建议分批处理或使用脚本。
3.  **Mock 单元测试**：修复 `test_rename_operation.py` 等单元测试，使用 Mock 的 `IndexStore`。
