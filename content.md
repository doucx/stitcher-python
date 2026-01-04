好的，我来分析这个 `FileNotFoundError`。这是一个非常微妙但典型的并发逻辑错误，即使在单线程代码中也会出现。

## [WIP] fix(refactor): 消除 MoveDirectoryOperation 中的重复文件操作

### 错误分析

**观察到的失败**: `FileNotFoundError: [Errno 2] No such file or directory: '.../mypkg/core/utils.stitcher.yaml'`。

**直接原因**: 当 `TransactionManager` 尝试执行一个 `MoveFileOp` 来移动 `utils.stitcher.yaml` 时，该文件已不存在于源位置。

**根本原因**: 这是一个**重复操作 (Double Operation)** 的逻辑缺陷。`MoveDirectoryOperation` 的 `analyze` 方法中存在两种机制，它们会**为同一个 Sidecar 文件创建两个独立的 `MoveFileOp`**：

1.  **智能路径 (Smart Path)**: 当 `rglob` 循环找到 `utils.py` 时，它会创建一个 `MoveFileOperation` 实例。这个实例的 `analyze` 方法非常智能，它会自动查找 `utils.py` 的所有 Sidecar 文件（包括 `utils.stitcher.yaml`）并为它们创建 `MoveFileOp`。这是我们期望的行为。
2.  **朴素路径 (Naive Path)**: `rglob("*")` 循环会继续执行，并且它会**再次**找到 `utils.stitcher.yaml` 文件本身。由于这个文件不是 `.py` 文件，代码会进入 `else` 块，为它创建一个**第二个、重复的** `MoveFileOp`。

**执行时的冲突**: `TransactionManager` 的操作队列中现在包含了两个完全相同的 `MoveFileOp(src=".../utils.stitcher.yaml", ...)`。
-   第一个 `MoveFileOp` 成功执行，文件被移动。
-   当轮到第二个 `MoveFileOp` 执行时，它尝试再次移动同一个源文件，但该文件已经被第一个操作移走了，因此 `shutil.move` 无法找到源文件，抛出 `FileNotFoundError`。

### 用户需求
修复 `MoveDirectoryOperation` 的逻辑，确保每个文件（包括代码文件和 Sidecar 文件）在整个事务中只被计划移动一次。

### 评论
这是一个很好的例子，说明了在组合操作时，确保每个操作的幂等性或唯一性是多么重要。这个 bug 暴露了当前实现中的一个隐藏的逻辑重叠。修复它将使重构引擎的行为更加可预测和健壮。

### 目标
1.  修改 `MoveDirectoryOperation.analyze` 方法。
2.  引入一个机制（例如一个 `set`）来跟踪已经被处理过的文件路径，以防止重复生成移动操作。

### 基本原理
我们将重构 `analyze` 方法的逻辑。我们将采用一个两阶段的方法来确保每个文件只被处理一次：
1.  **第一阶段 (智能处理)**: 我们将首先只遍历 `.py` 文件。为每个 `.py` 文件调用 `MoveFileOperation`，它会智能地处理该文件及其所有关联的 Sidecar 文件。我们将把所有这些被处理过的文件（`.py` 和 Sidecars）的路径添加到一个 `handled_paths` 集合中。
2.  **第二阶段 (通用处理)**: 接下来，我们将遍历目录中的所有文件（`*`）。对于每个文件，我们首先检查它是否已经在 `handled_paths` 集合中。如果是，就跳过它。如果不是，那么它就是一个独立的非 Python 文件（如 `config.txt`），我们为它创建一个简单的 `MoveFileOp`。
这种方法确保了 `.py` 文件的 Sidecar 由其主文件负责处理，而所有其他文件则被单独处理，从而完美地消除了操作重叠。

### 标签
#intent/fix #flow/ready #priority/critical #comp/engine #concept/executor #scope/core #ai/instruct #task/domain/refactoring #task/object/directory-move #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修正 `MoveDirectoryOperation` 的逻辑

我将使用 `write_file` 来替换 `move_directory.py` 的全部内容，以实现上述的防重叠逻辑。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Set

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


class MoveDirectoryOperation(AbstractOperation):
    """Orchestrates the move of an entire directory."""

    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        """
        Analyzes the directory move by planning moves for all contents,
        ensuring each file is processed exactly once, and scheduling the
        source directory for deletion.
        """
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # Phase 1: Smart-process all Python files and their sidecars
        for src_file in self.src_dir.rglob("*.py"):
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            # Delegate to the smart MoveFileOperation
            file_mover = MoveFileOperation(src_file, dest_file)
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

            # Mark the source file and its potential sidecars as handled
            handled_paths.add(src_file)
            handled_paths.add(src_file.with_suffix(".stitcher.yaml"))
            sig_rel_path = src_file.relative_to(ctx.graph.root_path).with_suffix(
                ".json"
            )
            sig_abs_path = ctx.graph.root_path / ".stitcher/signatures" / sig_rel_path
            handled_paths.add(sig_abs_path)

        # Phase 2: Process all remaining items (non-Python files)
        for src_item in self.src_dir.rglob("*"):
            if src_item in handled_paths or not src_item.is_file():
                continue

            # This item is a non-Python, non-sidecar file. Do a simple move.
            relative_path = src_item.relative_to(self.src_dir)
            dest_item = self.dest_dir / relative_path
            
            rel_src_item = src_item.relative_to(ctx.graph.root_path)
            rel_dest_item = dest_item.relative_to(ctx.graph.root_path)
            
            all_ops.append(MoveFileOp(rel_src_item, rel_dest_item))
            handled_paths.add(src_item)

        # Phase 3: Schedule the now-empty source directory for deletion
        all_ops.append(
            DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path))
        )

        return all_ops
~~~~~

### 下一步建议
该修复是精确且有针对性的。请执行此计划，然后重新运行测试。我非常有信心这次测试将会通过，因为我们已经从根本上解决了重复操作的问题。

测试通过后，我们可以自信地认为 `MoveDirectoryOperation` 已经健壮，并可以继续进行**阶段四**的工作：构建用户接口（CLI）。
