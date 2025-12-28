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

    def process_interactive_session(
        self, contexts: List[InteractionContext]
    ) -> List[ResolutionAction]:
        """
        Processes a list of conflicts, returning a list of chosen actions.
        The length of the returned list MUST match the input list.
        """
        ...