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
        old_name: str,
        new_name: str,
    ) -> str:
        """
        Apply a rename operation to the source code.

        Args:
            source_code: The original content of the file.
            usages: A list of locations in this file that refer to the symbol being renamed.
            old_name: The original fully qualified name (FQN) of the symbol.
                      Useful for verification and context awareness (e.g. short name extraction).
            new_name: The new fully qualified name (FQN). The strategy logic
                      should determine if a short name or full name is appropriate
                      for each insertion point.

        Returns:
            The modified source code.
        """
        ...