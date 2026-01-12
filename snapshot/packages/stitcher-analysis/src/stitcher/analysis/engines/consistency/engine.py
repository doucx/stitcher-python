from typing import List

from stitcher.app.services import Differ
from stitcher.spec import DifferProtocol
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import FileCheckResult
from stitcher.analysis.rules.protocols import AnalysisRule
from stitcher.analysis.rules.consistency.content import ContentRule
from stitcher.analysis.rules.consistency.existence import ExistenceRule
from stitcher.analysis.rules.consistency.signature import SignatureRule
from stitcher.analysis.rules.consistency.untracked import UntrackedRule


class ConsistencyEngine:
    def __init__(self, rules: List[AnalysisRule]):
        self._rules = rules

    def analyze(self, subject: AnalysisSubject) -> FileCheckResult:
        all_violations = []
        for rule in self._rules:
            violations = rule.check(subject)
            all_violations.extend(violations)

        return FileCheckResult(path=subject.file_path, violations=all_violations)


def create_consistency_engine(
    differ: DifferProtocol | None = None,
) -> ConsistencyEngine:
    # If no differ is provided, create a default one.
    # This allows consumers to inject a mock or custom differ if needed.
    effective_differ = differ or Differ()

    default_rules = [
        SignatureRule(differ=effective_differ),
        ContentRule(differ=effective_differ),
        ExistenceRule(),
        UntrackedRule(),
    ]
    return ConsistencyEngine(rules=default_rules)
