__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .core import SemanticPointer
from .set import PointerSet

# The Global Root Pointer
L = SemanticPointer()

__all__ = ["L", "SemanticPointer", "PointerSet"]
