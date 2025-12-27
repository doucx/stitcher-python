__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path
from needle.nexus import OverlayNexus
from needle.loaders.fs_loader import FileSystemLoader
from .messaging.bus import bus

# --- Composition Root for Stitcher's Nexus ---
# We create and configure our own instances instead of using pyneedle's global singletons.
# This decouples us and follows Inversion of Control principles.

# 1. Create the loader instance.
stitcher_loader = FileSystemLoader()

# 2. Create the nexus instance, injecting the loader.
stitcher_nexus = OverlayNexus(loaders=[stitcher_loader])

# 3. Auto-register built-in assets for the 'common' package.
try:
    _assets_path = Path(__file__).parent / "assets"
    if _assets_path.is_dir():
        stitcher_loader.add_root(_assets_path)
except NameError:
    pass
# ---------------------------------------------


# Public API for stitcher packages
__all__ = ["bus", "stitcher_nexus", "stitcher_loader"]