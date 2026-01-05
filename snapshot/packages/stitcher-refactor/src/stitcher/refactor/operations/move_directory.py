from pathlib import Path
from typing import List, Set

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src: Path, dest: Path):
        if not src.is_dir():
            raise ValueError(f"Source path is not a directory: {src}")
        self.src = src
        self.dest = dest

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # Phase 1: Smart-process all Python files and their sidecars
        for src_file in self.src.rglob("*.py"):
            relative_path = src_file.relative_to(self.src)
            dest_file = self.dest / relative_path

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
        for src_item in self.src.rglob("*"):
            if src_item in handled_paths or not src_item.is_file():
                continue

            # This item is a non-Python, non-sidecar file. Do a simple move.
            relative_path = src_item.relative_to(self.src)
            dest_item = self.dest / relative_path

            rel_src_item = src_item.relative_to(ctx.graph.root_path)
            rel_dest_item = dest_item.relative_to(ctx.graph.root_path)

            all_ops.append(MoveFileOp(rel_src_item, rel_dest_item))
            handled_paths.add(src_item)

        # Phase 3: Schedule the now-empty source directory for deletion
        all_ops.append(DeleteDirectoryOp(self.src.relative_to(ctx.graph.root_path)))

        return all_ops
