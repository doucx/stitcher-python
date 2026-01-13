Excellent. With the graph builder in place, we can now add the intelligence to analyze it.

This plan will populate the `algorithms.py` file with functions that wrap `networkx`'s powerful capabilities, providing a clean, domain-specific API for our future architecture rules. We will also create a dedicated test file to ensure these algorithms behave exactly as expected.

## [WIP] feat: Implement graph algorithms for architectural analysis

### 用户需求

Based on the roadmap, we need to develop graph algorithm tools in `stitcher.analysis.graph.algorithms`. This involves creating functions to detect circular dependencies and check for paths within the dependency graph, along with corresponding unit tests.

### 评论

This step transforms our graph data structure into a source of actionable insights. By creating an abstraction layer over `networkx`, we isolate the core analysis logic from the specific library implementation, making our architecture more maintainable. The `detect_circular_dependencies` function will be the first major feature enabled by this new infrastructure, providing immediate value by identifying critical architectural flaws.

### 目标

1.  Implement the function `detect_circular_dependencies` in `algorithms.py` to find all simple cycles in the graph.
2.  Implement the helper function `has_path` in `algorithms.py`.
3.  Create a new unit test file, `test_algorithms.py`, in the `packages/stitcher-analysis/tests/unit/graph/` directory.
4.  Write tests that verify the correctness of both algorithm functions using various graph structures (e.g., with and without cycles).

### 基本原理

1.  **Implementation (`algorithms.py`)**: We will use a `write_file` operation to populate the `algorithms.py` module. The `detect_circular_dependencies` function will directly call `networkx.simple_cycles` and convert the resulting generator into a `List[List[str]]` for a stable, predictable return type. `has_path` will be a simple wrapper around `networkx.has_path`.
2.  **Testing (`test_algorithms.py`)**: A new test file will be created. Inside, we will manually construct `networkx.DiGraph` instances representing different dependency scenarios. For `detect_circular_dependencies`, we will test a Directed Acyclic Graph (DAG) (expecting no cycles) and a graph containing a known cycle (expecting it to be found). For `has_path`, we will test both a valid path and an invalid path. This ensures our wrappers are functioning correctly.

### 标签

#intent/build #intent/tooling #flow/ready #priority/high #comp/analysis #comp/tests #concept/graph #scope/core #ai/instruct #task/domain/analysis #task/object/graph-infra #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: Implement the Graph Algorithms

We will populate the `algorithms.py` file with our cycle and path detection functions.

~~~~~act
write_file
packages/stitcher-analysis/src/stitcher/analysis/graph/algorithms.py
~~~~~
~~~~~python
from typing import List
import networkx as nx


def detect_circular_dependencies(graph: nx.DiGraph) -> List[List[str]]:
    """
    Finds all simple cycles in a directed graph.

    A simple cycle is a path where the start and end nodes are the same,
    and no other nodes are repeated. Self-loops are not considered simple cycles.

    Args:
        graph: The directed graph to check.

    Returns:
        A list of cycles, where each cycle is represented as a list of
        node identifiers (file paths).
    """
    return [list(cycle) for cycle in nx.simple_cycles(graph)]


def has_path(graph: nx.DiGraph, source: str, target: str) -> bool:
    """
    Checks if a path exists between two nodes in the graph.

    Args:
        graph: The directed graph to check.
        source: The starting node.
        target: The ending node.

    Returns:
        True if a path exists, False otherwise.
    """
    return nx.has_path(graph, source, target)
~~~~~

#### Acts 2: Implement Unit Tests for Graph Algorithms

Next, we create the test file and add tests to verify the correctness of our new algorithm functions.

~~~~~act
write_file
packages/stitcher-analysis/tests/unit/graph/test_algorithms.py
~~~~~
~~~~~python
import networkx as nx

from stitcher.analysis.graph.algorithms import (
    detect_circular_dependencies,
    has_path,
)


def test_detect_circular_dependencies():
    # 1. Arrange: Create a graph with a known cycle
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("a.py", "b.py"),
        ("b.py", "c.py"),
        ("c.py", "a.py"),  # Cycle: a -> b -> c -> a
        ("d.py", "a.py"),  # Not part of cycle
    ])

    # 2. Act
    cycles = detect_circular_dependencies(graph)

    # 3. Assert
    assert len(cycles) == 1
    # networkx can start the cycle from any node, so we sort to have a stable check
    assert sorted(cycles[0]) == ["a.py", "b.py", "c.py"]


def test_detect_circular_dependencies_no_cycles():
    # 1. Arrange: Create a Directed Acyclic Graph (DAG)
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("a.py", "b.py"),
        ("b.py", "c.py"),
        ("a.py", "c.py"),
    ])

    # 2. Act
    cycles = detect_circular_dependencies(graph)

    # 3. Assert
    assert len(cycles) == 0


def test_has_path():
    # 1. Arrange
    graph = nx.DiGraph()
    graph.add_edges_from([
        ("a.py", "b.py"),
        ("b.py", "c.py"),
        ("d.py", "e.py"),
    ])

    # 2. Act & 3. Assert
    assert has_path(graph, "a.py", "c.py") is True
    assert has_path(graph, "a.py", "e.py") is False
    assert has_path(graph, "a.py", "a.py") is True # A path to self always exists
~~~~~

### 下一步建议

我们已经成功地将底层的图算法封装成了清晰的、面向业务的 API。现在，我们拥有了检测架构问题的工具。

下一步是**第 5 步：实现架构规则 (Implement Architecture Rules)**。我将开始创建 `stitcher.analysis.rules.architecture` 目录和 `CircularDependencyRule`，这个规则将使用我们刚刚创建的 `detect_circular_dependencies` 函数来生成具体的 `Violation` 报告。如果你同意，我将开始制定此计划。
