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
