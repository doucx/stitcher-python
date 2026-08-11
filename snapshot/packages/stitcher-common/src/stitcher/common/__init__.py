__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .formatting import format_docstring, parse_docstring
from stitcher.spec.persistence import DocumentAdapter
from .bus import bus

# Note: The global 'bus' is now powered by pyneedle-bus.
# It is recommended to use 'from stitcher.common.bus import bus'.

__all__ = [
    "format_docstring",
    "parse_docstring",
    "DocumentAdapter",
    "bus",
]
