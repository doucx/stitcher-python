好的，我们来完成 `MoveDirectoryOperation` 重构的最后一步：让 Planner 理解并处理 `DeleteDirectoryIntent`。

这很简单，只需对 `Planner` 和 `engine/__init__.py` 进行少量修改即可。

## [WIP] feat(refactor): 为 Planner 添加 DeleteDirectory 支持

### 用户需求
扩展 `Planner` 以支持 `DeleteDirectoryIntent`，并改造 `MoveDirectoryOperation` 以正确声明目录删除意图。

### 评论
这是对 Planner 功能的一个小而重要的补充。通过让 `MoveDirectoryOperation` 显式声明删除源目录的意图，并让 Planner 理解这个意图，我们确保了重构操作的原子性和清洁度——移动完成后，不会留下空的源目录。

### 目标
1.  在 `MoveDirectoryOperation` 中，用 `DeleteDirectoryIntent` 替换旧的删除逻辑。
2.  更新 `engine/__init__.py` 以导出 `DeleteDirectoryIntent`。
3.  在 `Planner` 中添加处理 `DeleteDirectoryIntent` 的逻辑，将其转换为 `DeleteDirectoryOp`。

### 基本原理
我们将遵循与其他文件系统意图相同的模式：`MoveDirectoryOperation` 声明一个 `DeleteDirectoryIntent`，`Planner` 在聚合阶段捕获这个意图，并将其转换为一个具体的 `DeleteDirectoryOp` 添加到最终的 `FileOp` 列表中。

### 标签
#intent/build #flow/draft #priority/medium #comp/engine #scope/core #ai/instruct #task/domain/refactoring #task/object/planner #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 更新 `MoveDirectoryOperation`

我们首先让 `MoveDirectoryOperation` 正确地发出 `DeleteDirectoryIntent`。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    SidecarUpdateIntent,
    DeleteDirectoryOp,
    ScaffoldIntent,
)
~~~~~
~~~~~python.new
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
)
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
        # 3. Declare deletion of the source directory
        # TODO: This should be a `DeleteDirectoryIntent`. For now, this is a placeholder.
        # intents.append(DeleteDirectoryIntent(self.src_dir))
~~~~~
~~~~~python.new
        # 3. Declare deletion of the source directory
        intents.append(DeleteDirectoryIntent(self.src_dir))
~~~~~

#### Acts 2: 更新 `engine/__init__.py`

确保新的 Intent 类型被正确导出。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/__init__.py
~~~~~
~~~~~python.old
    MoveFileIntent,
    DeleteFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
)
~~~~~
~~~~~python.new
    MoveFileIntent,
    DeleteFileIntent,
    ScaffoldIntent,
    SidecarUpdateIntent,
    DeleteDirectoryIntent,
)
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/__init__.py
~~~~~
~~~~~python.old
    "MoveFileIntent",
    "DeleteFileIntent",
    "ScaffoldIntent",
    "SidecarUpdateIntent",
]
~~~~~
~~~~~python.new
    "MoveFileIntent",
    "DeleteFileIntent",
    "ScaffoldIntent",
    "SidecarUpdateIntent",
    "DeleteDirectoryIntent",
]
~~~~~

#### Acts 3: 更新 Planner

最后，让 Planner 知道如何处理这个新的 Intent。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
from stitcher.refactor.engine.transaction import (
    FileOp,
    MoveFileOp,
    WriteFileOp,
    DeleteFileOp,
)
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    MoveFileIntent,
    DeleteFileIntent,
    ScaffoldIntent,
)
~~~~~
~~~~~python.new
from stitcher.refactor.engine.transaction import (
    FileOp,
    MoveFileOp,
    WriteFileOp,
    DeleteFileOp,
    DeleteDirectoryOp,
)
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    SidecarUpdateIntent,
    MoveFileIntent,
    DeleteFileIntent,
    ScaffoldIntent,
    DeleteDirectoryIntent,
)
~~~~~
~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/planner.py
~~~~~
~~~~~python.old
            elif isinstance(intent, DeleteFileIntent):
                all_ops.append(DeleteFileOp(intent.path.relative_to(ctx.graph.root_path)))
            elif isinstance(intent, ScaffoldIntent):
                all_ops.append(WriteFileOp(intent.path.relative_to(ctx.graph.root_path), intent.content))
~~~~~
~~~~~python.new
            elif isinstance(intent, DeleteFileIntent):
                all_ops.append(DeleteFileOp(intent.path.relative_to(ctx.graph.root_path)))
            elif isinstance(intent, DeleteDirectoryIntent):
                all_ops.append(DeleteDirectoryOp(intent.path.relative_to(ctx.graph.root_path)))
            elif isinstance(intent, ScaffoldIntent):
                all_ops.append(WriteFileOp(intent.path.relative_to(ctx.graph.root_path), intent.content))
~~~~~

### 下一步建议

我们已经完成了所有 Operation 的改造，并且 Planner 现在能够处理所有核心意图。

现在是时候进入路线图的最后一步了：**验证与回归测试**。

我建议我们依次执行以下操作：
1.  **修复 `test_move_directory_e2e.py`**: 更新此测试以使用新的 `Planner.plan` 流程，并验证它是否能成功通过。
2.  **修复所有其他集成测试**: 逐一修复 `tests/integration` 目录下因 `analyze` 方法被移除而损坏的其他测试。
3.  **运行完整的测试套件**: 确保我们的重构没有引入任何回归问题。
