from pathlib import Path
from typing import List

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
        Analyzes the directory move by planning moves for all contents
        and scheduling the source directory for deletion.
        """
        all_ops: List[FileOp] = []

        # Iterate over all items (files and directories)
        for src_item in self.src_dir.rglob("*"):
            relative_path = src_item.relative_to(self.src_dir)
            dest_item = self.dest_dir / relative_path
            rel_src_item = src_item.relative_to(ctx.graph.root_path)

            if src_item.is_file():
                if src_item.suffix == ".py":
                    # Smart move for Python files
                    file_mover = MoveFileOperation(src_item, dest_item)
                    file_specific_ops = file_mover.analyze(ctx)
                    all_ops.extend(file_specific_ops)
                else:
                    # Simple move for all other files
                    rel_dest_item = dest_item.relative_to(ctx.graph.root_path)
                    all_ops.append(MoveFileOp(rel_src_item, rel_dest_item))

        # After planning all moves, schedule the source directory for deletion
        all_ops.append(
            DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path))
        )

        return all_ops