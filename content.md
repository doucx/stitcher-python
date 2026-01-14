好的，我们立即实施解决循环依赖的战略方案。

此计划将通过创建专用的 `discovery.py` 模块来解耦底层工具和高层逻辑，从而恢复架构的健康状态。

## [WIP] fix: Resolve circular import by creating a discovery module

### 错误分析

在 `stitcher-workspace` 包内，`core.py`（包含 `Workspace` 类）和 `config.py`（包含 `StitcherConfig` 模型）之间存在致命的循环导入。`core.py` 导入 `config.py` 以获取配置模型，而 `config.py` 又导入 `core.py` 以获取 `find_workspace_root` 工具函数。

### 用户需求

通过创建一个新的、独立的 `discovery.py` 模块来打破此循环依赖，该模块将专门承载 `find_workspace_root` 函数。

### 评论

这是一个典型的架构“正规化”操作。根据“正规军工程标准”，意图（业务逻辑）、计划（配置模型）和执行（底层工具）必须在代码结构上实现物理隔离。`find_workspace_root` 是一个纯粹的底层工具，将它从高层业务逻辑模块 `core.py` 中分离出来，是纠正架构分层错误的正确举措。

### 目标

1.  创建 `packages/stitcher-workspace/src/stitcher/workspace/discovery.py` 文件。
2.  将 `find_workspace_root` 函数及其依赖项从 `core.py` 移动到 `discovery.py`。
3.  更新所有引用 `find_workspace_root` 的地方，使其从新的 `discovery.py` 模块导入。
4.  确保 `core.py` 和 `config.py` 之间不再有循环依赖。

### 基本原理

我们将分步执行此重构：
1.  首先创建新的 `discovery.py` 文件，并填充 `find_workspace_root` 函数的完整内容。
2.  然后，通过 `patch` 操作从 `core.py` 中删除该函数。
3.  最后，通过一系列精确的 `patch` 操作，修复 `config.py` 和相关测试文件中的 `import` 语句，完成解耦。
这种方法确保了操作的原子性和可追溯性。

### 标签

#intent/fix #flow/ready #priority/critical #comp/workspace #scope/core #scope/dx #ai/brainstorm #task/domain/architecture #task/object/package-merge #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 创建 `discovery.py` 并迁移函数

我们首先创建新的 `discovery.py` 模块，并将 `find_workspace_root` 函数完整地迁移进去。

~~~~~act
write_file
packages/stitcher-workspace/src/stitcher/workspace/discovery.py
~~~~~
~~~~~python
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from .exceptions import WorkspaceNotFoundError


def find_workspace_root(start_path: Path) -> Path:
    current = start_path.resolve()
    # If start_path is a file, start from its parent
    if current.is_file():
        current = current.parent

    # Traverse upwards
    for parent in [current] + list(current.parents):
        # 1. Check for .git (strongest indicator)
        if (parent / ".git").exists():
            return parent

        # 2. Check for pyproject.toml with workspace definition
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                # Check for uv workspace or similar tools
                if (
                    "tool" in data
                    and "uv" in data["tool"]
                    and "workspace" in data["tool"]["uv"]
                ):
                    return parent
            except Exception:
                pass

    # No root found in the entire hierarchy
    raise WorkspaceNotFoundError(str(start_path))
~~~~~

#### Acts 2: 从 `core.py` 中移除函数

现在 `find_workspace_root` 已经有了新家，我们将其从 `core.py` 中移除。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/core.py
~~~~~
~~~~~python.old
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from .config import StitcherConfig
from .exceptions import WorkspaceNotFoundError

log = logging.getLogger(__name__)


def find_workspace_root(start_path: Path) -> Path:
    current = start_path.resolve()
    # If start_path is a file, start from its parent
    if current.is_file():
        current = current.parent

    # Traverse upwards
    for parent in [current] + list(current.parents):
        # 1. Check for .git (strongest indicator)
        if (parent / ".git").exists():
            return parent

        # 2. Check for pyproject.toml with workspace definition
        pyproject = parent / "pyproject.toml"
        if pyproject.exists():
            try:
                with pyproject.open("rb") as f:
                    data = tomllib.load(f)
                # Check for uv workspace or similar tools
                if (
                    "tool" in data
                    and "uv" in data["tool"]
                    and "workspace" in data["tool"]["uv"]
                ):
                    return parent
            except Exception:
                pass

    # No root found in the entire hierarchy
    raise WorkspaceNotFoundError(str(start_path))


class Workspace:
~~~~~
~~~~~python.new
try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from .config import StitcherConfig
from .exceptions import WorkspaceNotFoundError

log = logging.getLogger(__name__)


class Workspace:
~~~~~

#### Acts 3: 修复所有相关的导入语句

最后，我们将所有引用点指向新的 `discovery.py` 模块，彻底打破循环。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/config.py
~~~~~
~~~~~python.old
from .core import find_workspace_root
from .exceptions import WorkspaceNotFoundError
~~~~~
~~~~~python.new
from .discovery import find_workspace_root
from .exceptions import WorkspaceNotFoundError
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/factories.py
~~~~~
~~~~~python.old
from stitcher.workspace.core import find_workspace_root
~~~~~
~~~~~python.new
from stitcher.workspace.discovery import find_workspace_root
~~~~~

~~~~~act
patch_file
packages/stitcher-workspace/tests/unit/test_workspace.py
~~~~~
~~~~~python.old
from stitcher.workspace import Workspace, WorkspaceNotFoundError
from stitcher.workspace.core import find_workspace_root
from stitcher.test_utils import WorkspaceFactory
~~~~~
~~~~~python.new
import pytest
from stitcher.workspace import Workspace, WorkspaceNotFoundError
from stitcher.workspace.discovery import find_workspace_root
from stitcher.test_utils import WorkspaceFactory
~~~~~

### 下一步建议

架构的核心缺陷已经修复。我们现在处于一个干净的状态，可以安全地再次验证我们的修改。

请再次运行 `pytest`。如果测试通过，这表明循环依赖问题已彻底解决，我们可以继续推进合并任务的下一个逻辑步骤。
