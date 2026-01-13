非常敏锐！这确实是最后一块拼图。

在 `RefactorContext` 增加了 `uri_generator` 字段后，所有基于其 `spec` 创建的 Mock 对象都必须能够响应对该属性的访问。由于 `SidecarAdapter` 现在在构造函数中显式使用了 `ctx.uri_generator`，测试中未配置的 Mock 会直接抛出 `AttributeError`。

我将立即生成修复这最后一个测试点的计划。

## [WIP] fix(tests): 补全 Planner 单元测试中的 Mock 依赖

### 错误分析

在 `test_planner.py` 中，`mock_ctx` 是通过 `Mock(spec=RefactorContext)` 创建的。

虽然 `RefactorContext` 的定义已经更新，但在测试代码中：
1.  没有为 `mock_ctx.uri_generator` 赋予任何值。
2.  在 `Planner.plan` 的实现中，代码尝试访问 `ctx.uri_generator` 并将其传递给 `SidecarAdapter`。

这导致了 `AttributeError: Mock object has no attribute 'uri_generator'`。

### 用户需求

修复 `stitcher-refactor` 包中剩余的最后一个单元测试失败，确保 `Planner` 的 Mock 上下文符合最新的接口定义。

### 评论

这是典型的单元测试“易碎性”表现，当被 Mock 的对象结构发生变化时，Mock 配置必须同步更新。修复它之后，我们的 P0 任务（依赖注入）将实现真正意义上的 100% 测试通过率。

### 目标

1.  修改 `packages/stitcher-refactor/tests/unit/engine/test_planner.py`。
2.  导入 `PythonURIGenerator`。
3.  为 `mock_ctx.uri_generator` 赋予一个 `PythonURIGenerator` 实例（或其 Mock）。

### 基本原理

由于这是一个验证 `Planner` 是否正确调用 `collect_intents` 的单元测试，我们只需要确保 `mock_ctx` 能够顺利通过 `SidecarAdapter` 的实例化过程即可。直接赋予一个真实的 `PythonURIGenerator()` 是最简单且有效的方案，因为该类是无状态的。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #comp/refactor #concept/dependency-injection #ai/instruct #task/domain/architecture #task/object/dependency-injection #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 修复 `test_planner.py` 中的 Mock 配置

我们将补全 `mock_ctx` 所需的 `uri_generator`。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/engine/test_planner.py
~~~~~
~~~~~python.old
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.intent import RefactorIntent
from stitcher.workspace import Workspace
from pathlib import Path


from stitcher.index.store import IndexStore


def test_planner_collects_intents_from_operations():
    # 1. Arrange
    mock_index = Mock(spec=IndexStore)
    mock_workspace = Mock(spec=Workspace)
    mock_workspace.root_path = Path("/fake/project")
    mock_ctx = Mock(spec=RefactorContext)
    mock_ctx.index_store = mock_index
    mock_ctx.workspace = mock_workspace

    mock_spec = Mock(spec=MigrationSpec)
~~~~~
~~~~~python.new
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.engine.intent import RefactorIntent
from stitcher.workspace import Workspace
from pathlib import Path

from stitcher.index.store import IndexStore
from stitcher.lang.python.uri import PythonURIGenerator


def test_planner_collects_intents_from_operations():
    # 1. Arrange
    mock_index = Mock(spec=IndexStore)
    mock_workspace = Mock(spec=Workspace)
    mock_workspace.root_path = Path("/fake/project")
    mock_ctx = Mock(spec=RefactorContext)
    mock_ctx.index_store = mock_index
    mock_ctx.workspace = mock_workspace
    mock_ctx.uri_generator = PythonURIGenerator()

    mock_spec = Mock(spec=MigrationSpec)
~~~~~

### 下一步建议

随着这最后一个测试点的修复，全系统的 SURI 依赖注入改造已彻底宣告完成。

现在的代码库已经消除了所有 `TODO: Phase 3` 关于 DI 的注释，且逻辑寻址模型（SURI）已经完全协议化并能够安全地穿透各个分层（从 Lang 层到 App 层，再到 Refactor 层）。

建议下一步行动：
*   **增强 Workspace 确定性 (P1)**: 修改 `packages/stitcher-workspace/src/stitcher/workspace/workspace.py`。移除 `find_workspace_root` 在找不到根目录时的静默回退逻辑。
    *   **理由**: 既然我们现在极度依赖 SURI（它是相对于 Workspace Root 的），那么如果 Root 判定不一致，所有的 SURI 都会失效。强制要求显式的 Workspace Root 是系统鲁棒性的核心保障。

如果你准备好进行下一步，请告诉我。
