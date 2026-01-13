好的，我们已经确认了这是一个静态分析工具的 BUG。现在，我们将遵循标准的测试驱动开发（TDD）或测试驱动修复（Test-Driven Bugfixing）流程：首先创建一个能够稳定复现该错误的集成测试。

这个测试将作为我们调试的靶场，一旦我们修复了 `GraphBuilder` 的问题，这个测试就应该通过，从而防止未来的代码变更导致此问题复现。

我将生成一个计划来创建这个新的集成测试。

## [WIP] test(analysis): 添加集成测试以捕获循环依赖误报

### 用户需求

创建一个集成测试，该测试能够稳定地复现由“桶式导出 (`Barrel Export`)”设计模式引发的、`stitcher check` 错误的循环依赖报告。

### 评论

这是解决此类问题的正确且专业的做法。通过创建一个隔离的、可重复的集成测试，我们能将问题从复杂的 CLI 环境中剥离出来，聚焦于核心的分析引擎（`Indexer`, `GraphBuilder`, `ArchitectureEngine`），为后续的调试和修复工作提供一个清晰、可靠的验证基准。

### 目标

1.  在 `stitcher-analysis` 包中创建一个新的集成测试文件。
2.  利用 `WorkspaceFactory` 工具在测试环境中精确地构建出导致问题的目录和导入结构（即 `engines -> consistency -> engine` 的桶式导出模式）。
3.  在该测试中，编程式地调用 `ArchitectureEngine` 对这个构建出的结构进行分析。
4.  **断言** `ArchitectureEngine` 的分析结果**包含**一个循环依赖的 `Violation`。这个断言目前会通过，因为它捕获了当前的 BUG。

### 基本原理

我们的核心假设是 `GraphBuilder` 在解析符号别名时存在缺陷。`test_build_dependency_graph_resolves_init_aliases_correctly` 这个单元测试虽然通过了，但它使用的是 Mock 对象，可能与真实的 `IndexStore` 和文件系统交互存在差异。

通过创建一个完整的集成测试，我们让整个分析流水线（`Workspace` -> `FileIndexer` -> `IndexStore` -> `GraphBuilder` -> `ArchitectureEngine`）在真实的文件结构上运行。这能暴露 Mock 测试中可能被忽略的、由 FQN 构建、路径解析或 `IndexStore` 实现细节引入的问题。

一旦这个“失败测试”就位，我们就可以安全地修改 `GraphBuilder`，目标就是让这个测试最终**失败**（即不再报告循环依赖），届时我们再将断言反转为“结果应为空”，测试便转变为一个防止此问题复现的回归测试。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/analysis #concept/dependency-graph #ai/instruct #task/domain/testing #task/object/architecture-analysis #task/action/bug-reproduction #task/state/begin

---

### Script

#### Acts 1: 创建集成测试文件

我们将创建 `packages/stitcher-analysis/tests/integration/` 目录和测试文件 `test_architecture_analysis.py`，用于存放捕获此架构分析 BUG 的集成测试。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-analysis/tests/integration
touch packages/stitcher-analysis/tests/integration/__init__.py
~~~~~

~~~~~act
write_file
packages/stitcher-analysis/tests/integration/test_architecture_analysis.py
~~~~~
~~~~~python
from needle.pointer import L
from stitcher.test_utils import WorkspaceFactory, create_test_app
from stitcher.analysis.engines import create_architecture_engine


def test_barrel_export_does_not_cause_false_circular_dependency(tmp_path):
    """
    Regression test to ensure that a standard 'barrel export' pattern
    (exporting symbols from a sub-package's __init__.py) does not get
    misidentified as a circular dependency.

    This test replicates the structure that previously caused a false positive:
    - engines/__init__.py imports from .consistency
    - engines/consistency/__init__.py imports from .engine
    - engines/consistency/engine.py defines the class.

    The dependency graph builder must resolve the import in engines/__init__.py
    all the way to engines/consistency/engine.py, not stop at
    engines/consistency/__init__.py.
    """
    # 1. Arrange: Build the problematic workspace structure
    ws_factory = (
        WorkspaceFactory(tmp_path)
        .with_pyproject("packages/my_pkg")
        .with_config(
            {
                "scan_paths": ["packages/my_pkg/src"],
            }
        )
        .with_source("packages/my_pkg/src/my_pkg/__init__.py", "")
        .with_source(
            "packages/my_pkg/src/my_pkg/engines/__init__.py",
            """
            from .consistency import ConsistencyEngine
            __all__ = ["ConsistencyEngine"]
            """,
        )
        .with_source(
            "packages/my_pkg/src/my_pkg/engines/consistency/__init__.py",
            """
            from .engine import ConsistencyEngine
            __all__ = ["ConsistencyEngine"]
            """,
        )
        .with_source(
            "packages/my_pkg/src/my_pkg/engines/consistency/engine.py",
            """
            class ConsistencyEngine:
                pass
            """,
        )
    )
    project_root = ws_factory.build()

    # 2. Act: Run the analysis engine
    app = create_test_app(project_root)
    app.ensure_index_fresh()

    engine = create_architecture_engine()
    violations = engine.analyze(app.index_store)

    # 3. Assert: Verify that NO circular dependency is found.
    #    (Initially, this test will fail, proving the bug exists)
    circular_violations = [
        v for v in violations if v.kind == L.check.architecture.circular_dependency
    ]

    # TODO: This assertion will fail until GraphBuilder is fixed.
    # The goal is to make this test pass.
    assert (
        not circular_violations
    ), f"Expected no circular dependencies, but found {len(circular_violations)}: {circular_violations}"

~~~~~

### 下一步建议

现在我们有了一个能够捕获此 BUG 的测试用例。下一步是运行 `pytest packages/stitcher-analysis/tests/integration/test_architecture_analysis.py` 并确认它会失败。

失败后，我们就可以聚焦于调试 `packages/stitcher-analysis/src/stitcher/analysis/graph/builder.py` 中的 `GraphBuilder.build_dependency_graph` 方法，直到这个测试通过为止。
