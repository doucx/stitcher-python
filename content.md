Your diagnosis is correct. The traceback clearly indicates the root cause of the test failures: the refactoring process is crashing because `RefactorContext` is being instantiated without the required `lock_manager` argument. This prevents the planner from running and updating the `stitcher.lock` file, leading to the assertion failure in `test_refactor_move_updates_suri_in_lockfile`.

I will generate a plan to fix this by importing `LockFileManager` and providing it to the `RefactorContext`.

## [WIP] fix: Provide LockManager to RefactorContext

### 错误分析

1.  **根本原因**: 在 `packages/stitcher-application/src/stitcher/app/runners/refactor.py` 中，`RefactorContext` 的实例化缺少了必需的 `lock_manager` 参数，导致了 `TypeError`。
2.  **连锁反应**: 这个 `TypeError` 中断了 `refactor apply` 命令的执行。因此，用于更新 `stitcher.lock` 文件中的 SURI 的 `LockPathUpdateIntent` 从未被处理。
3.  **测试失败**: 由于 `stitcher.lock` 文件未被修改，测试中断言旧 SURI 不应存在的 `assert old_suri not in final_data` 失败了，因为旧 SURI 仍然存在。

### 用户需求

修复因 `refactor apply` 命令内部崩溃而导致的 `test_refactor_move_updates_suri_in_lockfile` 测试失败。

### 评论

这是一个典型的依赖注入问题。`RefactorContext` 的契约（其 `__init__` 方法）发生了变化，但其调用方没有相应更新。修复此问题将恢复重构引擎的核心功能。

### 目标

1.  在 `packages/stitcher-application/src/stitcher/app/runners/refactor.py` 中导入 `LockFileManager`。
2.  创建 `LockFileManager` 的实例。
3.  将此实例传递给 `RefactorContext` 的构造函数，以满足其依赖关系。

### 基本原理

`RefactorContext` 作为一个核心数据结构，需要向其消费者（如 `Planner`）提供所有必要的服务。`Planner` 依赖 `lock_manager` 来处理 `LockSymbolUpdateIntent` 和 `LockPathUpdateIntent`，从而修改 `stitcher.lock` 文件。通过在 `RefactorContext` 的创建点注入 `LockFileManager`，我们能够恢复 `Planner` 的完整功能，确保 SURI 可以在文件移动等重构操作后被正确更新。

### 标签

#intent/fix #flow/ready #priority/high #comp/engine #comp/refactor #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/refactor-context #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复 `refactor.py` 中的 `RefactorContext` 实例化

我将应用两个补丁到 `packages/stitcher-application/src/stitcher/app/runners/refactor.py` 文件。第一个补丁添加必要的 `LockFileManager` 导入，第二个补丁创建其实例并将其传递给 `RefactorContext`。

> **注意**: 尽管 `stitcher-application` 包未在文件树中列出，但我将根据您提供的明确无误的堆栈跟踪信息执行此操作，该信息是解决此问题的关键。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python.old
from stitcher.refactor.sidecar.manager import SidecarManager
~~~~~
~~~~~python.new
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.lang.sidecar import LockFileManager
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python.old
            sidecar_manager = SidecarManager(self.root_path)
            graph = SemanticGraph(workspace, self.index_store)

            graph.load_from_workspace()

            ctx = RefactorContext(
                workspace=workspace,
                graph=graph,
                sidecar_manager=sidecar_manager,
                index_store=self.index_store,
            )
~~~~~
~~~~~python.new
            sidecar_manager = SidecarManager(self.root_path)
            lock_manager = LockFileManager()
            graph = SemanticGraph(workspace, self.index_store)

            graph.load_from_workspace()

            ctx = RefactorContext(
                workspace=workspace,
                graph=graph,
                sidecar_manager=sidecar_manager,
                index_store=self.index_store,
                lock_manager=lock_manager,
            )
~~~~~

### 下一步建议

在应用此修复后，所有与 `refactor apply` 相关的测试（包括 `e2e` 和 `dry-run` 测试）应该都能通过。您可以运行完整的测试套件来验证这一点。
