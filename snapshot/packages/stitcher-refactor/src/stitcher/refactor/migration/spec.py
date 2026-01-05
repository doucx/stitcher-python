from typing import List, Dict, TypeAlias

from stitcher.refactor.operations.base import AbstractOperation
from stitcher.refactor.operations.rename_symbol import RenameSymbolOperation
from stitcher.refactor.operations.move_file import MoveFileOperation
from stitcher.refactor.operations.move_directory import MoveDirectoryOperation

# --- Aliases for better DX in migration scripts ---
Rename: TypeAlias = RenameSymbolOperation
Move: TypeAlias = MoveFileOperation
MoveDir: TypeAlias = MoveDirectoryOperation


class MigrationSpec:
    """
    A container for defining a set of refactoring operations.
    This serves as the API for Stitcher Migration Packs (SMP).
    """

    def __init__(self):
        self._operations: List[AbstractOperation] = []

    def add(self, operation: AbstractOperation) -> "MigrationSpec":
        """
        Register a single atomic operation.
        """
        self._operations.append(operation)
        return self

    def add_map(self, rename_map: Dict[str, str]) -> "MigrationSpec":
        """
        Syntactic sugar for adding multiple RenameSymbolOperation items.

        Args:
            rename_map: A dictionary mapping old FQNs to new FQNs.
        """
        for old_fqn, new_fqn in rename_map.items():
            self.add(RenameSymbolOperation(old_fqn, new_fqn))
        return self

    @property
    def operations(self) -> List[AbstractOperation]:
        """
        Returns the list of collected operations.
        """
        return self._operations
