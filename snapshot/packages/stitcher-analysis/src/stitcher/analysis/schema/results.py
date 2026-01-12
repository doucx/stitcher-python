from dataclasses import dataclass, field
from typing import List

from .violation import Violation


@dataclass
class FileCheckResult:
    path: str

    # All findings (errors, warnings, infos)
    violations: List[Violation] = field(default_factory=list)

    # Records of actions taken during auto-reconciliation
    # Reconciled items are also fundamentally Violations that were resolved.
    reconciled: List[Violation] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        return len(self.violations) == 0
