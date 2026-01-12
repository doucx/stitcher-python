from dataclasses import dataclass
from typing import Optional

from stitcher.spec import DocstringIR


@dataclass
class SymbolState:
    """
    Represents the state of a symbol across three dimensions:
    1. Source Code (Current Reality)
    2. YAML Documentation (Stored Documentation)
    3. Baseline/Signature History (Last Known State)
    """

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