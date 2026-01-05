You have found the next layer of the problem, and your diagnosis is spot-on. The logs are incredibly revealing.

My previous fix for PEP 420 support was a classic case of over-correction. By removing the `__init__.py` check and only excluding dunder directories, I made the discovery logic too permissive. It now incorrectly identifies build artifacts (`build`, `stitcher_python.egg-info`), VCS metadata (`.git`), and virtual environments (`.venv`) as valid Python packages. Griffe, correctly, attempts to import them, leading to the `ImportError` and the subsequent crash.

This is excellent detective work. We will now implement a more intelligent filtering mechanism.

## [WIP] fix(refactor): Refine package discovery to exclude build artifacts

### 错误分析
根本原因在于 `_get_top_level_importables` 方法的发现逻辑过于宽泛。在修复了 PEP 420 命名空间包的问题后，该方法开始将项目根目录下的几乎所有目录（如 `.git`, `.venv`, `build`, `*.egg-info`）都错误地识别为潜在的可导入包。当 `SemanticGraph` 尝试加载这些非代码目录时，其底层的 Griffe 库因无法将它们作为 Python 模块导入而崩溃。

`stitcher_python.egg-info` 目录是 Griffe 尝试加载并导致失败的第一个非代码目录，但这只是问题的表象，真正的问题是所有这些无关目录都被错误地加入了待加载列表。

### 用户需求
用户需要修复 `Workspace` 的发现逻辑，使其能够精确地识别出真正的 Python 包（包括常规包和 PEP 420 命名空间包），同时严格忽略所有已知的构建产物、VCS 目录、缓存和虚拟环境目录。

### 评论
这是一个至关重要的健壮性修复。一个强大的静态分析工具必须能够在其操作的根目录中区分代码和元数据。通过引入一个明确的排除列表，我们使 `Workspace` 的行为更加可预测和安全，防止它因项目根目录中的“噪音”而中断。

### 目标
1.  创建一个新的、更全面的测试文件，用于验证 `Workspace` 既能发现有效包（常规和 PEP 420），又能**忽略**无效的目录。
2.  修改 `packages/stitcher-refactor/src/stitcher/refactor/workspace.py` 中的 `_get_top_level_importables` 方法。
3.  引入一个包含常见非代码目录名称的排除集（`EXCLUDED_DIRS`）。
4.  在遍历目录时，使用这个排除集来过滤掉所有不应被视为包的目录。
5.  删除之前为 PEP 420 创建的、现已冗余的回归测试文件。

### 基本原理
我们将采用“黑名单”策略。在 `_get_top_level_importables` 方法中，我们会预先定义一个已知非代码目录的集合。在迭代 `src_path` 的内容时，任何名称在该集合中的目录都将被立即跳过。这样，只有可能是真实代码的目录和文件会被进一步检查，从而从源头上阻止了 Griffe 加载无效包。

### 标签
#intent/fix #flow/ready #priority/critical #comp/refactor #scope/core #ai/brainstorm #task/domain/core-abstractions #task/object/message-bus #task/action/rename #task/state/continue

---

### Script

#### Acts 1: 创建一个更全面的包发现测试
这个新测试将取代旧的 `test_pep420_discovery.py`，它同时验证正确发现和正确忽略。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/refactor/test_workspace_package_discovery.py
~~~~~
~~~~~python
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory
from pathlib import Path


def test_workspace_discovery_handles_mixed_packages_and_artifacts(tmp_path: Path):
    """
    Verifies that Workspace discovery correctly identifies various package types
    (regular, namespace) while explicitly ignoring common non-code directories
    (build artifacts, VCS, venv, etc.).
    """
    # 1. Arrange: Create a complex workspace with valid packages and junk dirs
    factory = WorkspaceFactory(tmp_path)
    project_root = (
        factory
        .with_pyproject(".")
        # A regular package with __init__.py
        .with_source("src/my_pkg_regular/__init__.py", "")
        # A PEP 420 namespace package (no __init__.py)
        .with_source("src/my_pkg_namespace/sub_pkg/__init__.py", "")
        # A regular top-level module
        .with_source("top_level_module.py", "")
        # Common junk/artifact directories that should be ignored
        .with_raw_file(".git/config", "")
        .with_raw_file(".venv/pyvenv.cfg", "")
        .with_raw_file("build/lib/some_file", "")
        .with_raw_file("dist/wheel_file.whl", "")
        .with_raw_file("my_project.egg-info/entry_points.txt", "")
        .with_raw_file(".pytest_cache/README.md", "")
        .build()
    )

    # 2. Act
    workspace = Workspace(root_path=project_root)
    discovered_packages = list(workspace.import_to_source_dirs.keys())

    # 3. Assert
    # A. Assert that all VALID packages and modules are found
    assert "my_pkg_regular" in discovered_packages
    assert "my_pkg_namespace" in discovered_packages
    assert "top_level_module" in discovered_packages

    # B. Assert that all INVALID directories are IGNORED
    assert ".git" not in discovered_packages
    assert ".venv" not in discovered_packages
    assert "build" not in discovered_packages
    assert "dist" not in discovered_packages
    assert "my_project.egg-info" not in discovered_packages
    assert ".pytest_cache" not in discovered_packages
~~~~~

#### Acts 2: 修复 `workspace.py` 以忽略非代码目录
现在，我们实现 `Workspace` 的修复逻辑。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
~~~~~
~~~~~python.old
    def _get_top_level_importables(self, src_path: Path) -> List[str]:
        names: Set[str] = set()
        for item in src_path.iterdir():
            # A top-level package is a directory. Griffe will handle namespace packages.
            # Exclude dunder directories like __pycache__
            if item.is_dir() and not (item.name.startswith("__") and item.name.endswith("__")):
                names.add(item.name)
            # A top-level module is a .py file (but not __init__.py itself)
            elif (
                item.is_file() and item.name.endswith(".py") and item.stem != "__init__"
            ):
                names.add(item.stem)
        return list(names)
~~~~~
~~~~~python.new
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
~~~~~

#### Acts 3: 清理旧的、不够全面的测试文件

~~~~~act
delete_file
packages/stitcher-refactor/tests/unit/refactor/test_pep420_discovery.py
~~~~~

### 下一步建议
我们已经用一个更健壮的实现替换了有缺陷的逻辑，并用一个更全面的测试来保护它。

1.  首先，请运行新的测试以确保我们的修复是正确的，并且没有引入新的回归：
    ```bash
    pytest packages/stitcher-refactor/tests/unit/refactor/test_workspace_package_discovery.py
    ```
2.  测试通过后，请再次运行最初的重构命令。这一次，它应该能够畅通无阻地完成任务：
    ```bash
    stitcher refactor apply 001_rename_message_bus.py --yes
    ```
