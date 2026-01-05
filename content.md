Excellent, we've reduced the failures from 9 to 3. The remaining errors all point to a single, subtle root cause in the new `Workspace` discovery logic.

The previous fixes correctly added the necessary `pyproject.toml` files, which solved the initial discovery problem. However, the `Workspace` class itself had two limitations that are now exposed by the more complex monorepo tests:

1.  **Incomplete Directory Discovery**: The logic for finding code directories (`_find_src_dir`) was not additive. It would find a `src/` directory but then stop, completely ignoring a co-existing `tests/` directory within the same package. This caused `AssertionError` in tests that correctly expected the `tests` directory to be in the search path.
2.  **Module vs. Package Blindness**: The logic for identifying "importables" (`_get_top_level_import_names`) only looked for package directories (those with an `__init__.py`). It failed to recognize simple top-level `.py` files (like `app.py`) as valid, importable modules. This meant Griffe was never asked to load them, leading to `ImportError` when other files tried to import them.

The fix is to make the discovery logic in `workspace.py` more comprehensive and robust.

## [WIP] fix(refactor): Enhance Workspace to find test dirs and modules

### 错误分析

剩余的三个测试失败都源于 `stitcher-refactor` 包中 `workspace.py` 的发现逻辑不够完善：

1.  **`AssertionError`**: `Workspace._find_src_dir` 方法在找到 `src` 目录后便会停止搜索，从而忽略了同一包下并存的 `tests` 目录。这导致 `graph.search_paths` 不完整，测试中断言 `tests` 目录存在的检查失败。
2.  **`ImportError`**: `Workspace._get_top_level_import_names` 方法只识别包含 `__init__.py` 的包目录，而忽略了顶层的 `.py` 模块文件（例如 `app.py`）。这导致 Griffe 无法加载这些模块，当测试代码尝试 `import app` 时，便会因模块未找到而失败。

### 用户需求

修复 `workspace.py` 中的逻辑缺陷，使所有集成测试都能通过。

### 评论

这是一个很好的例子，说明测试驱动开发的重要性。初步重构后，是更复杂的集成测试暴露了新设计的边缘情况。通过完善 `Workspace` 的发现能力，我们将使重构引擎对真实世界中多样化的项目结构更具鲁棒性。

### 目标

1.  重构 `workspace.py` 中的发现逻辑，使其能够同时识别 `src`、`tests` 目录以及平铺布局下的包根目录作为代码搜索路径。
2.  增强 `workspace.py` 的能力，使其不仅能识别包，还能识别顶层的 Python 模块文件。
3.  确保所有 `stitcher-refactor` 测试套件完全通过。

### 基本原理

我将修改 `workspace.py`。首先，将 `_find_src_dir` 重构为 `_find_code_dirs`，使其返回一个包含所有潜在代码根（`src`, `tests`, 包根目录）的列表，而不是单个路径。其次，将 `_get_top_level_import_names` 升级为 `_get_top_level_importables`，使其能够识别并返回 `.py` 文件的模块名。最后，更新主发现循环 `_discover_packages` 来使用这两个增强的辅助函数，从而构建一个完整的、准确的 `search_paths` 列表供 Griffe 使用。

### 标签

#intent/fix #flow/ready #priority/high #comp/engine #concept/parser #scope/core #ai/instruct #task/domain/testing #task/object/workspace-discovery #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: Refactor `workspace.py` for robust discovery

This patch overhauls the package discovery logic to correctly identify all source, test, and module locations.

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
~~~~~
~~~~~python.old
class Workspace:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # 'cascade' -> {'/path/to/cascade-application/src', '/path/to/cascade-engine/src'}
        self.import_to_source_dirs: Dict[str, Set[Path]] = defaultdict(set)
        self._discover_packages()

    def _discover_packages(self) -> None:
        """Scans for all pyproject.toml files to build the package map."""
        for pyproject_path in self.root_path.glob("**/pyproject.toml"):
            try:
                with pyproject_path.open("rb") as f:
                    tomllib.load(f)

                # Find the source directory (usually 'src' or package name)
                pkg_root = pyproject_path.parent
                src_dir = self._find_src_dir(pkg_root)
                if not src_dir:
                    continue

                # An import path like 'cascade' or 'stitcher'
                import_names = self._get_top_level_import_names(src_dir)
                for import_name in import_names:
                    self.import_to_source_dirs[import_name].add(src_dir)

            except Exception as e:
                log.warning(f"Could not process {pyproject_path}: {e}")

    def _find_src_dir(self, pkg_root: Path) -> Optional[Path]:
        """Finds the source directory within a package's root."""
        # Prefer 'src' directory if it exists
        src_dir = pkg_root / "src"
        if src_dir.is_dir():
            return src_dir

        # Fallback for flat layouts: check if pkg_root itself contains packages.
        is_flat_layout = any(
            item.is_dir() and (item / "__init__.py").exists()
            for item in pkg_root.iterdir()
        )
        if is_flat_layout:
            return pkg_root

        return None

    def _get_top_level_import_names(self, src_path: Path) -> List[str]:
        """Identifies top-level importable package names within a source dir."""
        names = []
        for item in src_path.iterdir():
            # A top-level package is a directory with an __init__.py
            if item.is_dir() and (item / "__init__.py").exists():
                names.append(item.name)
        return names

    def get_search_paths(self) -> List[Path]:
        """Returns all discovered source directories for Griffe."""
        all_paths: Set[Path] = set()
        for paths in self.import_to_source_dirs.values():
            all_paths.update(paths)
        return sorted(list(all_paths))
~~~~~
~~~~~python.new
class Workspace:
    def __init__(self, root_path: Path):
        self.root_path = root_path
        # 'cascade' -> {'/path/to/cascade-application/src', '/path/to/cascade-engine/src'}
        self.import_to_source_dirs: Dict[str, Set[Path]] = defaultdict(set)
        self._discover_packages()

    def _discover_packages(self) -> None:
        """Scans for all pyproject.toml files to build the package map."""
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
        """Finds potential source directories: src/, tests/, and the package root."""
        dirs: Set[Path] = set()

        src_dir = pkg_root / "src"
        if src_dir.is_dir():
            dirs.add(src_dir)

        tests_dir = pkg_root / "tests"
        if tests_dir.is_dir():
            dirs.add(tests_dir)

        # Check for importable items directly under pkg_root to detect flat layouts
        # or top-level test suites.
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
        """Identifies top-level importable names (packages and modules) within a source dir."""
        names: Set[str] = set()
        for item in src_path.iterdir():
            # A top-level package is a directory with an __init__.py
            if item.is_dir() and (item / "__init__.py").exists():
                names.add(item.name)
            # A top-level module is a .py file (but not __init__.py itself)
            elif item.is_file() and item.name.endswith(".py") and item.stem != "__init__":
                names.add(item.stem)
        return list(names)

    def get_search_paths(self) -> List[Path]:
        """Returns all discovered source directories for Griffe."""
        all_paths: Set[Path] = set()
        for paths in self.import_to_source_dirs.values():
            all_paths.update(paths)
        # Also add the root path itself to handle cases where pyproject.toml is nested
        # but top-level modules need to be found.
        all_paths.add(self.root_path)
        return sorted(list(all_paths))
~~~~~

### 下一步建议

这次的修改直接命中了问题的核心。在应用补丁后，请再次运行 `stitcher-refactor` 的测试套件。如果所有测试都通过，我将生成一个 `[COMMIT]` 计划来最终完成这次修复。
