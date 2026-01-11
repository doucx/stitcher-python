是的，这些警告是典型的 “测试基础设施污染” 问题。

由于我们将 stitcher-test-utils 注册为了 pytest11 插件，Pytest 会在启动的最早期加载它。而 stitcher-test-utils 之前的实现中，在模块顶部（Top-level）直接导入了 stitcher.common、stitcher.app 等核心包。
是的，这些警告是典型的 **“测试基础设施污染”** 问题。

由于我们将 `stitcher-test-utils` 注册为了 `pytest11` 插件，Pytest 会在启动的最早期加载它。而 `stitcher-test-utils` 之前的实现中，在模块顶部（Top-level）直接导入了 `stitcher.common`、`stitcher.app` 等核心包。

**问题的本质：**
1.  Pytest 启动，加载插件 `stitcher-test-utils`。
2.  插件执行 `import stitcher.app`，此时 Python 的 `sys.modules` 中已经填入了这些包。
3.  `pytest-cov`（覆盖率工具）随后启动，尝试为 `stitcher` 包安装监控钩子。
4.  `coverage` 发现这些包已经加载完毕，它错过了最初的加载过程，因此发出 `module-not-measured` 警告。

**修复方案：**
我将根据 **“高保真工程公理 (HFEA)”** 的“确定性路径”原则，对 `stitcher-test-utils` 进行重构，全面引入 **延迟导入 (Lazy Import)** 模式。所有的核心逻辑包导入将从模块顶部移入具体的函数或方法内部。这确保了在 `pytest-cov` 还没准备好之前，没有任何业务代码会被提前加载。

## [WIP] refactor(test-utils): eliminate coverage warnings via lazy imports

### 用户需求

测试过程中出现大量 `CoverageWarning`，提示模块在测量开始前已被导入。这干扰了测试输出，且表明测试基础设施存在副作用。

### 评论

这是典型的插件加载顺序问题。在 monorepo 架构中，测试工具包作为插件必须是“非侵入性”的。在顶级作用域进行业务代码导入会导致 Python 解释器状态提前改变，破坏了覆盖率工具的原子性。使用延迟导入是解决此类问题的工业级标准做法。

### 目标

1.  重构 `stitcher-test-utils` 中的所有辅助模块（`bus.py`, `helpers.py`, `fixtures.py`）。
2.  将所有对 `stitcher.*` 业务包的 `import` 语句从文件顶部移至函数或类方法内部。
3.  确保 `pytest` 插件在加载阶段仅进行注册，而不触发任何业务逻辑链。

### 基本原理

通过将 `import` 语句包裹在函数内部，我们利用了 Python 的动态加载特性。只有当某个测试用例实际请求该 Fixture 或调用该辅助函数时，相关的业务代码才会被加载。此时，`pytest-cov` 已经完全接管了环境，能够正确记录所有的执行路径，从而消除“未被测量”的警告。

### 标签

#intent/refine #flow/ready #priority/medium #comp/tests #scope/dx #task/domain/testing #task/object/test-utils #task/action/refactor #task/state/end

---

### Script

#### Acts 1: 对 Fixture 定义实施延迟导入

修改 `fixtures.py`，不再在顶部导入 `WorkspaceFactory` 和 `SpyBus`。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/fixtures.py
~~~~~
~~~~~python
import pytest
from pathlib import Path

@pytest.fixture
def workspace_factory(tmp_path: Path):
    """Provides a factory to create isolated test workspaces."""
    from .workspace import WorkspaceFactory
    return WorkspaceFactory(tmp_path)


@pytest.fixture
def spy_bus():
    """Provides a SpyBus instance to intercept and inspect bus messages."""
    from .bus import SpyBus
    return SpyBus()
~~~~~

#### Acts 2: 对 `SpyBus` 实施延迟导入

修改 `bus.py`，将对 `stitcher.common` 的依赖移入 `patch` 方法中。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

# Import the actual singleton to patch it in-place
import stitcher.common
from stitcher.common.messaging.protocols import Renderer
from needle.pointer import SemanticPointer
~~~~~
~~~~~python.new
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

# No top-level imports of stitcher packages to avoid coverage warnings
from needle.pointer import SemanticPointer
~~~~~

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus"):
        # The singleton instance we need to mutate
        real_bus = stitcher.common.bus

        # Define the interceptor hook
~~~~~
~~~~~python.new
class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus"):
        # Lazy import to avoid early pollution of sys.modules
        import stitcher.common
        
        # The singleton instance we need to mutate
        real_bus = stitcher.common.bus

        # Define the interceptor hook
~~~~~

#### Acts 3: 对 `helpers.py` 实施全面延迟导入

`helpers.py` 包含了大量的业务逻辑引用，必须全部移入函数内部。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/helpers.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional

def create_populated_index(root_path: Path):
    from stitcher.workspace import Workspace
    from stitcher.index.db import DatabaseManager
    from stitcher.index.store import IndexStore
    from stitcher.index.indexer import FileIndexer
    from stitcher.adapter.python.index_adapter import PythonAdapter

    db_path = root_path / ".stitcher" / "index" / "index.db"

    db_manager = DatabaseManager(db_path)
    db_manager.initialize()
    store = IndexStore(db_manager)

    workspace = Workspace(root_path)
    search_paths = workspace.get_search_paths()

    files_to_index = workspace.discover_files()

    indexer = FileIndexer(root_path, store)
    indexer.register_adapter(".py", PythonAdapter(root_path, search_paths))
    indexer.index_files(files_to_index)

    return store


def create_test_app(
    root_path: Path, interaction_handler: Optional[Any] = None
):
    from stitcher.app import StitcherApp
    from stitcher.adapter.python import (
        PythonTransformer,
        PythonFingerprintStrategy,
        GriffePythonParser,
    )
    
    parser = GriffePythonParser()
    transformer = PythonTransformer()
    strategy = PythonFingerprintStrategy()
    return StitcherApp(
        root_path=root_path,
        parser=parser,
        transformer=transformer,
        fingerprint_strategy=strategy,
        interaction_handler=interaction_handler,
    )


def get_stored_hashes(project_root: Path, file_path: str) -> dict:
    from stitcher.app.services import SignatureManager
    manager = SignatureManager(root_path=project_root)
    fingerprints = manager.load_composite_hashes(file_path)
    return {fqn: fp.to_dict() for fqn, fp in fingerprints.items()}
~~~~~

### 下一步建议

由于 `stitcher-test-utils` 在 `pyproject.toml` 中引用了 `stitcher-application` 等包，如果这些包在安装时是以“非可编辑”模式安装的，可能仍会有零星警告。但在典型的开发环境（`uv` 工作区）中，上述延迟导入重构应能消除几乎所有 `module-not-measured` 警告。

请再次运行测试，确认输出已经变得纯净。
