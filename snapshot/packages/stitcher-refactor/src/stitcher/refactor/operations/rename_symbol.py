import libcst as cst
from collections import defaultdict
from typing import List, Dict
from pathlib import Path

from .base import AbstractOperation
from .transforms.rename_transformer import SymbolRenamerTransformer
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.transaction import FileOp, WriteFileOp
from stitcher.refactor.engine.graph import UsageLocation


class RenameSymbolOperation(AbstractOperation):
    def __init__(self, old_fqn: str, new_fqn: str):
        self.old_fqn = old_fqn
        self.new_fqn = new_fqn

    def _get_base_name(self, fqn: str) -> str:
        return fqn.split(".")[-1]

    def analyze(self, ctx: RefactorContext) -> List[FileOp]:
        ops: List[FileOp] = []
        
        old_name = self._get_base_name(self.old_fqn)
        new_name = self._get_base_name(self.new_fqn)
        
        if old_name == new_name:
            return [] # No change needed

        rename_map = {old_name: new_name}
        
        # 1. Find all usages
        usages = ctx.graph.registry.get_usages(self.old_fqn)
        
        # 2. Group usages by file
        usages_by_file: Dict[Path, List[UsageLocation]] = defaultdict(list)
        for usage in usages:
            usages_by_file[usage.file_path].append(usage)
            
        # 3. For each affected file, apply transformation
        for file_path, file_usages in usages_by_file.items():
            try:
                # We assume file_path is absolute from Griffe
                original_source = file_path.read_text(encoding="utf-8")
                
                module = cst.parse_module(original_source)
                wrapper = cst.MetadataWrapper(module)
                
                transformer = SymbolRenamerTransformer(rename_map, file_usages)
                modified_module = wrapper.visit(transformer)

                if modified_module.code != original_source:
                    # The path in WriteFileOp should be relative to the project root
                    relative_path = file_path.relative_to(ctx.graph.root_path)
                    ops.append(WriteFileOp(path=relative_path, content=modified_module.code))

            except Exception:
                # Log error and continue? For now, let it fail fast.
                # In a real CLI, we'd collect these errors.
                raise

        return ops