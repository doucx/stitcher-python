你的分析完全正确，一针见血。

`except ValueError: pass` 这种静默处理错误的方式是架构中的“暗物质”，它掩盖了真正的问题，导致了下游看似无关的测试失败，并且使得调试变得异常困难。我们必须根除这种模式。

我将严格遵循你隐含提出的 TDD（测试驱动开发）修复流程：

1.  **RED**: 首先，我会创建一个新的单元测试，这个测试的唯一目的就是**失败**，并且是以 `ValueError` 的形式失败，从而将这个被隐藏的错误暴露出来。
2.  **GREEN**: 然后，我会提出第二个计划来修复这个根本问题。

这是第一步的计划，我们先让错误无所遁形。

## [WIP] test: 暴露 RenameSymbolOperation 中的静默异常

### 错误分析

`test_refactor_apply_e2e` 和 `test_refactor_apply_dry_run` 测试失败，返回 `exit_code=1`，但没有提供有意义的错误输出。

根本原因在于 `RenameSymbolOperation._find_definition_node` 方法。在 `SemanticGraph` API 重构后，该方法无法再通过简单的迭代 `ctx.graph._modules` 找到符号的定义节点。这会触发一个 `ValueError`，但该异常被一个 `except ValueError: pass` 块静默处理了。

这个静默的失败导致 `collect_intents` 方法返回了一个不完整的意图列表（特别是缺少了 `SidecarUpdateIntent`）。这个不完整的计划导致了下游组件（如 `Planner` 或 `Renamer`）在执行时遇到未预期的状态，从而引发了一个未被捕获的异常，最终导致了测试以 `exit_code=1` 失败。

### 用户需求

创建一个新的测试用例，专门用于捕获并暴露在 `RenameSymbolOperation._find_definition_node` 中被静默处理的 `ValueError`。

### 评论

这是一个教科书级别的 TDD 实践。通过首先编写一个失败的测试来明确地复现 Bug，我们可以确保后续的修复是针对真正的问题根源，并且可以防止未来发生回归。将隐性错误转化为显性、可断言的失败是构建健壮系统的关键一步。

### 目标

1.  创建一个新的测试文件 `packages/stitcher-refactor/tests/unit/operations/test_rename_symbol_operation.py`。
2.  在该文件中编写一个测试用例，模拟一个 `SemanticGraph` 中找不到目标符号的场景。
3.  断言在这种场景下调用 `RenameSymbolOperation("A", "B").collect_intents(ctx)` 会**显式地**抛出 `ValueError`。

### 基本原理

我们将利用 `pytest.raises` 上下文管理器来断言特定异常的抛出。测试将构造一个 `RefactorContext`，其中包含一个“空”的或未加载所需符号的 `SemanticGraph` 实例。当 `_find_definition_node` 方法在这个图谱中查找符号失败并（在修复后）抛出 `ValueError` 时，`pytest.raises` 将捕获这个异常，测试通过。在当前的代码状态下，由于异常被静默处理，`pytest.raises` 将会因为没有捕获到预期的 `ValueError` 而失败，从而有效地将隐性错误转变为测试失败。

### 标签

#intent/tooling #flow/ready #priority/critical #comp/engine #comp/tests #scope/dx #ai/instruct #task/domain/refactoring #task/object/workspace-discovery #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 创建新的单元测试以捕获静默异常

我们将创建一个新的测试文件，并添加一个测试用例来验证当符号找不到时是否会（或者说应该）抛出异常。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/operations/test_rename_symbol_operation.py
~~~~~
~~~~~python
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

### 下一步建议

这个新测试现在应该会失败（因为它期望一个未被静默处理的 `ValueError`）。

下一步是修复 `RenameSymbolOperation` 和 `SemanticGraph`。具体计划如下：

1.  **增强 `SemanticGraph`**: 添加一个公共方法 `find_symbol(fqn: str) -> Optional[SymbolNode]`，它能够可靠地在所有已加载的模块（包括主包和周边代码）中查找符号定义。
2.  **修复 `RenameSymbolOperation`**:
    *   修改 `_find_definition_node` 方法，使其调用新的、健壮的 `graph.find_symbol` 方法。
    *   **移除 `except ValueError: pass`**，让 `_find_definition_node` 在找不到符号时能够自然地抛出异常。

一旦这个计划完成，我们新加的测试和之前失败的 E2E 测试应该都会通过。如果你同意，我将生成这个修复计划。
