from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    DeleteDirectoryIntent,
    ScaffoldIntent,
)


class MoveDirectoryOperation(AbstractOperation):
    def __init__(self, src_dir: Path, dest_dir: Path):
        self.src_dir = src_dir
        self.dest_dir = dest_dir

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []
        src_dir = ctx.workspace.root_path.joinpath(self.src_dir)
        dest_dir = ctx.workspace.root_path.joinpath(self.dest_dir)

        # 1. Declare namespace rename intent
        old_prefix = path_to_fqn(src_dir, ctx.graph.search_paths)
        new_prefix = path_to_fqn(dest_dir, ctx.graph.search_paths)
        if old_prefix and new_prefix and old_prefix != new_prefix:
            intents.append(RenameIntent(old_prefix, new_prefix))
            for member in ctx.graph.iter_members(old_prefix):
                if member.fqn.startswith(old_prefix + "."):
                    suffix = member.fqn[len(old_prefix) :]
                    new_fqn = new_prefix + suffix
                    intents.append(RenameIntent(member.fqn, new_fqn))

        # 2. Declare physical file moves for all files within the directory
        if src_dir.is_dir():
            for src_item in src_dir.rglob("*"):
                if not src_item.is_file():
                    continue
                relative_path = src_item.relative_to(src_dir)
                dest_item = dest_dir / relative_path
                intents.append(MoveFileIntent(src_item, dest_item))

        # 3. Declare deletion of the source directory
        intents.append(DeleteDirectoryIntent(src_dir))

        # 4. Declare scaffolding of __init__.py files
        intents.extend(self._scaffold_init_intents(dest_dir, ctx))
        return intents

    def _scaffold_init_intents(
        self, directory_path: Path, ctx: RefactorContext
    ) -> List[ScaffoldIntent]:
        intents: List[ScaffoldIntent] = []
        search_paths = ctx.graph.search_paths
        active_root = next(
            (
                sp
                for sp in sorted(
                    search_paths, key=lambda p: len(p.parts), reverse=True
                )
                if directory_path.is_relative_to(sp)
            ),
            None,
        )

        if not active_root:
            return []

        current = directory_path
        while current != active_root and not (current / "__init__.py").exists():
            intents.append(ScaffoldIntent(path=current / "__init__.py", content=""))
            current = current.parent
        return intents
