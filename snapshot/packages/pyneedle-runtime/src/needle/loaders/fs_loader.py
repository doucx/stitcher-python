import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union

from needle.spec import WritableResourceLoaderProtocol, SemanticPointerProtocol
from .protocols import FileHandlerProtocol, WritableFileHandlerProtocol
from .json_handler import JsonHandler


class FileSystemLoader(WritableResourceLoaderProtocol):
    def __init__(
        self,
        roots: Optional[List[Path]] = None,
        handlers: Optional[List[FileHandlerProtocol]] = None,
    ):
        self.handlers = handlers or [JsonHandler()]
        self.roots = roots or [self._find_project_root()]

    def _find_project_root(self, start_dir: Optional[Path] = None) -> Path:
        current_dir = (start_dir or Path.cwd()).resolve()
        while current_dir.parent != current_dir:
            if (current_dir / "pyproject.toml").is_file() or (
                current_dir / ".git"
            ).is_dir():
                return current_dir
            current_dir = current_dir.parent
        return start_dir or Path.cwd()

    def add_root(self, path: Path):
        if path not in self.roots:
            self.roots.insert(0, path)

    def load(self, domain: str) -> Dict[str, Any]:
        merged_registry: Dict[str, Any] = {}
        # Iterate in reverse so higher-priority roots (added later) are processed first
        for root in reversed(self.roots):
            # Path Option 1: .stitcher/needle/<domain> (project-specific overrides)
            hidden_path = root / ".stitcher" / "needle" / domain
            if hidden_path.is_dir():
                merged_registry.update(self._load_directory(hidden_path))

            # Path Option 2: needle/<domain> (packaged assets)
            asset_path = root / "needle" / domain
            if asset_path.is_dir():
                merged_registry.update(self._load_directory(asset_path))
        return merged_registry

    def _load_directory(self, root_path: Path) -> Dict[str, Any]:
        registry: Dict[str, Any] = {}
        for dirpath, _, filenames in os.walk(root_path):
            for filename in filenames:
                file_path = Path(dirpath) / filename
                for handler in self.handlers:
                    if handler.match(file_path):
                        content = handler.load(file_path)
                        registry.update(content)
                        break
        return registry

    def _get_writable_handler(
        self, path: Path
    ) -> Optional[WritableFileHandlerProtocol]:
        for handler in self.handlers:
            if isinstance(handler, WritableFileHandlerProtocol) and handler.match(path):
                return handler
        return None

    def locate(
        self, pointer: SemanticPointerProtocol, domain: str
    ) -> Union[Path, None]:
        # Locate always operates on the highest priority root.
        root = self.roots[0]
        # Per SST spec, writes/locates target the hidden .stitcher directory
        base_path = root / ".stitcher" / "needle" / domain

        parts = str(pointer).split(".")
        if len(parts) < 2:
            # Cannot determine category/namespace from pointer like 'a'
            return None

        # L.a.b.c -> category='a', namespace='b', key='c'
        category = parts[0]
        namespace = parts[1]

        # Check for category directory and namespace file
        category_dir = base_path / category
        # For now, we hardcode .json as the default write format.
        # A more advanced version could query handlers.
        namespace_file = category_dir / f"{namespace}.json"

        return namespace_file

    def put(self, pointer: SemanticPointerProtocol, value: Any, domain: str) -> bool:
        target_path = self.locate(pointer, domain)
        if not target_path:
            return False

        handler = self._get_writable_handler(target_path)
        if not handler:
            return False

        key = str(pointer)
        data = handler.load(target_path)  # Load existing data
        data[key] = value  # Update with new value

        try:
            handler.save(target_path, data)
            # SST Spec: Ensure __init__.json exists for discoverability
            init_path = target_path.parent / "__init__.json"
            if not init_path.exists():
                handler.save(init_path, {"_desc": f"Category '{target_path.parent.name}'"})

            return True
        except Exception:
            return False