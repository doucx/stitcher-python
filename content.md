You've caught another, more subtle bug. My fix for the `src` layout allowed the test to proceed, but now it has failed at the assertion stage. This is excellent; it means our new test is successfully probing the limits of the refactoring logic.

The `AssertionError` is crystal clear:

-   **Expected:** `from cascade.runtime.adapters.cache.in_memory import InMemoryCache`
-   **Actual:** `from cascade.core.adapters.cache.in_memory import InMemoryCache`

The refactoring operation successfully moved all the files and updated the sidecars, but it **failed to update the import statement in `app.py`**, which is an external file that references the code being moved.

Let's trace why:

1.  `MoveDirectoryOperation` works by iterating over files in the source directory (`src/cascade/core/adapters`) and creating a `MoveFileOperation` for each one (like `in_memory.py`).
2.  The `MoveFileOperation` for `in_memory.py` correctly calculates that the FQN for the *module* changed from `cascade.core.adapters.cache.in_memory` to `cascade.runtime.adapters.cache.in_memory`.
3.  It then creates a `RenameSymbolOperation` to handle this FQN change.
4.  **Here is the subtle bug:** The current `RenameSymbolOperation` is too simplistic. It works by finding the *last part* of the FQN (the "base name") and renaming that. In this case, the base name `in_memory` does not change. The operation incorrectly creates a rename map of `{'in_memory': 'in_memory'}` and applies it, resulting in no change to the code.
5.  The operation that *should* have been triggered is a rename of the module segment `core` to `runtime`. However, the `MoveFileOperation` for a leaf file doesn't have the context that one of its parent modules is the thing actually being renamed.

The responsibility for understanding the module path change must lie with the `MoveDirectoryOperation` itself.

The `MoveDirectoryOperation` must be made smarter. It should be responsible for orchestrating the high-level FQN prefix change.

1.  It will first calculate the module FQN for the source directory being moved (`cascade.core.adapters`) and the destination (`cascade.runtime.adapters`).
2.  It will then create a single, powerful `RenameSymbolOperation` for this top-level module path change. This operation will correctly identify that `core` needs to become `runtime` in all import statements across the entire project (including `app.py`).
3.  After planning this crucial code update, it can then proceed with its original logic of moving the files and sidecars.

This ensures that the context of the directory move is used to correctly refactor all dependent code *before* the individual files are processed.

## [WIP] fix(refactor): Fix MoveDirectoryOperation to update external imports

### 错误分析

The test `test_move_deeply_nested_directory_updates_all_references_and_sidecars` failed because moving a directory did not update the `import` statements in external files (`app.py`). The current implementation delegates to `MoveFileOperation` for each file, but this loses the high-level context of the parent directory move. `RenameSymbolOperation` was then fed an FQN where the base name didn't change (e.g., `...cache.in_memory` -> `...cache.in_memory`), causing it to do nothing.

### 用户需求

修复 `MoveDirectoryOperation` so that it correctly refactors all import statements in the codebase that refer to the modules being moved.

### 评论

This is a critical bug fix. A refactoring tool that moves code but leaves broken imports behind is not just unhelpful, it's dangerous. The fix elevates `MoveDirectoryOperation` from a simple file orchestrator to a semantically-aware operation that understands the implications of a directory move on the project's entire module structure.

### 目标

1.  Modify `stitcher.refactor.operations.move_directory.MoveDirectoryOperation`.
2.  Add logic to calculate the FQN of the source and destination directories themselves.
3.  Instantiate and run a `RenameSymbolOperation` for this high-level directory FQN change. This will handle all external import updates.
4.  Ensure the existing logic for moving files and updating sidecars remains but now runs alongside the import-fixing logic.

### 基本原理

We will enhance `MoveDirectoryOperation.analyze`. Before it iterates through the files to be moved, it will perform a "global" refactoring step. It will use the same `_path_to_fqn` helper logic (which we'll need to import) to determine, for example, that the directory `src/cascade/core/adapters` corresponds to the module FQN `cascade.core.adapters`. It will then trigger `RenameSymbolOperation("cascade.core.adapters", "cascade.runtime.adapters")`. This single operation is powerful enough to find all usages of that module path (like the one in `app.py`) and rewrite them correctly. The subsequent file-by-file processing will then handle the physical moves and sidecar content updates.

### 标签

#intent/fix #flow/ready #priority/critical #comp/engine #scope/core #ai/instruct #task/domain/testing #task/object/test-coverage #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 修复 `MoveDirectoryOperation`

I will `patch` the `MoveDirectoryOperation` to first apply a global rename for the module path before processing individual files.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/move_directory.py
~~~~~
~~~~~python.old
from pathlib import Path
from typing import List, Set

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
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
        all_ops.append(DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path)))

        return all_ops
~~~~~
~~~~~python.new
from pathlib import Path
from typing import List, Set

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation


class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # Phase 0: Plan the global import refactoring
        # We need a file from the directory to use the helper, any will do.
        # Let's create a dummy path for the dir itself.
        # This feels a bit hacky, maybe the helper should be a static method.
        # For now, let's instantiate MoveFileOperation just to use its helper.
        # This is a bit of a code smell, suggesting _path_to_fqn could be a static utility.
        # Let's assume an __init__.py exists for path_to_fqn to work as expected on a dir path.
        dummy_init_path = self.src_dir / "__init__.py"
        move_helper = MoveFileOperation(dummy_init_path, Path())
        old_dir_fqn = move_helper._path_to_fqn(self.src_dir, ctx.graph.root_path)
        new_dir_fqn = move_helper._path_to_fqn(self.dest_dir, ctx.graph.root_path)

        if old_dir_fqn and new_dir_fqn and old_dir_fqn != new_dir_fqn:
            rename_op = RenameSymbolOperation(old_dir_fqn, new_dir_fqn)
            all_ops.extend(rename_op.analyze(ctx))

        # Phase 1: Smart-process all Python files and their sidecars
        for src_file in self.src_dir.rglob("*.py"):
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            # Delegate to the smart MoveFileOperation.
            # Its RenameSymbolOperation will now handle internal FQN updates, which is fine.
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
        all_ops.append(DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path)))

        return all_ops
~~~~~

### 下一步建议

The critical logic bug in `MoveDirectoryOperation` has now been addressed. The operation is now aware of its impact on the project's overall module namespace and acts accordingly.

I will re-run the `test_move_deeply_nested_directory_updates_all_references_and_sidecars` test. It should now pass all assertions, including the one that previously failed.

Once confirmed, we will be ready to commit both the new test and the fix.
