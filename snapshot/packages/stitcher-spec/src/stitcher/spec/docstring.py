from dataclasses import dataclass, field
from typing import List, Optional, Union, Dict, Any


@dataclass
class DocstringItem:
    """Represents a single item within a docstring section, like a parameter or a return value."""

    name: Optional[str] = None  # e.g., the parameter name
    annotation: Optional[str] = None  # e.g., the type annotation string
    description: str = ""  # The description text
    default: Optional[str] = None  # The default value as a string representation


class SectionKind(str, Enum):
    TEXT = "text"
    PARAMETERS = "parameters"
    RETURNS = "returns"
    RAISES = "raises"
    YIELDS = "yields"
    ATTRIBUTES = "attributes"
    EXAMPLES = "examples"
    NOTES = "notes"
    WARNING = "warning"
    SEE_ALSO = "see_also"
    ADMONITION = "admonition"


@dataclass
class DocstringSection:
    """Represents a section of a docstring, like 'Args' or 'Returns'."""

    kind: str  # Should use SectionKind values
    title: Optional[str] = None  # The rendered title, e.g., "Parameters"
    content: Union[str, List["DocstringItem"]] = ""


@dataclass
class DocstringIR:
    """The Intermediate Representation of a docstring."""

    summary: Optional[str] = None
    extended: Optional[str] = None
    sections: List[DocstringSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(
        default_factory=dict
    )  # For "See Also", "Notes"
    addons: Dict[str, Any] = field(default_factory=dict)  # For "Addon.*" data