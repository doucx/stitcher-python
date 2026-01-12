from dataclasses import dataclass
from typing import List

from needle.pointer import L
from stitcher.analysis.protocols import AnalysisSubject
from stitcher.analysis.schema import Violation
from stitcher.analysis.rules.protocols import AnalysisRule


@dataclass
class UntrackedRule(AnalysisRule):
    def check(self, subject: AnalysisSubject) -> List[Violation]:
        # 1. If explicitly tracked, this rule does not apply.
        if subject.is_tracked:
            return []

        # 2. If not tracked, but has nothing to document, we don't care.
        if not subject.is_documentable():
            return []

        # 3. It is untracked and documentable.
        # We now identify which specific public symbols are missing documentation.
        states = subject.get_all_symbol_states()
        undocumented_keys = [
            s.fqn
            for s in states.values()
            if s.is_public
            and s.fqn != "__doc__"
            and not s.source_doc_content
        ]

        # Mimic legacy behavior:
        # If there are specific symbols needing docs, give a detailed warning.
        # Otherwise (e.g. only __doc__ or all have docs but just no YAML), generic warning.
        if undocumented_keys:
            return [
                Violation(
                    kind=L.check.file.untracked_with_details,
                    fqn=subject.file_path,
                    context={"count": len(undocumented_keys), "keys": undocumented_keys}
                )
            ]
        else:
            return [
                Violation(
                    kind=L.check.file.untracked,
                    fqn=subject.file_path
                )
            ]