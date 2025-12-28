from typing import Protocol, List
from dataclasses import dataclass, field

from stitcher.spec import ResolutionAction, ConflictType


@dataclass
class InteractionContext:
    """Data packet passed to the handler to request a user decision."""

    file_path: str
    fqn: str
    conflict_type: ConflictType
    # Future extensions:
    # signature_diff: str = ""
    # doc_diff: str = ""


class InteractionHandler(Protocol):
    """Protocol for handling user interactions during a check."""

    def ask_resolution(self, context: InteractionContext) -> ResolutionAction:
        """
        Asks the user (or a non-interactive policy) how to resolve a conflict.
        """
        ...