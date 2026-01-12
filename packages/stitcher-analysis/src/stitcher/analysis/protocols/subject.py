from typing import Protocol, Dict

from stitcher.analysis.schema import SymbolState


class AnalysisSubject(Protocol):
    @property
    def file_path(self) -> str: ...

    @property
    def is_tracked(self) -> bool: ...

    def is_documentable(self) -> bool: ...

    def get_all_symbol_states(self) -> Dict[str, SymbolState]: ...
