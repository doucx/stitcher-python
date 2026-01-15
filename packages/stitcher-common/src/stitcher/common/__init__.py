__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .formatting import format_docstring, parse_docstring
from stitcher.spec.persistence import DocumentAdapter

# Note: The global 'bus' has been moved to stitcher.bus.
# Please use 'from stitcher.bus import bus' instead.

__all__ = [
    "format_docstring",
    "parse_docstring",
    "DocumentAdapter",
]
