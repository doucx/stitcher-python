from dataclasses import dataclass, field
from typing import Dict, Any
from needle.pointer import SemanticPointer


@dataclass
class Violation:
    """
    Represents a specific finding or issue identified by the analysis engine.
    Instead of using string keys, it uses SemanticPointers to strictly type the issue kind.
    """

    # The semantic type of the violation (e.g., L.issue.signature_drift)
    kind: SemanticPointer

    # The fully qualified name of the symbol where the violation occurred
    fqn: str

    # Contextual data required to render the message (e.g., diffs, counts)
    context: Dict[str, Any] = field(default_factory=dict)