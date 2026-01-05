遵循 Quipu 协议，我将修正该测试以确保它能准确揭示**内容合并冲突 (Content Merge Conflict)** 这一架构盲点。

之前的测试通过是因为现有的 `TransactionManager` 具备基础的路径 Rebase 能力，这掩盖了路径冲突的问题。新的测试将引入**双重修改 (Concurrent Modifications)**，这是简单的 Rebase 无法解决的——后一个 `Write` 必然会覆盖前一个 `Write`，导致数据丢失。

## [WIP] test: 修正架构缺陷验证测试 (Lost Edit Scenario)

### 用户需求
修正 `test_fail_concurrent_move_and_rename.py`，使其能稳定地复现数据丢失问题。

### 评论
原测试意外通过，因为 `TransactionManager._rebase_ops` 处理了路径变更。新测试将通过引入针对同一文件的两次独立内容修改（两个不同的重命名操作），迫使系统暴露出“后写入覆盖先写入”的缺陷。

### 目标
1.  在一个文件中定义两个符号：`class A` 和 `def b`。
2.  在一个事务中同时执行三个操作：
    - Move 文件。
    - Rename `A` -> `NewA`。
    - Rename `b` -> `NewB`。
3.  断言最终文件同时包含 `NewA` 和 `NewB`。
4.  预期：当前架构只能保留最后一个操作的结果，导致测试失败。

### 基本原理
当前架构是线性的：Op1 读取原始代码 -> 生成全量新代码；Op2 读取原始代码 -> 生成全量新代码。当它们被串行执行时，Op2 的全量写入会无情地覆盖 Op1 的成果。

### 标签
#intent/tooling #flow/draft #priority/critical #comp/tests #concept/state #scope/core #ai/instruct #task/domain/refactoring #task/object/planner #task/action/verify-failure #task/state/continue

---

### Script

#### Acts 1: 重写测试逻辑

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/tests/integration/test_fail_concurrent_move_and_rename.py
~~~~~
~~~~~python
import pytest
from stitcher.refactor.engine.graph import SemanticGraph
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import (
    TransactionManager,
    MoveFileOp,
    WriteFileOp,
    DeleteFileOp
)
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory

def test_smoking_gun_concurrent_modifications_lost_edit(tmp_path):
    """
    THE SMOKING GUN TEST (REVISED)
    
    Scenario:
    We have a file 'mypkg/core.py' containing TWO symbols.
    We want to perform a transaction that:
    1. Moves the file.
    2. Renames Symbol A.
    3. Renames Symbol B.
    
    Current Architecture Failure Mode (The "Lost Edit"):
    1. MoveOp: Plans Move(core -> utils).
    2. RenameOp(A): Reads 'core.py' (original), replaces A->NewA. Plans: Write(core, Content_A_Modified).
    3. RenameOp(B): Reads 'core.py' (original), replaces B->NewB. Plans: Write(core, Content_B_Modified).
    
    Execution (even with Path Rebasing):
    1. Move(core -> utils) executes.
    2. Write(utils, Content_A_Modified) executes. (File has NewA, but old B).
    3. Write(utils, Content_B_Modified) executes. (File has NewB, but old A).
       -> IT OVERWRITES THE PREVIOUS WRITE.
    
    Result: The file ends up with only ONE of the renames applied.
    """
    # 1. ARRANGE
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory.with_pyproject(".")
        .with_source("mypkg/__init__.py", "")
        .with_source(
            "mypkg/core.py", 
            """
class OldClass:
    pass

def old_func():
    pass
            """
        )
        .build()
    )

    src_path = project_root / "mypkg/core.py"
    dest_path = project_root / "mypkg/utils.py"
    
    # 2. ACT
    workspace = Workspace(root_path=project_root)
    graph = SemanticGraph(workspace=workspace)
    graph.load("mypkg")
    
    sidecar_manager = SidecarManager(root_path=project_root)
    ctx = RefactorContext(
        workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
    )

    # Three operations touching the same file
    move_op = MoveFileOperation(src_path, dest_path)
    rename_class_op = RenameSymbolOperation("mypkg.core.OldClass", "mypkg.utils.NewClass")
    rename_func_op = RenameSymbolOperation("mypkg.core.old_func", "mypkg.utils.new_func")

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

    # 3. ASSERT
    assert dest_path.exists(), "Destination file missing!"
    
    content = dest_path.read_text()
    
    has_new_class = "class NewClass" in content
    has_new_func = "def new_func" in content
    
    # Debug output
    if not (has_new_class and has_new_func):
        print("\n--- FAILURE DIAGNOSTIC ---")
        print(f"Content of {dest_path}:")
        print(content)
        print("--------------------------")

    # Both renames must be present. 
    # Current architecture will fail this: one will be missing.
    assert has_new_class, "Lost Edit: Class rename was overwritten!"
    assert has_new_func, "Lost Edit: Function rename was overwritten!"
~~~~~

### 下一步建议

确认测试失败（变红）后，我们将正式开始 `Planner 2.0` 的开发工作。我们将按照路线图，首先在 `stitcher.refactor.intent` 模块中定义 `RefactorIntent` 类层次结构。
