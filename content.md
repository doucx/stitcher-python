Of course. My last fix was clearly insufficient. The new test failures, particularly the explicit `ValueError` from `test_rename_symbol_definition.py`, provide the crucial insight needed. The problem is deeper than just a missing method; the core symbol-finding logic is not robust enough for the project's complexity.

We will follow your lead and fix this properly.

## [WIP] fix: Implement robust symbol finding and repair failing tests

### 错误分析

1.  **根本原因**: `test_rename_symbol_definition.py` 失败并抛出 `ValueError: Could not find definition for symbol: common.messaging.bus.MessageBus`，这暴露了 `SemanticGraph.find_symbol` 的实现过于天真。它只能在一级包中找到符号，无法处理 `common.messaging.bus` 这样的嵌套 FQN。这正是导致 E2E 测试 `test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 失败的根本原因——它们在处理嵌套符号时也触发了这个 `ValueError`，导致程序以 `exit_code=1` 退出。

2.  **次要原因 (测试问题)**:
    *   `test_rename_symbol_operation.py` 失败是因为我之前编写的 TDD 测试中的 mock 逻辑与实际实现不匹配，并且断言了错误的异常信息。
    *   `test_rename_operation.py` 失败是因为 `TypeError: 'Mock' object is not iterable`。这是因为我的上一处修改改变了 `RenameSymbolOperation` 的内部迭代逻辑，而这个单元测试中的 mock 没有相应更新。

### 用户需求

修复所有因 `SemanticGraph` 查找符号逻辑不完善而导致的测试失败，并清理所有相关的、因 API 变更而损坏的测试用例。

### 评论

这是一个关键的修复。一个不能在复杂项目中可靠地定位符号的重构引擎是毫无用处的。这次修复将通过实现一个递归的、全域的符号查找算法，来根除当前所有相关的 Bug，并为 `SemanticGraph` 组件建立一个真正健壮的基础。同时，我们也将清理和简化在此过程中暴露出的脆弱的测试代码。

### 目标

1.  **重写 `SemanticGraph.find_symbol`**: 实现一个能够递归遍历所有已加载模块和子模块的、健壮的符号查找方法。
2.  **修复 `test_rename_operation.py`**: 更新该测试中的 mock，使其与 `find_symbol` 的新公共 API 对齐，移除对内部实现的依赖。
3.  **简化 `test_rename_symbol_operation.py`**: 移除该测试中复杂且已经过时的 mock 设置，使其只专注于验证核心行为——当符号不存在时抛出 `ValueError`。

### 基本原理

我们将采用递归下降的策略来重写 `find_symbol`。它将从顶层加载的模块开始，逐级深入其成员，直到找到匹配 FQN 的符号或遍历完所有路径。对于测试的修复，我们将遵循“测试公共 API，而非内部实现”的原则，将 mock 调整为直接与 `find_symbol` 交互，并清理掉那些试图模拟旧有内部行为的脆弱代码。

### 标签

#intent/fix #flow/ready #priority/critical #comp/engine #comp/tests #scope/core #ai/instruct #task/domain/refactoring #task/object/workspace-discovery #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 实现递归的、健壮的 `find_symbol` 方法

这是最核心的修复。我们将重写 `find_symbol` 方法，使其能够处理任意深度的 FQN。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def find_symbol(self, fqn: str) -> Optional[SymbolNode]:
        for pkg_name in self._modules.keys():
            for member in self.iter_members(pkg_name):
                if member.fqn == fqn:
                    return member
        return None
~~~~~
~~~~~python.new
    def find_symbol(self, fqn: str) -> Optional[SymbolNode]:
        def _find_in_members(obj: griffe.Object) -> Optional[SymbolNode]:
            if obj.path == fqn and not isinstance(obj, griffe.Alias):
                filepath = obj.filepath
                path: Path
                if isinstance(filepath, list):
                    path = filepath[0] if filepath else Path("")
                else:
                    path = filepath or Path("")
                return SymbolNode(fqn=obj.path, kind=obj.kind, path=path)

            if hasattr(obj, "members"):
                for member in obj.members.values():
                    if isinstance(member, griffe.Alias):
                        continue
                    # Optimization: if fqn doesn't start with member path, no need to recurse
                    if fqn.startswith(member.path):
                        found = _find_in_members(member)
                        if found:
                            return found
            return None

        for module in self._griffe_loader.modules_collection.values():
            found = _find_in_members(module)
            if found:
                return found
        return None
~~~~~

#### Acts 2: 修复 `test_rename_operation.py` 中损坏的 Mock

现在我们更新单元测试，使其不再依赖于 `iter_members` 的内部实现，而是直接 mock 新的 `find_symbol` 公共 API。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    mock_registry.get_usages.return_value = locations

    # Configure the mock graph for the _find_definition_node logic
    mock_graph._modules = {"mypkg": Mock()}
    mock_definition_node = Mock(spec=SymbolNode)
    mock_definition_node.fqn = old_fqn
    mock_definition_node.path = file_a_path  # Assume definition is in file_a
    mock_graph.iter_members.return_value = [mock_definition_node]

    # Mock file system reads
    def mock_read_text(path, *args, **kwargs):
~~~~~
~~~~~python.new
    mock_registry.get_usages.return_value = locations

    # Configure the mock graph to use the new find_symbol public API
    mock_definition_node = Mock(spec=SymbolNode)
    mock_definition_node.fqn = old_fqn
    mock_definition_node.path = file_a_path  # Assume definition is in file_a
    mock_graph.find_symbol.return_value = mock_definition_node

    # Mock file system reads
    def mock_read_text(path, *args, **kwargs):
~~~~~

#### Acts 3: 简化并修正 `test_rename_symbol_operation.py`

最后，我们清理 TDD 测试。移除第一部分复杂的、基于内部实现的 mock，只保留第二部分简洁的、面向最终行为的测试，并确保它能正确运行。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/operations/test_rename_symbol_operation.py
~~~~~
~~~~~python.old
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.workspace import Workspace


def test_collect_intents_raises_error_if_symbol_not_found():
    """
    Verifies that a ValueError is raised if the target symbol for renaming
    cannot be found in the semantic graph. This prevents silent failures.
    """
    # 1. Arrange
    # Mock a workspace and an empty semantic graph
    mock_workspace = MagicMock(spec=Workspace)
    mock_graph = MagicMock(spec=SemanticGraph)
    mock_graph.iter_members.return_value = []  # Simulate symbol not found
    mock_graph._modules = {}  # Mock the internal structure it iterates

    # This is the key part of the mock that will trigger the error
    def find_def_node_side_effect(ctx):
        # Simulate the original logic raising an error
        raise ValueError("Symbol 'non.existent.symbol' not found")

    # In the fixed version, we will mock graph.find_symbol, but for now,
    # we target the problematic internal method.
    # To test the existing code, we need to mock the iteration to be empty.
    op = RenameSymbolOperation(
        old_fqn="non.existent.symbol", new_fqn="new.existent.symbol"
    )
    # Patch the problematic method directly to check if its exception is silenced
    op._find_definition_node = MagicMock(side_effect=find_def_node_side_effect)

    mock_ctx = MagicMock(spec=RefactorContext)
    mock_ctx.graph = mock_graph

    # 2. Act & Assert
    # We expect a ValueError because the symbol doesn't exist.
    # If this test fails, it's because the `except ValueError: pass` is silencing it.
    with pytest.raises(
        ValueError, match="Could not find definition for symbol: non.existent.symbol"
    ):
        op.collect_intents(mock_ctx)

    # To make the test pass after we fix the silent pass, we need to adjust
    # how we're mocking. For now, let's create a more realistic test.
    # Let's write the test for the *fixed* code.

    # Re-arranging for the post-fix scenario
    real_workspace = Workspace(root_path=Path("/tmp"))
    real_graph = SemanticGraph(workspace=real_workspace)
    # The graph is empty, so it won't find the symbol.

    ctx = RefactorContext(
        workspace=real_workspace, graph=real_graph, sidecar_manager=MagicMock()
    )
    op_final = RenameSymbolOperation(
        old_fqn="non.existent.symbol", new_fqn="new.existent.symbol"
    )

    with pytest.raises(
        ValueError, match="Could not find definition for symbol: non.existent.symbol"
    ):
        op_final.collect_intents(ctx)
~~~~~
~~~~~python.new
import pytest
from pathlib import Path
from unittest.mock import MagicMock

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.workspace import Workspace


def test_collect_intents_raises_error_if_symbol_not_found():
    """
    Verifies that a ValueError is raised if the target symbol for renaming
    cannot be found in the semantic graph. This prevents silent failures.
    """
    # 1. Arrange
    # Create a real, but empty, workspace and semantic graph.
    workspace = Workspace(root_path=Path("/tmp"))
    graph = SemanticGraph(workspace=workspace)
    # The graph is empty, so it won't find the symbol.

    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=MagicMock()
    )
    op = RenameSymbolOperation(
        old_fqn="non.existent.symbol", new_fqn="new.existent.symbol"
    )

    # 2. Act & Assert
    # We expect a ValueError because the symbol doesn't exist in the empty graph.
    with pytest.raises(
        ValueError, match="Could not find definition for symbol: non.existent.symbol"
    ):
        op.collect_intents(ctx)
~~~~~

### 下一步建议

我们已经实施了一个更深层次、更全面的修复。请再次运行测试套件。我非常有信心这次所有相关的测试都将通过。

成功后，我们将正式回到我们的主线任务：**4.2 调整 Planner 策略**。
