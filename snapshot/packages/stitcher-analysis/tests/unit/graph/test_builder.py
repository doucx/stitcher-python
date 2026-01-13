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