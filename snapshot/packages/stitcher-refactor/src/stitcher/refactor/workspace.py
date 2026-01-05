import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

try:
    import tomllib
except ImportError:
    import tomli as tomllib

log = logging.getLogger(__name__)


class Workspace:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # 'cascade' -> {'/path/to/cascade-application/src', '/path/to/cascade-engine/src'}
        self.import_to_source_dirs: Dict[str, Set[Path]] = defaultdict(set)
        self._discover_packages()

    def _discover_packages(self) -> None:
        for pyproject_path in self.root_path.glob("**/pyproject.toml"):
            try:
                with pyproject_path.open("rb") as f:
                    tomllib.load(f)

                pkg_root = pyproject_path.parent
                code_dirs = self._find_code_dirs(pkg_root)

                for code_dir in code_dirs:
                    import_names = self._get_top_level_importables(code_dir)
                    for import_name in import_names:
                        # The directory to add to the search path is the code_dir itself
                        self.import_to_source_dirs[import_name].add(code_dir)

            except Exception as e:
                log.warning(f"Could not process {pyproject_path}: {e}")

# A set of common directories and artifacts that are definitely not Python packages.
# Using a set for efficient O(1) lookups.
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    "build",
    "dist",
    ".egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "__pycache__",
    "site-packages",
}


class Workspace:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # 'cascade' -> {'/path/to/cascade-application/src', '/path/to/cascade-engine/src'}
        self.import_to_source_dirs: Dict[str, Set[Path]] = defaultdict(set)
        self._discover_packages()

    def _discover_packages(self) -> None:
        for pyproject_path in self.root_path.glob("**/pyproject.toml"):
            try:
                with pyproject_path.open("rb") as f:
                    tomllib.load(f)

                pkg_root = pyproject_path.parent
                code_dirs = self._find_code_dirs(pkg_root)

                for code_dir in code_dirs:
                    import_names = self._get_top_level_importables(code_dir)
                    for import_name in import_names:
                        # The directory to add to the search path is the code_dir itself
                        self.import_to_source_dirs[import_name].add(code_dir)

            except Exception as e:
                log.warning(f"Could not process {pyproject_path}: {e}")

    def _find_code_dirs(self, pkg_root: Path) -> List[Path]:
        dirs: Set[Path] = set()

        src_dir = pkg_root / "src"
        if src_dir.is_dir():
            dirs.add(src_dir)

        tests_dir = pkg_root / "tests"
        if tests_dir.is_dir():
            dirs.add(tests_dir)

        # Check for importable items directly under pkg_root to detect flat layouts
        is_flat_layout = any(
            (item.is_dir() and (item / "__init__.py").exists())
            or (item.is_file() and item.name.endswith(".py"))
            for item in pkg_root.iterdir()
            if item.name not in {".venv", "src", "tests"}
        )
        if is_flat_layout or not dirs:
            dirs.add(pkg_root)

        return list(dirs)

    def _get_top_level_importables(self, src_path: Path) -> List[str]:
        names: Set[str] = set()
        for item in src_path.iterdir():
            item_name = item.name

            # Primary filter: ignore common non-code directories and artifacts.
            # This also handles dot-prefixed directories like .git, .venv, etc.
            if item_name in EXCLUDED_DIRS or item_name.endswith(".egg-info"):
                continue

            # A top-level package is a directory. Griffe will handle namespace packages.
            if item.is_dir():
                names.add(item_name)
            # A top-level module is a .py file (but not __init__.py itself)
            elif (
                item.is_file() and item_name.endswith(".py") and item.stem != "__init__"
            ):
                names.add(item.stem)
        return list(names)

    def _find_code_dirs(self, pkg_root: Path) -> List[Path]:
        dirs: Set[Path] = set()

        src_dir = pkg_root / "src"
        if src_dir.is_dir():
            dirs.add(src_dir)

        tests_dir = pkg_root / "tests"
        if tests_dir.is_dir():
            dirs.add(tests_dir)

        # Check for importable items directly under pkg_root to detect flat layouts
        is_flat_layout = any(
            (item.is_dir() and (item / "__init__.py").exists())
            or (item.is_file() and item.name.endswith(".py"))
            for item in pkg_root.iterdir()
            if item.name not in {".venv", "src", "tests"}
        )
        if is_flat_layout or not dirs:
            dirs.add(pkg_root)

        return list(dirs)

    def get_search_paths(self) -> List[Path]:
        all_paths: Set[Path] = set()
        for paths in self.import_to_source_dirs.values():
            all_paths.update(paths)
        # Also add the root path itself to handle cases where pyproject.toml is nested
        # but top-level modules need to be found.
        all_paths.add(self.root_path)
        return sorted(list(all_paths))
