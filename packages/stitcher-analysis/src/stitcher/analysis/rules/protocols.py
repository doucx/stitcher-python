from typing import Protocol, List

from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import Violation


class AnalysisRule(Protocol):
    def check(self, subject: AnalysisSubject) -> List[Violation]: ...
