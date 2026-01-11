from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRecord:
    id: int
    path: str
    content_hash: str
    last_mtime: float
    last_size: int
    indexing_status: int


@dataclass
class SymbolRecord:
    id: str  # SURI
    name: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

    # Populated during Scan phase
    alias_target_fqn: Optional[str] = None
    
    # Populated during Link phase
    alias_target_id: Optional[str] = None
    canonical_fqn: Optional[str] = None
    
    file_id: Optional[int] = None
    logical_path: Optional[str] = None
    signature_hash: Optional[str] = None


@dataclass
class ReferenceRecord:
    target_fqn: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

    # Populated during Link phase
    target_id: Optional[str] = None
    
    # Context
    source_file_id: Optional[int] = None
    id: Optional[int] = None  # Database Row ID