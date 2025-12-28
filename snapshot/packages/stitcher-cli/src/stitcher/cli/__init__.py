__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path

from needle.loaders import FileSystemLoader
from stitcher.common import stitcher_nexus
from .main import app

# --- Composition Root for Stitcher CLI Assets ---
# This is where the CLI layer registers its own resources into the shared nexus.

# Auto-register built-in assets for the 'cli' package using the new architecture.
try:
    _cli_assets_root = Path(__file__).parent / "assets"
    if _cli_assets_root.is_dir():
        # 1. Create a dedicated loader for the CLI's assets.
        cli_loader = FileSystemLoader(root=_cli_assets_root)
        # 2. Add it to the nexus loader stack with the highest priority.
        #    This ensures CLI-specific strings override common ones.
        stitcher_nexus.loaders.insert(0, cli_loader)
except NameError:
    # This might happen in some testing or packaging scenarios.
    pass

__all__ = ["app"]