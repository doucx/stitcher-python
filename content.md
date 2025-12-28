Of course. Your analysis is spot on. The `TypeError` reveals a critical flaw in the composition logic. My previous change correctly simplified `FileSystemLoader` but broke its downstream consumers by not adapting them to the new, more explicit architecture.

Your proposal to make `stitcher-common` the "composition root" is the correct path forward. It perfectly aligns with the principle of separating a generic library (`pyneedle`) from a specific application (`stitcher`). The library provides the tools (`FileSystemLoader`, `OverlayNexus`, root-finding utilities), and the application uses them to assemble its specific, layered configuration.

I will generate a plan to implement this superior architecture.

## [WIP] fix(common): Adapt stitcher-common to new composable loader architecture

### 错误分析
`test_assembly.py` fails during test collection because `stitcher.common.__init__` attempts to instantiate `FileSystemLoader()` without the now-mandatory `root` argument. This is a direct consequence of the previous refactoring, which correctly simplified `FileSystemLoader` but left `stitcher-common` in an inconsistent state. The error highlights an architectural issue: `stitcher-common` was implicitly relying on `FileSystemLoader` to discover paths, a responsibility that has now been correctly removed from the loader.

### 用户需求
1.  **Decouple `pyneedle` Defaults**: The default `nexus` instance provided by `pyneedle-runtime` must be completely generic and root-agnostic. It should not perform any filesystem discovery on its own.
2.  **Move Root Finding Utility**: The `_find_project_root` function should live in `pyneedle-runtime` as a reusable utility, but not be called by its default `nexus`.
3.  **Establish `stitcher-common` as Composition Root**: The `stitcher.common` package must take on the responsibility of building the application-specific, layered `nexus`. It should:
    a. Use the utility from `pyneedle-runtime` to find the project's root.
    b. Locate its own internal assets directory.
    c. Create two distinct `FileSystemLoader` instances for these two roots.
    d. Combine them in the correct priority order using `OverlayNexus` to create the global `stitcher_nexus`.

### 评论
This is a critical and correct architectural refinement. It enforces a clean separation of concerns:
-   `pyneedle` remains a pure, side-effect-free infrastructure library.
-   `stitcher-common` becomes the explicit "main" entry point for the application's service configuration, composing the generic tools from `pyneedle` into an application-aware whole.
This change makes the system's behavior much more predictable and resolves the dependency violation.

### 目标
1.  Make the `FileSystemLoader` constructor more robust by allowing an optional `root`.
2.  Ensure the default `nexus` in `pyneedle-runtime` is initialized as an empty, inert instance.
3.  Rewrite `stitcher.common.__init__.py` to correctly assemble the `stitcher_nexus` using a high-priority project loader and a low-priority common assets loader.

### 基本原理
We are moving from an implicit, "magical" configuration to an explicit composition model. The generic library (`pyneedle`) provides the building blocks. The application (`stitcher-common`) is now responsible for assembling those blocks in a way that reflects the application's specific needs (i.e., layering project-specific resources over built-in package assets).

### 标签
#intent/fix #intent/refine #flow/ready #priority/high #comp/runtime #comp/cli #concept/config #scope/core #dx #task/domain/storage #task/object/loader-architecture #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: Make `FileSystemLoader` robust to empty initialization
We will make the `root` argument optional. If no root is provided, the loader will simply be empty, which is a safe and predictable default.

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python.old
    def __init__(
        self,
        root: Path,
        handlers: Optional[List[FileHandlerProtocol]] = None,
        default_domain: str = "en",
    ):
        super().__init__(default_domain)
        self.handlers = handlers or [JsonHandler()]
        self.root = root
        
        # Cache structure: domain -> flattened_dict
        self._data_cache: Dict[str, Dict[str, str]] = {}

    def _ensure_loaded(self, domain: str) -> Dict[str, str]:
        if domain not in self._data_cache:
            self._data_cache[domain] = self._scan_root(domain)
        return self._data_cache[domain]
~~~~~
~~~~~python.new
    def __init__(
        self,
        root: Optional[Path] = None,
        handlers: Optional[List[FileHandlerProtocol]] = None,
        default_domain: str = "en",
    ):
        super().__init__(default_domain)
        self.handlers = handlers or [JsonHandler()]
        self.root = root
        
        # Cache structure: domain -> flattened_dict
        self._data_cache: Dict[str, Dict[str, str]] = {}

    def _ensure_loaded(self, domain: str) -> Dict[str, str]:
        if domain not in self._data_cache:
            if not self.root:
                self._data_cache[domain] = {}
            else:
                self._data_cache[domain] = self._scan_root(domain)
        return self._data_cache[domain]
~~~~~

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/loaders/fs_loader.py
~~~~~
~~~~~python.old
    def locate(self, pointer: Union[str, Any], domain: str) -> Path:
        """For a single-root loader, locate is deterministic."""
        key = str(pointer)
        base_dir = self.root / ".stitcher" / "needle" / domain
        
        parts = key.split(".")
        filename = f"{parts[0]}.json"  # Default to JSON
        return base_dir / filename
~~~~~
~~~~~python.new
    def locate(self, pointer: Union[str, Any], domain: str) -> Path:
        """For a single-root loader, locate is deterministic."""
        if not self.root:
            raise RuntimeError("Cannot locate path on a loader with no root.")

        key = str(pointer)
        base_dir = self.root / ".stitcher" / "needle" / domain
        
        parts = key.split(".")
        filename = f"{parts[0]}.json"  # Default to JSON
        return base_dir / filename
~~~~~

#### Acts 2: Decouple `pyneedle-runtime`'s default `nexus`
The global `nexus` in `pyneedle` will now be an empty shell, safe to import anywhere without filesystem side-effects. The `_find_project_root` utility remains for others to use.

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/runtime.py
~~~~~
~~~~~python.old
# --- Global Singleton Instance ---
# This is the "batteries-included" setup.
# It automatically discovers the project root and sets up a file system loader.
_project_root = _find_project_root()
_default_loader = FileSystemLoader(root=_project_root)
nexus = OverlayNexus(loaders=[_default_loader])
# ---------------------------------

# Make the loader accessible for advanced use cases (e.g., adding asset paths)
# Example: from needle import _default_loader
#          _default_loader.add_root(my_assets_path)
#          nexus.reload()

__all__ = ["L", "nexus", "SemanticPointer", "PointerSet", "_default_loader"]
~~~~~
~~~~~python.new
# --- Global Singleton Instance ---
# This is a generic, side-effect-free instance.
# Applications should compose their own nexus with specific loaders.
nexus = OverlayNexus(loaders=[])
# ---------------------------------


__all__ = ["L", "nexus", "SemanticPointer", "PointerSet", "_find_project_root"]
~~~~~

#### Acts 3: Rebuild `stitcher-common` as the Composition Root
This is the core of the fix. `stitcher.common` now explicitly builds its layered `nexus`.

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path
from needle.nexus import OverlayNexus
from needle.loaders import FileSystemLoader
from needle.runtime import _find_project_root
from .formatting import format_docstring, parse_docstring
from .messaging.bus import MessageBus

# --- Composition Root for Stitcher's Core Services ---

# 1. Discover necessary roots
#    - The current project's root (for user overrides)
#    - The `stitcher-common` package's own assets root (for defaults)
_project_root = _find_project_root()
_common_assets_root = Path(__file__).parent / "assets"

# 2. Create a loader for each root.
#    The project loader will be writable and has higher priority.
project_loader = FileSystemLoader(root=_project_root)
common_assets_loader = FileSystemLoader(root=_common_assets_root)

# 3. Create the nexus instance, composing loaders in the correct priority order.
#    `project_loader` comes first, so it overrides `common_assets_loader`.
stitcher_nexus = OverlayNexus(loaders=[project_loader, common_assets_loader])

# 4. Create the bus instance, injecting the application-specific nexus.
bus = MessageBus(nexus_instance=stitcher_nexus)

# Public API for stitcher packages.
# `stitcher_loader` is aliased to `project_loader` to maintain the contract
# for write operations, ensuring they go to the user's project directory.
stitcher_loader = project_loader

__all__ = [
    "bus",
    "stitcher_nexus",
    "stitcher_loader",
    "format_docstring",
    "parse_docstring",
]
~~~~~

### 下一步建议
The core architectural issue is now resolved. The system is more robust and easier to reason about. The next logical step is to run the entire test suite across all packages to ensure that this change has not introduced any regressions in other areas that might have been implicitly relying on the old behavior.
