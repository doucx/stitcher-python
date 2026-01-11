好的，我完全理解。你的分析是正确的：`rename_namespace.py` 中的代码路径没有被任何现有测试覆盖，导致 `pyright` 发现的类型错误在 CI 中被遗漏了。

我的任务是创建一个新的集成测试，该测试将专门执行 `RenameNamespaceOperation` 的 `analyze` 方法，从而暴露这个 `AttributeError`。我不会修复代码，只会创建这个会失败的测试。

## [WIP] test: 为 RenameNamespaceOperation 创建失败的测试

### 用户需求

创建一个新的测试用例，该用例会执行 `stitcher.refactor.operations.rename_namespace.RenameNamespaceOperation.analyze` 方法，并因为 `ctx.graph.registry` 属性不存在而失败。

### 评论

这是一个标准的测试驱动开发（TDD）或测试驱动修复（TDF）流程。首先编写一个重现错误的测试，是确保修复有效且防止未来回归的最佳实践。

### 目标

1.  在 `packages/stitcher-refactor/tests/integration/` 目录下创建一个新的测试文件 `test_rename_namespace_operation.py`。
2.  在该文件中，构建一个包含命名空间（例如 `my_pkg.utils`）的虚拟项目。
3.  初始化并填充 `RefactorContext`，包括 `Workspace`、`IndexStore` 和 `SemanticGraph`。
4.  实例化 `RenameNamespaceOperation` 来重命名一个命名空间。
5.  调用其 `analyze` 方法，这将触发 `AttributeError: 'SemanticGraph' object has no attribute 'registry'` 错误，导致测试失败。

### 基本原理

为了触发这个特定的错误，我们需要调用 `RenameNamespaceOperation.analyze` 方法。这个方法依赖于一个完整的 `RefactorContext`。因此，一个集成测试是必要的，它会使用 `WorkspaceFactory` 来构建一个真实的、虽然是临时的项目结构。然后，我们将创建并加载 `SemanticGraph` 和 `IndexStore`，模拟一个完整的重构环境。当调用 `analyze` 时，它将尝试访问不存在的 `ctx.graph.registry` 属性，从而使测试按预期失败。

### 标签

#intent/tooling #flow/ready #priority/high #comp/tests #comp/refactor #concept/state #ai/instruct #task/domain/testing #task/object/integration-test #task/action/creation #task/state/begin

---

### Script

#### Acts 1: 创建新的集成测试文件

我将创建一个新的测试文件。这个测试会搭建一个包含 `my_pkg/utils/helpers.py` 和一个使用它的 `my_pkg/main.py` 的项目。然后它会尝试分析一个重命名 `my_pkg.utils` 的操作，这将直接调用到有问题的代码。

~~~~~act
write_file
packages/stitcher-refactor/tests/integration/test_rename_namespace_operation.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.test_utils import WorkspaceFactory, create_populated_index

from stitcher.refactor.engine import (
    RefactorContext,
    SemanticGraph,
)
from stitcher.refactor.operations.rename_namespace import RenameNamespaceOperation
from stitcher.workspace import Workspace
from stitcher.refactor.sidecar import SidecarManager


def test_rename_namespace_operation_fails_as_expected(workspace_factory: WorkspaceFactory):
    """
    This test is designed to FAIL.
    It specifically targets the `analyze` method of `RenameNamespaceOperation`
    to confirm it hits the `AttributeError` due to the incorrect use of `ctx.graph.registry`.
    """
    # 1. Setup a workspace
    ws = (
        workspace_factory.with_project_name("my-project")
        .with_config({"scan_paths": ["src"]})
        .with_source(
            "src/my_pkg/utils/helpers.py",
            """
            def helper_func():
                return 1
            """,
        )
        .with_source(
            "src/my_pkg/main.py",
            """
            from my_pkg.utils.helpers import helper_func
            
            def main():
                return helper_func()
            """,
        )
        .with_raw_file("src/my_pkg/__init__.py", "")
        .with_raw_file("src/my_pkg/utils/__init__.py", "")
    )
    root_path = ws.build()

    # 2. Setup Refactor Context
    workspace = Workspace(root_path)
    index_store = create_populated_index(root_path)
    graph = SemanticGraph(workspace, index_store)
    graph.load_from_workspace()
    sidecar_manager = SidecarManager(root_path)
    ctx = RefactorContext(workspace, graph, sidecar_manager, index_store)

    # 3. Define the operation
    op = RenameNamespaceOperation(old_prefix="my_pkg.utils", new_prefix="my_pkg.tools")

    # 4. Execute the faulty method
    # This call is expected to raise an AttributeError.
    op.analyze(ctx)
~~~~~

### 下一步建议

现在，我已经创建了一个会失败的测试。下一步是运行测试套件，确认这个新测试确实因为 `AttributeError` 而失败。

一旦失败被确认，你就可以要求我生成一个新的计划来修复 `rename_namespace.py` 中的 bug。
