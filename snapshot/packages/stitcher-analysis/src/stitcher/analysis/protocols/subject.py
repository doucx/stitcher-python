from typing import Protocol, Dict

from stitcher.analysis.schema import SymbolState


class AnalysisSubject(Protocol):
    """
    A protocol defining the interface for any subject (file/module)
    that can be analyzed by the consistency engine.
    """

    @property
    def file_path(self) -> str:
        """The relative path of the file being analyzed."""
        ...

    @property
    def is_tracked(self) -> bool:
        """
        Whether the file is currently tracked by Stitcher
        (i.e., has a corresponding .stitcher.yaml file).
        """
        ...

    def is_documentable(self) -> bool:
        """Whether this subject contains any documentable entities."""
        ...

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        """
        Retrieves the complete state map for all symbols in this subject,
        aggregating data from code, yaml, and history.
        """
        ...