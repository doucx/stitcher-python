好的，我们开始执行重构路线图中的第一阶段任务：**基础能力下沉 (Infrastructure Sinking)**。

第一步是将文件事务系统从 `stitcher-refactor` 迁移到 `stitcher-common`，使其成为一个供全系统使用的共享基础组件。这将为后续统一文件操作和实现全局 `--dry-run` 功能奠定基础。

我将生成一个计划来创建新的目录结构，移动核心逻辑，并更新相关的代码导入。

## [WIP] refactor(common): 将事务系统迁移至 stitcher-common

### 用户需求

根据“Stitcher 重构路线图”，实施“阶段一：基础能力下沉”中的“1.1 统一文件事务系统”任务。需要将 `stitcher.refactor.engine.transaction` 模块的功能迁移至新的 `stitcher.common.transaction` 模块。

### 评论

这是重构计划中至关重要且正确的第一步。通过将事务处理能力下沉到 `stitcher-common`，我们消除了最明显的代码重复，并为建立一个更加健壮、统一的平台层奠定了基础。此举完全符合“单一真理来源”和“平台优于功能”的架构原则。

### 目标

1.  在 `stitcher-common` 包中创建新的 `transaction` 模块目录。
2.  将 `stitcher-refactor` 中的 `transaction.py` 文件移动到新位置，并重命名为 `manager.py`。
3.  在新模块的 `__init__.py` 中暴露公共 API (`TransactionManager`, `FileOp` 等)。
4.  更新 `stitcher-refactor` 中所有对旧事务模块的引用，使其指向 `stitcher-common` 中的新位置。
5.  从 `stitcher-refactor` 的公共 API 中移除已迁移的 `TransactionManager`。

### 基本原理

遵循重构路线图 `Stitcher 重构路线图：架构融合与能力下沉.md` 中定义的“基础设施下沉”策略。当前，文件事务逻辑仅存在于 `stitcher-refactor` 包中，导致其他包（如 `stitcher-application`）无法复用，并进行了重复的、非事务性的文件写入。将此核心功能迁移至基础包 `stitcher-common`，可以将其提升为全系统共享的 IO 基础设施，是消除技术债、提升架构一致性的关键步骤。

### 标签

#intent/refine #flow/ready #priority/high #comp/common #comp/refactor #concept/executor #scope/core #ai/instruct #task/domain/refactoring #task/object/transaction-system #task/action/migration #task/state/begin

---

### Script

#### Acts 1: 创建新的事务模块目录结构

首先，我们在 `stitcher-common` 包中创建用于存放事务逻辑的新目录。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-common/src/stitcher/common/transaction
~~~~~

#### Acts 2: 迁移核心事务逻辑

我们将 `transaction.py` 文件从 `stitcher-refactor` 移动到新创建的目录中，并将其重命名为 `manager.py` 以更好地反映其主要内容。

~~~~~act
move_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.py
packages/stitcher-common/src/stitcher/common/transaction/manager.py
~~~~~

~~~~~act
move_file
packages/stitcher-refactor/src/stitcher/refactor/engine/transaction.stitcher.yaml
packages/stitcher-common/src/stitcher/common/transaction/manager.stitcher.yaml
~~~~~

#### Acts 3: 暴露新的公共 API

为了让其他包可以方便地从 `stitcher.common.transaction` 导入，我们创建一个 `__init__.py` 文件来暴露模块内的核心类。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/transaction/__init__.py
~~~~~
~~~~~python
from .manager import (
    TransactionManager,
    FileOp,
    WriteFileOp,
    MoveFileOp,
    DeleteFileOp,
    DeleteDirectoryOp,
    FileSystemAdapter,
    RealFileSystem,
)

__all__ = [
    "TransactionManager",
    "FileOp",
    "WriteFileOp",
    "MoveFileOp",
    "DeleteFileOp",
    "DeleteDirectoryOp",
    "FileSystemAdapter",
    "RealFileSystem",
]
~~~~~

#### Acts 4: 更新 `stitcher-refactor` 的依赖导入

现在，我们需要更新 `stitcher-refactor` 的代码，使其从新的共享位置导入事务类。

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
    DeleteDirectoryOp,
)
~~~~~
~~~~~python.new
from stitcher.common.transaction import (
    FileOp,
    MoveFileOp,
    WriteFileOp,
    DeleteFileOp,
    DeleteDirectoryOp,
)
~~~~~

#### Acts 5: 清理旧的 API 导出

最后，我们从 `stitcher-refactor` 的 `engine` 模块中移除对旧 `TransactionManager` 的导出，完成解耦。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/__init__.py
~~~~~
~~~~~python.old
from .transaction import TransactionManager
~~~~~
~~~~~python.new

~~~~~

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/__init__.py
~~~~~
~~~~~python.old
__all__ = [
    "TransactionManager",
    "RefactorContext",
~~~~~
~~~~~python.new
__all__ = [
    "RefactorContext",
~~~~~

### 下一步建议

我们已经成功将事务系统迁移到了 `stitcher-common`。根据路线图，下一个关键步骤是**适配 `stitcher-application`**：

-   修改 `stitcher-application` 中的 `PumpRunner`, `GenerateRunner`, `TransformRunner` 等，让它们停止直接调用 `path.write_text`。
-   转而让它们生成 `FileOp` 并通过 `TransactionManager` 来执行文件写入。

这个改动将使得 `pump`, `generate`, `strip` 等核心命令**自动获得事务能力和 `--dry-run` 的潜力**。如果你同意，我将准备执行此项改造的计划。
