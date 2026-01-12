from dataclasses import dataclass, field
from typing import List

from .violation import Violation


@dataclass
class FileCheckResult:
    """
    Aggregates all analysis results for a single file.
    Uses a flat list of Violations instead of categorizing by severity/type,
    delegating interpretation to the consumer/reporter.
    """

    path: str
    
    # All findings (errors, warnings, infos)
    violations: List[Violation] = field(default_factory=list)
    
    # Records of actions taken during auto-reconciliation
    # Reconciled items are also fundamentally Violations that were resolved.
    reconciled: List[Violation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """
        A file is clean if there are no active violations.
        Reconciled items do not count against cleanliness as they are resolved.
        """
        return len(self.violations) == 0