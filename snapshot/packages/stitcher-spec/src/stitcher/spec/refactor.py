from dataclasses import dataclass
from typing import Protocol, List

from .models import SourceLocation


@dataclass
class RefactorUsage:
    """Represents a specific usage of a symbol to be refactored."""
    location: SourceLocation
    # Optional text matching for verification (e.g. ensure we are replacing the right thing)
    match_text: str = ""


class RefactoringStrategyProtocol(Protocol):
    """
    Defines how a specific language handles refactoring operations.
    """

    def rename_symbol(
        self,
        source_code: str,
        usages: List[RefactorUsage],
        new_name: str
    ) -> str:
        """
        Apply a rename operation to the source code.

        Args:
            source_code: The original content of the file.
            usages: A list of locations in this file that refer to the symbol being renamed.
            new_name: The new fully qualified name (FQN) or short name.
                      The strategy is responsible for determining whether to use
                      the short name or FQN based on the context of each usage.

        Returns:
            The modified source code.
        """
        ...