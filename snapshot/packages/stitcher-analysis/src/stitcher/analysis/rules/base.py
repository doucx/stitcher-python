from typing import Protocol, List
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import SymbolState, Violation


class SymbolRule(Protocol):
    id: str

    def check(self, state: SymbolState) -> List[Violation]: ...


class SubjectRule(Protocol):
    id: str

    def check(self, subject: AnalysisSubject) -> List[Violation]: ...
