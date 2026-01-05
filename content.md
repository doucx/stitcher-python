当然，这是预料之中的。我们刚刚用 `collect_intents` 替换了 `analyze` 方法，所以测试文件现在需要同步更新。

我将修改测试文件，使其使用新的 `Planner` 和 `collect_intents` 流程，而不是模拟旧的、错误的线性分析模式。这将使我们的 "Smoking Gun" 测试真正地去验证 Planner 2.0 的端到端行为。

## [WIP] test: 更新测试用例以适配 Planner v2

### 用户需求
修改 `test_fail_concurrent_move_and_rename.py` 测试，使其调用新的 `Planner.plan` 方法，并验证 Planner 2.0 能否正确处理并发修改，从而使测试通过。

### 评论
这个修改标志着我们从“证明旧架构有缺陷”阶段，正式进入“验证新架构已修复缺陷”阶段。通过让测试使用完整的 Planner 2.0 流程，我们能够端到端地验证意图收集、聚合、批量重命名和文件操作生成是否协同工作，最终产生正确的结果。

### 目标
1.  移除测试中对旧 `analyze` 方法的调用。
2.  创建一个 `MigrationSpec` 来收集所有操作。
3.  实例化 `Planner` 并调用其新的 `plan` 方法来生成最终的 `FileOp` 列表。
4.  保持断言不变，预期 Planner 2.0 能够通过这些断言。

### 基本原理
测试的 arrange 和 assert 部分保持不变，核心是 act 部分的重构。我们将不再手动、线性地调用 `analyze` 并拼接结果，而是模拟一个真实的迁移场景：将所有操作添加到一个 `MigrationSpec` 中，然后让 `Planner` 来处理这个规范。这是对新架构最直接的验证。

### 标签
#intent/tooling #intent/fix #flow/draft #priority/critical #comp/tests #scope/core #ai/instruct #task/domain/refactoring #task/object/planner #task/action/verify-fix #task/state/continue

---

### Script

#### Acts 1: 更新测试文件以使用 Planner 2.0

我们将重写 `test_fail_concurrent_move_and_rename.py` 的中间部分，用新的 Planner 替换旧的模拟逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_fail_concurrent_move_and_rename.py
~~~~~
~~~~~python.old
    # Analyze independently (Linear Architecture)
    ops_1 = move_op.analyze(ctx)
    ops_2 = rename_class_op.analyze(ctx)
    ops_3 = rename_func_op.analyze(ctx)
    
    all_ops = ops_1 + ops_2 + ops_3

    tm = TransactionManager(project_root)
    for fop in all_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
        elif isinstance(fop, DeleteFileOp):
            tm.add_delete_file(fop.path)
            
    tm.commit()
~~~~~
~~~~~python.new
    # Use the new Planner V2 architecture
    from stitcher.refactor.migration import MigrationSpec
    from stitcher.refactor.engine.planner import Planner

    spec = MigrationSpec()
    spec.add(move_op)
    spec.add(rename_class_op)
    spec.add(rename_func_op)

    planner = Planner()
    all_ops = planner.plan(spec, ctx)

    tm = TransactionManager(project_root)
    for fop in all_ops:
        if isinstance(fop, MoveFileOp):
            tm.add_move(fop.path, fop.dest)
        elif isinstance(fop, WriteFileOp):
            tm.add_write(fop.path, fop.content)
        elif isinstance(fop, DeleteFileOp):
            tm.add_delete_file(fop.path)

    tm.commit()
~~~~~

### 下一步建议

现在测试文件已经更新，以完全采用 Planner 2.0 的工作流程。

请再次运行测试。如果一切顺利，它现在应该会变绿，证明我们已经成功绞杀了这个核心架构缺陷。如果测试通过，我们就可以满怀信心地进入路线图的最后一步：**验证与回归测试**，确保新架构在所有其他场景下依然稳健。
