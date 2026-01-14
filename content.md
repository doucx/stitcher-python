分析得非常到位。“一种声音”是消除代码中重复逻辑、建立单一事实来源（Single Source of Truth - SSoT）的绝佳隐喻，完全符合高保真工程公理（HFEA）。

当前 `stitcher-workspace` 包中存在两个“声音”在尝试定位项目文件：
1.  **`core.py` 中的 `find_workspace_root`**: 这是最权威的声音，它通过检查 `.git` 或 `pyproject.toml` 中的 `[tool.uv.workspace]` 来寻找项目**根目录**。
2.  **`config.py` 中的 `_find_pyproject_toml`**: 这是一个次要的声音，它只负责向上寻找 `pyproject.toml` 文件，代表着一种重复的、范围更窄的搜索逻辑。

为了实现“一种声音”，我们将进行以下重构：废除 `config.py` 自己的搜索逻辑，并让它完全依赖 `core.py` 中权威的 `find_workspace_root` 函数来确定上下文。

我将生成一个计划来执行这项重构。

## [WIP] refactor(workspace): 集中化工作区根目录发现逻辑

### 用户需求

用户要求重构 `stitcher-workspace` 包，以确保发现项目根目录的逻辑是集中化的，并且源自单一的、权威的来源，即“一种声音”。

### 评论

这是一个优秀的重构建议。遵循单一事实来源（SSoT）和“不要重复自己”（DRY）原则，可以消除潜在的不一致性，使代码库更易于理解和维护。将根目录发现逻辑集中到 `core.py` 的 `find_workspace_root` 函数中，是完全正确的做法。

### 目标

1.  将 `stitcher.workspace.core.find_workspace_root` 函数确立为整个包中定位工作区根目录的**唯一**权威。
2.  重构 `stitcher.workspace.config.load_config_from_path` 函数，使其调用 `find_workspace_root` 来定位根目录，而不是执行自己的向上搜索。
3.  从 `config.py` 中彻底删除冗余的 `_find_pyproject_toml` 辅助函数。
4.  在 `stitcher.workspace` 包的 `__init__.py` 中导出 `find_workspace_root`，使其成为明确的公共API。

### 基本原理

重构的核心思想是改变 `config.py` 的职责。它不应该“寻找”配置文件，而应该在被告知工作区根目录后，“加载”位于该根目录下的配置文件。

具体流程如下：
1.  `load_config_from_path` 将首先调用 `core.find_workspace_root(search_path)` 来获取权威的工作区根目录。
2.  一旦获得 `workspace_root`，它将直接在该路径下查找 `pyproject.toml` (`workspace_root / "pyproject.toml"`)。
3.  这种方式消除了 `config.py` 中重复的向上遍历逻辑，使得 `_find_pyproject_toml` 函数变得多余，可以安全地删除。
4.  最后，将 `find_workspace_root` 提升为包的公共接口，明确其核心地位。

### 标签

#intent/refine #flow/ready #priority/high #comp/workspace #concept/config #scope/core #ai/instruct #task/domain/architecture #task/object/workspace-discovery #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 `config.py` 以使用权威的根目录发现函数

我们将修改 `load_config_from_path` 函数，移除对 `_find_pyproject_toml` 的调用，转而使用从 `core.py` 导入的 `find_workspace_root`。同时，我们将删除不再需要的 `_find_pyproject_toml` 函数。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/config.py
~~~~~
~~~~~python.old
def _find_pyproject_toml(search_path: Path) -> Path:
    current_dir = search_path.resolve()
    while current_dir.parent != current_dir:
        pyproject_path = current_dir / "pyproject.toml"
        if pyproject_path.is_file():
            return pyproject_path
        current_dir = current_dir.parent
    raise FileNotFoundError("Could not find pyproject.toml in any parent directory.")


def _find_plugins(workspace_root: Path) -> Dict[str, str]:
~~~~~
~~~~~python.new
from .core import find_workspace_root
from .exceptions import WorkspaceNotFoundError


def _find_plugins(workspace_root: Path) -> Dict[str, str]:
~~~~~

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/config.py
~~~~~
~~~~~python.old
def load_config_from_path(
    search_path: Path,
) -> Tuple[List[StitcherConfig], Optional[str]]:
    plugins = _find_plugins(search_path)
    project_name: Optional[str] = None
    stitcher_data: Dict[str, Any] = {}

    try:
        config_path = _find_pyproject_toml(search_path)
        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        project_name = data.get("project", {}).get("name")
        stitcher_data = data.get("tool", {}).get("stitcher", {})

    except FileNotFoundError:
        # If no root config file, return default config with discovered plugins
        return [StitcherConfig(plugins=plugins)], None

    configs: List[StitcherConfig] = []
~~~~~
~~~~~python.new
def load_config_from_path(
    search_path: Path,
) -> Tuple[List[StitcherConfig], Optional[str]]:
    project_name: Optional[str] = None
    stitcher_data: Dict[str, Any] = {}

    try:
        workspace_root = find_workspace_root(search_path)
        plugins = _find_plugins(workspace_root)
        config_path = workspace_root / "pyproject.toml"

        if config_path.exists():
            with open(config_path, "rb") as f:
                data = tomllib.load(f)

            project_name = data.get("project", {}).get("name")
            stitcher_data = data.get("tool", {}).get("stitcher", {})
        else:
            # Workspace root found (e.g. by .git), but no pyproject.toml
            return [StitcherConfig(plugins=plugins)], None

    except WorkspaceNotFoundError:
        # No workspace found at all, so no config and no plugins.
        return [StitcherConfig()], None

    configs: List[StitcherConfig] = []
~~~~~

#### Acts 2: 将 `find_workspace_root` 导出为包的公共 API

现在，我们将修改 `__init__.py` 文件，将 `find_workspace_root` 函数添加到 `__all__` 中，使其成为包的正式接口。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/__init__.py
~~~~~
~~~~~python.old
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import Optional, List
from .core import Workspace
from .config import StitcherConfig, load_config_from_path
from .exceptions import WorkspaceError, WorkspaceNotFoundError

__all__ = [
    "Workspace",
    "WorkspaceError",
    "WorkspaceNotFoundError",
    "StitcherConfig",
    "load_config_from_path",
    "Optional",
    "List",
]
~~~~~
~~~~~python.new
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import Optional, List
from .core import Workspace, find_workspace_root
from .config import StitcherConfig, load_config_from_path
from .exceptions import WorkspaceError, WorkspaceNotFoundError

__all__ = [
    "Workspace",
    "WorkspaceError",
    "WorkspaceNotFoundError",
    "StitcherConfig",
    "load_config_from_path",
    "find_workspace_root",
    "Optional",
    "List",
]
~~~~~

### 下一步建议

我们已经成功地将根目录发现逻辑集中化。下一步是验证这一重构的正确性。

我建议检查并更新 `stitcher-workspace` 相关的测试用例，特别是那些依赖于配置加载的测试，以确保它们在新的逻辑下仍然能够正确运行。例如，测试场景应覆盖：
1.  通过 `.git` 找到根目录，但 `pyproject.toml` 不存在。
2.  通过 `pyproject.toml` 中的 `[tool.uv.workspace]` 找到根目录。
3.  在子目录中运行命令时，仍能正确找到根配置。
4.  在没有工作区的目录中运行时的失败情况。

如果你同意，我将开始准备更新测试的计划。
