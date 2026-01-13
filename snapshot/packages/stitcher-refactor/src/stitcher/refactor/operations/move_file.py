from pathlib import Path
from typing import List

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.utils import path_to_fqn
from stitcher.refactor.engine.intent import (
    RefactorIntent,
    RenameIntent,
    MoveFileIntent,
    ScaffoldIntent,
)


class MoveFileOperation(AbstractOperation):
    def __init__(self, src_path: Path, dest_path: Path):
        self.src_path = src_path
        self.dest_path = dest_path

    def collect_intents(self, ctx: RefactorContext) -> List[RefactorIntent]:
        intents: List[RefactorIntent] = []

        # Resolve paths against the project root
        src_path = ctx.workspace.root_path.joinpath(self.src_path)
        dest_path = ctx.workspace.root_path.joinpath(self.dest_path)

        old_module_fqn = path_to_fqn(src_path, ctx.graph.search_paths)
        new_module_fqn = path_to_fqn(dest_path, ctx.graph.search_paths)

        # 1. Declare symbol rename intents if the module's FQN changes.
        if (
            old_module_fqn is not None
            and new_module_fqn is not None
            and old_module_fqn != new_module_fqn
        ):
            intents.append(RenameIntent(old_module_fqn, new_module_fqn))
            members = ctx.graph.iter_members(old_module_fqn)
            for member in members:
                if member.fqn == old_module_fqn:
                    continue
                if member.fqn.startswith(old_module_fqn + "."):
                    suffix = member.fqn[len(old_module_fqn) :]
                    target_new_fqn = new_module_fqn + suffix
                    intents.append(RenameIntent(member.fqn, target_new_fqn))

        # 2. Declare physical file move intents for main file and sidecars
        intents.append(MoveFileIntent(src_path, dest_path))
        for get_sidecar_path in [
            ctx.sidecar_manager.get_doc_path,
            ctx.sidecar_manager.get_signature_path,
        ]:
            sidecar_src = get_sidecar_path(src_path)
            if sidecar_src.exists():
                sidecar_dest = get_sidecar_path(dest_path)
                intents.append(MoveFileIntent(sidecar_src, sidecar_dest))

        # 3. Declare scaffolding intents for __init__.py files
        intents.extend(self._scaffold_init_intents(dest_path, ctx))
        return intents

    def _scaffold_init_intents(
        self, file_path: Path, ctx: RefactorContext
    ) -> List[ScaffoldIntent]:
        intents: List[ScaffoldIntent] = []
        parent = file_path.parent
        search_paths = ctx.graph.search_paths
        active_root = next(
            (
                sp
                for sp in sorted(
                    search_paths, key=lambda p: len(p.parts), reverse=True
                )
                if parent.is_relative_to(sp)
            ),
            None,
        )

        if not active_root:
            return []

        while parent != active_root and not (parent / "__init__.py").exists():
            intents.append(ScaffoldIntent(path=parent / "__init__.py", content=""))
            parent = parent.parent
        return intents
