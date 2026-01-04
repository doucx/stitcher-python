from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp
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
        Analyzes the directory move by creating a MoveFileOperation for each file.
        """
        all_ops: List[FileOp] = []

        # Find all Python files within the source directory
        for src_file in self.src_dir.rglob("*.py"):
            # Calculate the corresponding destination path for the file
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            # Delegate the complex analysis to the existing MoveFileOperation
            file_mover = MoveFileOperation(src_file, dest_file)

            # Analyze the individual file move and collect the resulting operations
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

        return all_ops