好的，我们开始验证与回归测试阶段。

首先，我将修复 `test_move_directory_e2e.py`，使其适配 Planner 2.0 的新架构。这与我们之前修复 "Smoking Gun" 测试的操作非常相似：用 `MigrationSpec` 和 `Planner.plan` 调用替换旧的 `analyze` 调用。

## [WIP] test: 适配 Planner v2 更新目录移动 E2E 测试

### 用户需求
更新 `test_move_directory_e2e.py` 以使用新的 `Planner.plan` 流程，并验证其在 Planner 2.0 架构下依然能成功通过。

### 评论
这是对新架构的第一次正式验证。`MoveDirectoryOperation` 是最复杂的操作之一，因为它涉及到多种类型的意图（重命名、移动、更新sidecar、脚手架、删除）。如果这个测试能够通过，将极大地增强我们对 Planner 2.0 意图聚合和执行规划能力的信心。

### 目标
1.  修改 `test_move_directory_e2e.py` 的 "ACT" 部分。
2.  使用 `MigrationSpec` 来封装 `MoveDirectoryOperation`。
3.  调用 `Planner().plan(spec, ctx)` 来生成文件操作。
4.  保持断言不变，验证测试是否通过。

### 基本原理
通过将测试用例从直接调用 `analyze` 迁移到通过 `Planner` 进行规划，我们现在测试的是整个 Planner 2.0 工作流的端到端正确性，而不仅仅是单个 `Operation` 的意图收集。

### 标签
#intent/tooling #intent/fix #flow/draft #priority/high #comp/tests #scope/core #ai/instruct #task/domain/refactoring #task/object/planner #task/action/verify-fix #task/state/continue

---

### Script

#### Acts 1: 更新 `test_move_directory_e2e.py`

我们将修改测试的执行部分，以适配新的 Planner 流程。

~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
    op = MoveDirectoryOperation(core_dir, services_dir)
    file_ops = op.analyze(ctx)

    # 3. EXECUTION
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        else:
            tm.add_write(fop.path, fop.content)
    tm.commit()
~~~~~
~~~~~python.new
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner
    from stitcher.refactor.engine.transaction import DeleteDirectoryOp

    spec = MigrationSpec().add(MoveDirectoryOperation(core_dir, services_dir))
    planner = Planner()
    file_ops = planner.plan(spec, ctx)

    # 3. EXECUTION
    tm = TransactionManager(project_root)
    for fop in file_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, DeleteDirectoryOp):
            tm.add_delete_dir(fop.path)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
    tm.commit()
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/tests/integration/test_move_directory_e2e.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    DeleteDirectoryOp,
)
~~~~~
~~~~~python.new
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    WriteFileOp,
)
~~~~~

### 下一步建议

`test_move_directory_e2e.py` 已经成功适配。

现在，我将继续修复 `tests/integration` 目录下的其他所有因 `analyze` 接口变更而损坏的测试用例，以完成我们的回归测试阶段。我会逐个文件进行修复。
