from typing import Protocol, List, Optional, Tuple

from .index import SymbolRecord, ReferenceRecord


class IndexStoreProtocol(Protocol):
    def get_symbols_by_file_path(self, file_path: str) -> List[SymbolRecord]: ...

    def find_symbol_by_fqn(
        self, target_fqn: str
    ) -> Optional[Tuple[SymbolRecord, str]]: ...

    def find_references(self, target_fqn: str) -> List[Tuple[ReferenceRecord, str]]: ...
