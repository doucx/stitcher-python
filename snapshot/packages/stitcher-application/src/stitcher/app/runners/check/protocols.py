from typing import Protocol, Dict, Optional
from dataclasses import dataclass
from stitcher.spec import DocstringIR


from typing import Protocol, Dict, Optional
from dataclasses import dataclass
from stitcher.spec import DocstringIR


@dataclass
class SymbolState:
    """A complete snapshot of a symbol's state from all sources."""

    fqn: str
    is_public: bool

    # --- Source Code State (Current) ---
    exists_in_code: bool
    source_doc_content: Optional[str]
    signature_hash: Optional[str]
    signature_text: Optional[str]

    # --- YAML Documentation State (Current) ---
    exists_in_yaml: bool
    yaml_doc_ir: Optional[DocstringIR]
    yaml_content_hash: Optional[str]
    
    # --- Baseline State (Stored) ---
    baseline_signature_hash: Optional[str]
    baseline_signature_text: Optional[str]
    baseline_yaml_content_hash: Optional[str]


class CheckSubject(Protocol):
    """The contract for what the CheckAnalyzer can inspect."""

    @property
    def file_path(self) -> str:
        ...
        
    def is_documentable(self) -> bool:
        """Checks if the subject as a whole is worth tracking."""
        ...

    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        """
        Gets the aggregated state of all symbols relevant to this subject.
        This includes symbols defined in code and/or documented in YAML.
        """
        ...