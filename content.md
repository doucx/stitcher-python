## [WIP] You've correctly identified the issue. The test is failing with a `KeyError: 'runtime'` from deep within the `griffe` loader.

### 错误分析

The error occurs because we are attempting to load different parts of the same namespace package (`cascade`) through separate, sequential calls to `graph.load()`.

1.  **`graph.load("cascade.engine")`**: This call succeeds. `griffe` finds the `cascade-engine/src` directory, loads the `cascade` package from there, and discovers the `engine` submodule. It now has an in-memory representation of the `cascade` package based *only* on this first location.
2.  **`graph.load("cascade.runtime")`**: This call fails. `griffe` sees that it already has a module named `cascade`. It then tries to find the `runtime` submodule *within the existing `cascade` module object*. Since that object was built only from the `cascade-engine` sources, it has no knowledge of the `runtime` submodule located in `cascade-runtime/src`, leading to the `KeyError`.

The correct way to handle namespace packages is to load the top-level namespace package in a single call, allowing `griffe` to discover all its constituent parts across all provided search paths.

### 用户需求
修复 `packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py` 中失败的 `test_move_directory_in_monorepo_updates_cross_package_references` 测试用例。

### 评论
这是一个经典的关于如何与静态分析工具（如 `griffe`）交互处理 Python 命名空间包的案例。这个修复不仅能解决当前的 `KeyError`，还能使我们的测试逻辑更加健壮和正确，因为它遵循了加载分布式命名空间包的标准模式。这个改进确保了 `SemanticGraph` 能够一次性构建起完整的、跨越多个物理目录的包的语义视图。

### 目标
修改测试用例，将两个独立的 `graph.load()` 调用合并为一个，以正确加载整个 `cascade` 命名空间包。

### 基本原理
我们将把 `graph.load("cascade.engine")` 和 `graph.load("cascade.runtime")` 这两行代码替换为单一的 `graph.load("cascade")`. 由于 `Workspace` 已经正确地将 `cascade-engine/src` 和 `cascade-runtime/src` 都添加到了 `SemanticGraph` 的搜索路径中，`griffe` 在收到加载 `cascade` 的指令时，会自动扫描所有这些路径，发现并合并所有构成 `cascade` 命名空间包的子模块（包括 `engine` 和 `runtime`）。这样就能在一次操作中构建出完整的、正确的语义图谱。

### 标签
#intent/fix #flow/ready #priority/high #comp/tests #concept/state #scope/dx #ai/instruct #task/domain/testing #task/object/refactor-engine #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正命名空间包的加载方式

我们将修改 `test_move_directory_monorepo_e2e.py` 文件，用一次 `graph.load("cascade")` 调用替换掉对子模块的多次调用。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_monorepo_e2e.py
~~~~~
~~~~~python.old
    # Load all modules contributing to the 'cascade' namespace
    graph.load("cascade.engine")
    graph.load("cascade.runtime")
~~~~~
~~~~~python.new
    # Load the top-level namespace package. Griffe will discover all its parts
    # from the search paths provided by the Workspace.
    graph.load("cascade")
~~~~~

### 下一步建议
测试已修复。现在，我们可以继续执行路线图中的 **任务 3.2: 代码清理与文档完善**。

我将准备一个计划来审查和清理代码库，并为新引入的 `Workspace` 和 `SidecarManager` 添加必要的文档，以完成重构的收尾工作。
