You are absolutely right. My previous attempt was a "blind fix," which goes against the HFEA principle of "Regression Driven Development." Without a test that fails before the fix and passes after, I cannot guarantee the correctness of the solution. Your insistence on creating a test file first is the only correct path forward.

I will now generate a plan to create a specific, failing unit test that precisely captures this `__init__.py` alias resolution problem.

## [WIP] test(analysis): Add failing test for __init__ alias resolution in GraphBuilder

### 错误分析

我之前的修复未能解决问题，这表明我的核心假设——即简单地循环解析 `alias_target_fqn` 就足够了——要么是错误的，要么是实现上有缺陷。根本原因是我在没有建立一个可复现的失败场景（即回归测试）的情况下就尝试进行修复。这违反了工程的最佳实践。

现在，我们必须退后一步，构建一个“照明”工具——一个单元测试——来精确地照亮 `GraphBuilder` 在处理 `__init__.py` 桶式导出时的失败之处。

### 用户需求

创建一个新的单元测试，该测试专门模拟一个包含 `__init__.py` 文件重导出符号的场景，并断言 `GraphBuilder` 生成的依赖图存在错误（即，错误地将依赖指向 `__init__.py` 而不是真正的源文件）。

### 评论

这是纠正我们开发流程的关键一步。一个健壮的、专门针对此场景的回归测试将成为我们未来所有重构的安全网，并确保我们这次能真正地、一劳永逸地解决这个问题。我们不应再进行任何没有测试支持的修复。

### 目标

1.  在 `packages/stitcher-analysis/tests/unit/graph/` 目录下创建一个新的测试文件（或扩展现有文件）。
2.  在该文件中，定义一个名为 `test_build_dependency_graph_resolves_init_aliases_correctly` 的测试用例。
3.  该测试将通过 `unittest.mock` 精心构建一个 `IndexStoreProtocol` 的模拟实现，该实现精确地描述了一个存在 `__init__.py` 别名的项目结构。
4.  测试的核心断言将验证生成的图中边的连接是否正确：消费方模块应直接连接到符号的定义模块，而不是 `__init__.py`。

### 基本原理

我们将创建一个完全隔离的单元测试，只关注 `GraphBuilder` 的行为。通过模拟 `IndexStore`，我们可以完全控制输入数据，确保测试的确定性和速度。

模拟的场景如下：
-   `app.py` 导入并使用了 `my_pkg.my_func`。
-   `my_pkg/__init__.py` 从 `./logic.py` 导入了 `my_func`，并将其暴露出来（`from .logic import my_func`）。
-   `my_pkg/logic.py` 是 `my_func` 的真正定义之处。

我们的测试将断言，最终的图中必须存在一条从 `app.py` 指向 `my_pkg/logic.py` 的边，并且**绝对不能**存在一条从 `app.py` 指向 `my_pkg/__init__.py` 的边。

### 标签

#intent/tooling #flow/ready #priority/critical #comp/tests #concept/state #scope/core #ai/brainstorm #task/domain/testing #task/object/architecture-check #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 创建精确复现错误的单元测试

我们将创建新的测试文件 `test_builder.py` 并添加能够捕获此别名解析错误的测试用例。

~~~~~act
write_file
packages/stitcher-analysis/tests/unit/graph/test_builder.py
~~~~~
~~~~~python
from unittest.mock import MagicMock
import networkx as nx

from stitcher.spec.index import FileRecord, DependencyEdge, SymbolRecord
from stitcher.analysis.graph.builder import GraphBuilder


def test_build_dependency_graph_simple():
    # 1. Arrange: Setup mock store and data
    mock_store = MagicMock()

    mock_files = [
        FileRecord(id=1, path="src/a.py", content_hash="a", last_mtime=1, last_size=1, indexing_status=1),
        FileRecord(id=2, path="src/b.py", content_hash="b", last_mtime=1, last_size=1, indexing_status=1),
    ]
    mock_store.get_all_files.return_value = mock_files

    mock_edges = [
        DependencyEdge(source_path="src/a.py", target_fqn="b_module.some_func", kind="import", lineno=1),
    ]
    mock_store.get_all_dependency_edges.return_value = mock_edges

    def mock_find_symbol(fqn):
        symbol_rec = SymbolRecord(id=fqn, name="", kind="", lineno=1, col_offset=0, end_lineno=1, end_col_offset=0)
        if fqn.startswith("b_module"):
            return (symbol_rec, "src/b.py")
        return None

    mock_store.find_symbol_by_fqn.side_effect = mock_find_symbol

    # 2. Act: Build the graph
    builder = GraphBuilder()
    graph = builder.build_dependency_graph(mock_store)

    # 3. Assert: Verify the graph structure
    assert isinstance(graph, nx.DiGraph)
    assert set(graph.nodes) == {"src/a.py", "src/b.py"}
    assert graph.has_edge("src/a.py", "src/b.py")


def test_build_dependency_graph_resolves_init_aliases_correctly():
    """
    This is the regression test for the __init__.py barrel export issue.
    
    It simulates the following structure:
    - app.py:        `from my_pkg import my_func`
    - my_pkg/__init__.py: `from .logic import my_func`
    - my_pkg/logic.py:  `def my_func(): ...`
    
    The graph edge should be `app.py -> my_pkg/logic.py`, NOT `app.py -> my_pkg/__init__.py`.
    """
    # 1. Arrange
    mock_store = MagicMock()

    # Define the files in our simulated project
    mock_files = [
        FileRecord(id=1, path="app.py", content_hash="a", last_mtime=1, last_size=1, indexing_status=1),
        FileRecord(id=2, path="my_pkg/__init__.py", content_hash="b", last_mtime=1, last_size=1, indexing_status=1),
        FileRecord(id=3, path="my_pkg/logic.py", content_hash="c", last_mtime=1, last_size=1, indexing_status=1),
    ]
    mock_store.get_all_files.return_value = mock_files

    # Define the import relationships
    mock_edges = [
        # app.py imports the aliased symbol from the package
        DependencyEdge(source_path="app.py", target_fqn="my_pkg.my_func", kind="import", lineno=1),
        # __init__.py creates the alias by importing from the logic module
        DependencyEdge(source_path="my_pkg/__init__.py", target_fqn="my_pkg.logic.my_func", kind="import", lineno=1),
    ]
    mock_store.get_all_dependency_edges.return_value = mock_edges

    # Define the symbols and how to find them
    # This is the REAL function definition
    func_symbol = SymbolRecord(
        id="...", name="my_func", kind="function", lineno=1, col_offset=0, end_lineno=1, end_col_offset=0,
        canonical_fqn="my_pkg.logic.my_func"
    )
    # This is the ALIAS created in __init__.py
    alias_symbol = SymbolRecord(
        id="...", name="my_func", kind="alias", lineno=1, col_offset=0, end_lineno=1, end_col_offset=0,
        canonical_fqn="my_pkg.my_func",
        alias_target_fqn="my_pkg.logic.my_func" # Critical link
    )
    
    symbol_map = {
        "my_pkg.my_func": (alias_symbol, "my_pkg/__init__.py"),
        "my_pkg.logic.my_func": (func_symbol, "my_pkg/logic.py"),
    }
    mock_store.find_symbol_by_fqn.side_effect = lambda fqn: symbol_map.get(fqn)

    # 2. Act
    builder = GraphBuilder()
    graph = builder.build_dependency_graph(mock_store)
    
    # 3. Assert
    # The graph must connect app.py to the *real* source file, not the __init__
    assert graph.has_edge("app.py", "my_pkg/logic.py"), \
        "Graph should link consumer to the canonical source of the symbol."
    
    # The incorrect edge must NOT exist
    assert not graph.has_edge("app.py", "my_pkg/__init__.py"), \
        "Graph should NOT link consumer to the __init__.py alias."

    # The internal dependency from __init__ to logic should still exist
    assert graph.has_edge("my_pkg/__init__.py", "my_pkg/logic.py"), \
        "The internal dependency from __init__ to its implementation module should be preserved."
~~~~~
~~~~~act
delete_file
packages/stitcher-analysis/tests/unit/graph/test_builder_alias_resolution.py
~~~~~

### 下一步建议

现在我们已经有了一个专门捕获此错误的测试。请执行它，我们期望它会失败。

一旦我们确认了测试的失败，我将基于这个失败的测试用例，重新审视并提出一个能够使其通过的、正确的 `GraphBuilder` 修复方案。这是唯一可靠的前进道路。
