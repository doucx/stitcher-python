好的，我们开始实施路线图的第一步：实现 `Workspace` 类并为其建立健壮的单元测试。这需要我们首先增强 `WorkspaceFactory` 以支持在 monorepo 结构中声明多个 `pyproject.toml` 文件。

这是一个计划，它将创建 `Workspace` 类、更新测试工厂并添加相应的单元测试。

## [WIP] feat: 实现 Workspace 类以支持 Monorepo 包发现

### 用户需求

根据重构路线图，实施第一阶段的任务 1.1：
1.  创建一个新的 `Workspace` 类，它能够通过扫描项目中的 `pyproject.toml` 文件来发现所有 Python 包，包括复杂的命名空间包。
2.  更新测试工具 `WorkspaceFactory`，使其能够声明式地构建包含多个 `pyproject.toml` 的 monorepo 结构，以便进行测试。
3.  为 `Workspace` 类编写全面的单元测试，覆盖 `src` 布局、扁平布局和命名空间包三种核心场景。

### 评论

这是整个重构工作的基石。通过创建一个由 `pyproject.toml` 元数据驱动的 `Workspace` 抽象，我们能从根本上摆脱当前对文件系统布局的脆弱假设。这将使重构引擎变得更加健壮，并能够正确处理真实世界中的复杂项目结构，是后续所有重构工作得以正确执行的先决条件。

### 目标

1.  **更新 `WorkspaceFactory`**: 在 `stitcher-test-utils` 中为 `WorkspaceFactory` 添加一个新的 `with_pyproject` 方法，使其能够在一个虚拟工作区内的任意子目录中创建 `pyproject.toml` 文件。
2.  **实现 `Workspace` 类**: 创建 `packages/stitcher-refactor/src/stitcher/refactor/workspace.py` 文件，并实现 `Workspace` 类。该类将负责扫描、解析并构建一个从“导入名”到“源文件目录”的权威映射。
3.  **编写单元测试**: 创建 `packages/stitcher-refactor/tests/unit/refactor/test_workspace.py` 文件，并利用更新后的 `WorkspaceFactory` 编写三个核心测试用例，以验证 `Workspace` 在不同项目布局下的行为是否正确。

### 基本原理

我们将采用一种元数据驱动的方法。`Workspace` 类将成为项目结构的“单一事实来源”。它通过 `glob` 查找所有的 `pyproject.toml` 文件，并使用 `tomllib` 进行解析。通过一系列辅助方法，它能智能地定位每个包的源代码目录（无论是 `src/` 还是扁平布局），并从中推断出顶级的可导入包名。对于命名空间包，它会将多个物理源目录正确地关联到同一个导入名下。

为了测试这一核心功能，我们必须首先增强 `WorkspaceFactory`。新的 `with_pyproject` 方法将允许测试用例精确地模拟一个 monorepo，其中每个子项目都有自己的 `pyproject.toml`。这将使我们的单元测试能够完全在内存中声明性地构建出复杂的项目结构，从而对 `Workspace` 的发现逻辑进行精确且隔离的验证。

### 标签

#intent/build #flow/ready #priority/high #comp/refactor #comp/test-utils #concept/config #scope/core #ai/instruct #task/domain/refactor-engine #task/object/workspace-discovery #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 增强测试工具 `WorkspaceFactory`

首先，我们为 `WorkspaceFactory` 添加 `with_pyproject` 方法，并调整 `build` 方法以支持在没有全局项目配置的情况下构建工作区。这将使我们能够为后续的 `Workspace` 测试创建复杂的 monorepo 布局。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
~~~~~
~~~~~python.old
    def with_entry_points(
        self, group: str, entry_points: Dict[str, str]
    ) -> "WorkspaceFactory":
        project = self._pyproject_data.setdefault("project", {})
        eps = project.setdefault("entry-points", {})
        eps[group] = entry_points
        return self

    def with_source(self, path: str, content: str) -> "WorkspaceFactory":
        self._files_to_create.append(
            {"path": path, "content": dedent(content), "format": "raw"}
        )
        return self
~~~~~
~~~~~python.new
    def with_entry_points(
        self, group: str, entry_points: Dict[str, str]
    ) -> "WorkspaceFactory":
        project = self._pyproject_data.setdefault("project", {})
        eps = project.setdefault("entry-points", {})
        eps[group] = entry_points
        return self

    def with_pyproject(self, path_prefix: str) -> "WorkspaceFactory":
        """Creates a minimal pyproject.toml in a subdirectory."""
        pkg_name = Path(path_prefix).name
        pyproject_content = {"project": {"name": pkg_name, "version": "0.1.0"}}
        self._files_to_create.append(
            {
                "path": str(Path(path_prefix) / "pyproject.toml"),
                "content": pyproject_content,
                "format": "toml",
            }
        )
        return self

    def with_source(self, path: str, content: str) -> "WorkspaceFactory":
        self._files_to_create.append(
            {"path": path, "content": dedent(content), "format": "raw"}
        )
        return self
~~~~~

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/workspace.py
~~~~~
~~~~~python.old
    def build(self) -> Path:
        # 1. Finalize pyproject.toml if data was added
        if self._pyproject_data:
            self._files_to_create.append(
                {
                    "path": "pyproject.toml",
                    "content": self._pyproject_data,
                    "format": "toml",
                }
            )

        # 2. Write all files
        for file_spec in self._files_to_create:
~~~~~
~~~~~python.new
    def build(self) -> Path:
        # 1. Finalize pyproject.toml if data was added for the root project
        if self._pyproject_data:
            # Check if a root pyproject.toml is already manually specified to avoid overwriting
            if not any(f["path"] == "pyproject.toml" for f in self._files_to_create):
                self._files_to_create.append(
                    {
                        "path": "pyproject.toml",
                        "content": self._pyproject_data,
                        "format": "toml",
                    }
                )

        # 2. Write all files
        for file_spec in self._files_to_create:
~~~~~

#### Acts 2: 实现 `Workspace` 类

现在，我们创建 `Workspace` 类的实现文件。它包含了发现和解析包的核心逻辑。

~~~~~act
write_file
packages/stitcher-refactor/src/stitcher/refactor/workspace.py
~~~~~
~~~~~python
import logging
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional

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

        # Fallback for flat layouts: find the first dir containing __init__.py
        for item in pkg_root.iterdir():
            if item.is_dir() and (item / "__init__.py").exists():
                return item

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

#### Acts 3: 为 `Workspace` 添加单元测试

最后，我们创建单元测试文件，以确保 `Workspace` 在各种场景下都能正确工作。

~~~~~act
write_file
packages/stitcher-refactor/tests/unit/refactor/test_workspace.py
~~~~~
~~~~~python
from stitcher.refactor.workspace import Workspace
from stitcher.test_utils import WorkspaceFactory


def test_workspace_standard_src_layout(tmp_path):
    # ARRANGE
    factory = WorkspaceFactory(tmp_path).with_pyproject("pkg_a").with_source(
        "pkg_a/src/pkga_lib/__init__.py", ""
    )
    project_root = factory.build()
    pkg_a_src = project_root / "pkg_a" / "src"

    # ACT
    workspace = Workspace(project_root)

    # ASSERT
    assert workspace.import_to_source_dirs["pkga_lib"] == {pkg_a_src}
    assert workspace.get_search_paths() == [pkg_a_src]


def test_workspace_flat_layout(tmp_path):
    # ARRANGE
    factory = WorkspaceFactory(tmp_path).with_pyproject("pkg_b").with_source(
        "pkg_b/pkgb_lib/__init__.py", ""
    )
    project_root = factory.build()
    pkg_b_lib_dir = project_root / "pkg_b" / "pkgb_lib"

    # ACT
    workspace = Workspace(project_root)

    # ASSERT
    # For flat layout, the source dir is the package dir itself
    assert workspace.import_to_source_dirs["pkgb_lib"] == {pkg_b_lib_dir}
    assert workspace.get_search_paths() == [pkg_b_lib_dir]


def test_workspace_namespace_package(tmp_path):
    # ARRANGE: Simulate two distributions contributing to the 'cascade' namespace
    factory = (
        WorkspaceFactory(tmp_path)
        .with_pyproject("cascade-engine")
        .with_source("cascade-engine/src/cascade/__init__.py", "")
        .with_pyproject("cascade-app")
        .with_source("cascade-app/src/cascade/__init__.py", "")
    )
    project_root = factory.build()
    engine_src = project_root / "cascade-engine" / "src"
    app_src = project_root / "cascade-app" / "src"

    # ACT
    workspace = Workspace(project_root)

    # ASSERT
    assert workspace.import_to_source_dirs["cascade"] == {engine_src, app_src}
    assert sorted(workspace.get_search_paths()) == sorted([engine_src, app_src])
~~~~~

### 下一步建议

我们已经成功完成了路线图的第一步，奠定了坚实的基础。

下一步，我们将进入路线图的**阶段二**，将新创建的 `Workspace` 组件集成到现有的 `SemanticGraph` 和 `RefactorContext` 中，并开始替换掉旧的、硬编码的路径发现逻辑。如果你同意，我将为此生成下一个计划。
