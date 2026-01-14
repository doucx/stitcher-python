from typing import Protocol, List, Tuple, Union
from pathlib import Path
from stitcher.spec.index import SymbolRecord, ReferenceRecord, DocEntryRecord


class LanguageAdapter(Protocol):
    def parse(
        self, file_path: Path, content: str
    ) -> Union[
        Tuple[List[SymbolRecord], List[ReferenceRecord]],
        Tuple[List[SymbolRecord], List[ReferenceRecord], List[DocEntryRecord]],
    ]: ...
