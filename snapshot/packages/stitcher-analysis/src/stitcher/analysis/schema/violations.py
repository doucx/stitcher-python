from dataclasses import dataclass
from enum import Enum


class ViolationLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Violation:
    fqn: str
    rule_id: str
    level: ViolationLevel
    category: str
    message: str
