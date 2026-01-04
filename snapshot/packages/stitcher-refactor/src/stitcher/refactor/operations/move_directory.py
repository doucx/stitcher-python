from pathlib import Path
from typing import List, Set

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, MoveFileOp, DeleteDirectoryOp
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.move_file import MoveFileOperation


class MoveDirectoryOperation(AbstractOperation):
    """
    Orchestrates the move of an entire directory, including Python files,
    sidecars, other assets, and finally cleaning up the source directory.
    """

    def __init__(self, src_dir: Path, dest_dir: Path):
        if not src_dir.is_dir():
            raise ValueError(f"Source path is not a directory: {src_dir}")
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        """
        Analyzes the directory move using a three-phase process:
        1. Semantic Move: Handles Python files and their sidecars, updating references.
        2. Verbatim Move: Moves all remaining files.
        3. Cleanup: Deletes the now-empty source directory.
        """
        all_ops: List[FileOp] = []
        handled_paths: Set[Path] = set()

        # --- Phase 1: Semantic Move ---
        for src_file in self.src_dir.rglob("*.py"):
            relative_path = src_file.relative_to(self.src_dir)
            dest_file = self.dest_dir / relative_path

            file_mover = MoveFileOperation(src_file, dest_file)
            file_specific_ops = file_mover.analyze(ctx)
            all_ops.extend(file_specific_ops)

            # Track which source files were handled by the semantic mover
            # Note: MoveFileOperation handles the .py, .yaml, and .json sidecars.
            handled_paths.add(src_file)
            if src_file.with_suffix(".stitcher.yaml").exists():
                handled_paths.add(src_file.with_suffix(".stitcher.yaml"))

            rel_sig_path = (
                ctx.graph.root_path
                / ".stitcher/signatures"
                / src_file.relative_to(ctx.graph.root_path).with_suffix(".json")
            )
            if rel_sig_path.exists():
                handled_paths.add(rel_sig_path)

        # --- Phase 2: Verbatim Move ---
        for src_item in self.src_dir.rglob("*"):
            if not src_item.is_file():
                continue
            if src_item in handled_paths:
                continue

            relative_path = src_item.relative_to(self.src_dir)
            dest_item = self.dest_dir / relative_path

            all_ops.append(
                MoveFileOp(
                    src_item.relative_to(ctx.graph.root_path),
                    dest_item.relative_to(ctx.graph.root_path),
                )
            )
            handled_paths.add(src_item)

        # --- Phase 3: Cleanup ---
        all_ops.append(
            DeleteDirectoryOp(self.src_dir.relative_to(ctx.graph.root_path))
        )

        return all_ops