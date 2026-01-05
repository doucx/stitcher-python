好的，收到了新的测试失败信息。我们修复上一个 bug 时，引入了对 `ctx.graph.search_paths` 的依赖，但这破坏了单元测试中 `SemanticGraph` 的 mock 对象，因为它没有配置这个属性。

我将立即修复这个单元测试。

## [WIP] fix(refactor): 修复单元测试中 SemanticGraph 的 Mock

### 错误分析

`AttributeError: Mock object has no attribute 'search_paths'`
这个错误发生在 `packages/stitcher-refactor/tests/unit/test_rename_operation.py` 中。

在之前的修复中，我为 `RenameSymbolOperation` 添加了 `_path_to_fqn` 方法，这个方法需要从 `ctx.graph.search_paths` 获取项目的源文件搜索路径，以便将文件路径解析为模块 FQN。

然而，`test_rename_symbol_analyze_orchestration` 这个单元测试使用的是一个 `Mock(spec=SemanticGraph)` 对象。这个 mock 对象并没有被配置 `search_paths` 属性。因此，当 `analyze` 方法尝试访问 `ctx.graph.search_paths` 时，mock 对象按预期抛出了 `AttributeError`。

### 用户需求

修复 `test_rename_symbol_analyze_orchestration` 单元测试，使其通过。

### 评论

这是一个典型的 TDD（测试驱动开发）流程中会遇到的问题。当被测试单元的依赖发生变化时，相关的 mock 也必须同步更新。这次失败恰好验证了我们的重构确实引入了新的依赖，修复这个测试将使我们的测试套件重新稳固。

### 目标

1.  定位到 `packages/stitcher-refactor/tests/unit/test_rename_operation.py` 中的 `test_rename_symbol_analyze_orchestration` 函数。
2.  在 `mock_graph` 对象的初始化部分，为其添加 `search_paths` 属性，并赋予一个合理的值（例如，测试中使用的 `tmp_path`）。

### 基本原理

我将通过 `patch_file` 指令，为 `mock_graph` 对象添加一行配置 `mock_graph.search_paths = [tmp_path]`。这会满足 `analyze` 方法对该属性的依赖，使单元测试能够顺利执行，同时确保 `_path_to_fqn` 方法在测试环境中能正确地将文件路径解析为模块 FQN。

### 标签

#intent/fix #flow/ready #priority/high #comp/tests #scope/dx #ai/instruct #task/domain/refactoring #task/object/rename-operation #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 更新单元测试 Mock 配置

此操作将为 `mock_graph` 对象添加 `search_paths` 属性，以修复因依赖变更导致的测试失败。

~~~~~act
patch_file
packages/stitcher-refactor/tests/unit/test_rename_operation.py
~~~~~
~~~~~python.old
    mock_graph.registry = mock_registry

    # Let's use a real tmp_path for reading files to simplify mocking Path.read_text
    # We will create fake files that the operation can read.
    tmp_path = Path("/tmp/fake_project")  # conceptual
    mock_graph.root_path = tmp_path

    mock_workspace = Mock(spec=Workspace)
~~~~~
~~~~~python.new
    mock_graph.registry = mock_registry

    # Let's use a real tmp_path for reading files to simplify mocking Path.read_text
    # We will create fake files that the operation can read.
    tmp_path = Path("/tmp/fake_project")  # conceptual
    mock_graph.root_path = tmp_path
    # The refactored `analyze` method now depends on search_paths
    mock_graph.search_paths = [tmp_path]

    mock_workspace = Mock(spec=Workspace)
~~~~~

### 下一步建议

在应用此修复后，所有测试（包括单元测试和我们之前修复的集成测试）都应该能够通过。这将标志着 `RenameSymbolOperation` 的 sidecar 更新功能已经基本完成。下一步可以考虑将这些更改提交，并正式结束这个 bug 修复任务。
