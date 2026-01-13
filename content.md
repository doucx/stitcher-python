Excellent. We have the data access layer ready. Now, we will build the component that consumes this data to construct the in-memory dependency graph.

This plan will implement the `GraphBuilder` class, which is the core of our new graph capability. It will also create a corresponding unit test to verify its logic in isolation, ensuring its correctness and adherence to the project's testing standards.

## [WIP] feat: Implement GraphBuilder and its unit tests

### 用户需求

As per the roadmap, the next step is to implement the `GraphBuilder`. This component will consume data from the `IndexStore` to construct a `networkx.DiGraph` representing the project's file-level import dependencies. A corresponding unit test must also be created to validate this logic.

### 评论

This is the heart of Phase 2. The `GraphBuilder` transforms the raw, relational data from our index into a powerful, queryable graph structure. The most critical piece of logic is resolving symbolic imports (`target_fqn`) to physical file locations, which effectively maps the conceptual dependencies to the actual file system structure. The accompanying unit test, using a mocked `IndexStore`, will be vital for ensuring this complex resolution logic is robust and correct.

### 目标

1.  Implement the `GraphBuilder` class in `packages/stitcher-analysis/src/stitcher/analysis/graph/builder.py`.
2.  The builder will have a `build_dependency_graph` method that takes an `IndexStoreProtocol` instance and returns a `networkx.DiGraph`.
3.  Create a new test directory: `packages/stitcher-analysis/tests/unit/graph/`.
4.  Implement a unit test file, `test_builder.py`, within that directory.
5.  The test will use a mock `IndexStore` to provide controlled input and verify that the generated graph has the correct nodes and edges.

### 基本原理

1.  **Implementation (`builder.py`)**: The `GraphBuilder` will first call `store.get_all_files()` to populate the graph with nodes, where each node is a file path. It will then iterate through the results of `store.get_all_dependency_edges()`. For each edge, it will use `store.find_symbol_by_fqn()` to resolve the dependency's target FQN to a file path. An internal cache will be used to prevent redundant lookups for the same FQN. If a symbol is resolved to a file within the project, a directed edge is added from the source file to the target file in the graph. External dependencies (unresolvable FQNs) are ignored.
2.  **Testing (`test_builder.py`)**: A new test file will be created following the monorepo testing architecture. We will use `unittest.mock.MagicMock` to create a fake `IndexStore`. This mock will be configured to return predefined `FileRecord` and `DependencyEdge` objects, and to simulate the behavior of `find_symbol_by_fqn`. The test will then assert that the `GraphBuilder` correctly constructs the graph based on this controlled data, verifying node count, edge count, and the presence of specific dependency links.

### 标签

#intent/build #intent/tooling #flow/ready #priority/high #comp/analysis #comp/tests #concept/graph #scope/core #ai/instruct #task/domain/analysis #task/object/graph-infra #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: Implement the GraphBuilder

We will write the full implementation of the `GraphBuilder` class.

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/graph/builder.py
~~~~~
~~~~~python
from typing import Dict
import networkx as nx

from stitcher.spec import IndexStoreProtocol


class GraphBuilder:
    def build_dependency_graph(self, store: IndexStoreProtocol) -> nx.DiGraph:
        """
        Builds a file-level dependency graph from the index store.

        Nodes: File paths (str)
        Edges: Represent an import from source file to target file.
        """
        graph = nx.DiGraph()
        fqn_to_path_cache: Dict[str, str | None] = {}

        # 1. Add all source files as nodes
        all_files = store.get_all_files()
        for file_record in all_files:
            graph.add_node(file_record.path)

        # 2. Add edges based on import references
        all_edges = store.get_all_dependency_edges()
        for edge in all_edges:
            source_path = edge.source_path
            target_fqn = edge.target_fqn

            # Skip if we've already processed this FQN and found it unresolvable
            if target_fqn in fqn_to_path_cache and fqn_to_path_cache[target_fqn] is None:
                continue

            # Resolve FQN to a file path
            if target_fqn not in fqn_to_path_cache:
                symbol_result = store.find_symbol_by_fqn(target_fqn)
                if symbol_result:
                    _, target_path = symbol_result
                    fqn_to_path_cache[target_fqn] = target_path
                else:
                    # Mark as unresolvable (likely an external library)
                    fqn_to_path_cache[target_fqn] = None

            target_path = fqn_to_path_cache.get(target_fqn)

            # Add edge if the target is an internal, resolved file
            if target_path and source_path != target_path:
                graph.add_edge(source_path, target_path)

        return graph
~~~~~

#### Acts 2: Create the test directory structure

Now, we create the necessary directory for our new test file, ensuring we do not create `__init__.py` files, per the testing specification.

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-analysis/tests/unit/graph
~~~~~

#### Acts 3: Implement the unit test for GraphBuilder

Finally, we write the test file that verifies the `GraphBuilder`'s logic using a mocked `IndexStore`.

~~~~~act
write_file
packages/stitcher-analysis/tests/unit/graph/test_builder.py
~~~~~
~~~~~python
from unittest.mock import MagicMock
import networkx as nx

from stitcher.spec.index import FileRecord, DependencyEdge, SymbolRecord
from stitcher.analysis.graph.builder import GraphBuilder


def test_build_dependency_graph():
    # 1. Arrange: Setup mock store and data
    mock_store = MagicMock()

    # Mock files (nodes)
    mock_files = [
        FileRecord(id=1, path="src/a.py", content_hash="a", last_mtime=1, last_size=1, indexing_status=1),
        FileRecord(id=2, path="src/b.py", content_hash="b", last_mtime=1, last_size=1, indexing_status=1),
        FileRecord(id=3, path="src/c.py", content_hash="c", last_mtime=1, last_size=1, indexing_status=1),
    ]
    mock_store.get_all_files.return_value = mock_files

    # Mock dependencies (potential edges)
    mock_edges = [
        # a -> b
        DependencyEdge(source_path="src/a.py", target_fqn="b_module.some_func", kind="import", lineno=1),
        # a -> c
        DependencyEdge(source_path="src/a.py", target_fqn="c_module.SomeClass", kind="import", lineno=2),
        # b -> c
        DependencyEdge(source_path="src/b.py", target_fqn="c_module.SomeClass", kind="import", lineno=5),
        # a -> external (should be ignored)
        DependencyEdge(source_path="src/a.py", target_fqn="os.path.join", kind="import", lineno=3),
        # c -> a (creating a cycle for later tests)
        DependencyEdge(source_path="src/c.py", target_fqn="a_module.main", kind="import", lineno=1),
    ]
    mock_store.get_all_dependency_edges.return_value = mock_edges

    # Mock FQN lookup
    def mock_find_symbol(fqn):
        symbol_rec = SymbolRecord(id=fqn, name="", kind="", lineno=1, col_offset=0, end_lineno=1, end_col_offset=0)
        if fqn.startswith("a_module"):
            return (symbol_rec, "src/a.py")
        if fqn.startswith("b_module"):
            return (symbol_rec, "src/b.py")
        if fqn.startswith("c_module"):
            return (symbol_rec, "src/c.py")
        return None  # For external symbols like 'os.path.join'

    mock_store.find_symbol_by_fqn.side_effect = mock_find_symbol

    # 2. Act: Build the graph
    builder = GraphBuilder()
    graph = builder.build_dependency_graph(mock_store)

    # 3. Assert: Verify the graph structure
    assert isinstance(graph, nx.DiGraph)
    assert set(graph.nodes) == {"src/a.py", "src/b.py", "src/c.py"}
    assert graph.number_of_edges() == 4

    # Check for specific edges
    assert graph.has_edge("src/a.py", "src/b.py")
    assert graph.has_edge("src/a.py", "src/c.py")
    assert graph.has_edge("src/b.py", "src/c.py")
    assert graph.has_edge("src/c.py", "src/a.py")

    # Check that external dependency was ignored
    # (There's no node for 'os', and no edge pointing to a non-existent node)
    assert "os" not in graph.nodes

    # Verify calls to mock
    assert mock_store.get_all_files.call_count == 1
    assert mock_store.get_all_dependency_edges.call_count == 1
    # We call find_symbol_by_fqn 4 times (a,b,c,os), not 5, due to caching
    assert mock_store.find_symbol_by_fqn.call_count == 4
~~~~~

### 下一步建议

我们已经成功地构建了图的生成器并为其建立了测试保障。现在我们拥有了一个内存中的项目依赖图。

下一步是利用这个图。根据路线图，我们将进入 **第 4 步：开发图算法工具 (Graph Algorithms)**。我将开始填充 `stitcher/analysis/graph/algorithms.py` 文件，封装 `networkx` 的能力，并提供一个 `detect_circular_dependencies` 函数。如果你同意，我将着手准备这个计划。
