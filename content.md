简要回答
执行 SURI 全局化架构重构的阶段 1：定义核心协议 (`stitcher-spec`) 并增强工作区坐标系能力 (`stitcher-workspace`)。

## [WIP] feat: 定义 SURI 协议并增强 Workspace 坐标系能力

### 用户需求
1.  **协议定义**: 在 `stitcher-spec` 中定义 `URIGeneratorProtocol` 和 `LockManagerProtocol`，确立 SURI 生成和 Lock 文件管理的接口标准。
2.  **坐标系增强**: 在 `stitcher-workspace` 中实现 `find_workspace_root`、`find_owning_package` 和 `to_workspace_relative`，使 `Workspace` 能够作为全系统的地理定位服务，确保 SURI 基于 Workspace Root 锚定。

### 评论
这是整个 SURI/Lockfile 架构转型的基石。通过将 SURI 生成抽象为协议，解耦了具体的语言实现；通过赋予 Workspace 全局路径解释权，解决了 Monorepo 下路径歧义的问题。这一步虽然不涉及具体业务逻辑迁移，但决定了后续重构的正确性。

### 目标
1.  修改 `stitcher-spec/src/stitcher/spec/protocols.py`，添加 `URIGeneratorProtocol` 和 `LockManagerProtocol`。
2.  更新 `stitcher-spec/src/stitcher/spec/__init__.py` 导出新协议。
3.  修改 `stitcher-workspace/src/stitcher/workspace/workspace.py`，实现工作区根目录查找、包归属查找和相对路径计算逻辑。

### 基本原理
-   **协议先行**: 根据 ADAP 协议，首先定义清晰的接口契约，消除实现时的模糊性。
-   **SSoT (Single Source of Truth)**: Workspace Root 是计算 SURI 的唯一参考点，必须通过统一的算法 (`find_workspace_root`) 来确定，避免各组件自行猜测。
-   **物理与逻辑分离**: `find_owning_package` 建立了文件（物理）到包（逻辑单元/Lock文件边界）的明确映射。

### 标签
#intent/architect #flow/ready #priority/critical #comp/interfaces #comp/build #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/suri-lockfile #task/action/phase-1-implementation #task/state/begin

---

### Script

#### Acts 1: 定义核心协议 (`stitcher-spec`)

首先，我们在 `stitcher-spec` 中定义 SURI 生成器和 Lock 管理器的协议。这将作为后续实现的契约。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
from typing import Protocol, Dict, Union, Optional, List, Any
from .models import ModuleDef, FunctionDef, ClassDef
from .fingerprint import Fingerprint
from .docstring import DocstringIR
~~~~~
~~~~~python.new
from typing import Protocol, Dict, Union, Optional, List, Any
from pathlib import Path
from .models import ModuleDef, FunctionDef, ClassDef
from .fingerprint import Fingerprint
from .docstring import DocstringIR
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/protocols.py
~~~~~
~~~~~python.old
class DocstringSerializerProtocol(Protocol):
    def to_yaml(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR: ...
~~~~~
~~~~~python.new
class DocstringSerializerProtocol(Protocol):
    def to_yaml(self, ir: DocstringIR) -> Union[str, Dict[str, Any]]: ...

    def from_yaml(self, data: Union[str, Dict[str, Any]]) -> DocstringIR: ...


class URIGeneratorProtocol(Protocol):
    """
    Protocol for generating Stitcher Uniform Resource Identifiers (SURIs).
    SURIs must be anchored to the workspace root to ensure global uniqueness.
    """

    @property
    def scheme(self) -> str: ...

    def generate_file_uri(self, workspace_rel_path: str) -> str: ...

    def generate_symbol_uri(self, workspace_rel_path: str, fragment: str) -> str: ...


class LockManagerProtocol(Protocol):
    """
    Protocol for managing the stitcher.lock file, which serves as the distributed
    persistence layer for fingerprints.
    """

    def load(self, package_root: Path) -> Dict[str, Fingerprint]: ...

    def save(self, package_root: Path, data: Dict[str, Fingerprint]) -> None: ...
~~~~~

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python.old
    "DocstringParserProtocol",
    "DocstringRendererProtocol",
    "DocstringSerializerProtocol",
    "DocumentManagerProtocol",
    "SignatureManagerProtocol",
    "DifferProtocol",
    "DocstringMergerProtocol",
    "IndexStoreProtocol",
    "Fingerprint",
~~~~~
~~~~~python.new
    "DocstringParserProtocol",
    "DocstringRendererProtocol",
    "DocstringSerializerProtocol",
    "URIGeneratorProtocol",
    "LockManagerProtocol",
    "DocumentManagerProtocol",
    "SignatureManagerProtocol",
    "DifferProtocol",
    "DocstringMergerProtocol",
    "IndexStoreProtocol",
    "Fingerprint",
~~~~~

#### Acts 2: 增强 Workspace 坐标系能力 (`stitcher-workspace`)

接着，我们在 `stitcher-workspace` 中实现核心的路径计算逻辑。这些方法将作为全系统的坐标基准。

~~~~~act
patch_file
packages/stitcher-workspace/src/stitcher/workspace/workspace.py
~~~~~
~~~~~python.old
import logging
import os
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from stitcher.config import StitcherConfig

log = logging.getLogger(__name__)


class Workspace:
    def __init__(self, root_path: Path, config: Optional[StitcherConfig] = None):
        self.root_path = root_path
        self.config = config
        # 'cascade' -> {'/path/to/cascade-application/src', '/path/to/cascade-engine/src'}
        self.import_to_source_dirs: Dict[str, Set[Path]] = defaultdict(set)
        self.peripheral_source_dirs: Set[Path] = set()

        if self.config:
            self._build_from_config()
        else:
            self._discover_packages()

    def _build_from_config(self) -> None:
~~~~~
~~~~~python.new
import logging
import os
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

from stitcher.config import StitcherConfig

log = logging.getLogger(__name__)


def find_workspace_root(start_path: Path) -> Path:
    """
    Finds the workspace root by looking for a .git directory or a top-level pyproject.toml
    defining a workspace.
    """
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
                if "tool" in data and "uv" in data["tool"] and "workspace" in data["tool"]["uv"]:
                    return parent
            except Exception:
                pass
    
    # Fallback: if nothing found, return the start path (or raise error? For now, start path)
    return start_path


class Workspace:
    def __init__(self, root_path: Path, config: Optional[StitcherConfig] = None):
        self.root_path = root_path.resolve()
        self.config = config
        # 'cascade' -> {'/path/to/cascade-application/src', '/path/to/cascade-engine/src'}
        self.import_to_source_dirs: Dict[str, Set[Path]] = defaultdict(set)
        self.peripheral_source_dirs: Set[Path] = set()

        if self.config:
            self._build_from_config()
        else:
            self._discover_packages()

    def find_owning_package(self, file_path: Path) -> Path:
        """
        Finds the nearest directory containing a pyproject.toml upwards from the file_path.
        This determines the physical location of the stitcher.lock file.
        Returns the workspace root if no package-level pyproject.toml is found.
        """
        current = file_path.resolve()
        if current.is_file():
            current = current.parent
        
        # Stop if we hit the workspace root to avoid escaping the project
        while current != self.root_path and current != current.parent:
            if (current / "pyproject.toml").exists():
                return current
            current = current.parent
            
        return self.root_path

    def to_workspace_relative(self, path: Path) -> str:
        """
        Converts an absolute path to a POSIX path relative to the workspace root.
        This is the canonical format for SURI paths.
        """
        return path.resolve().relative_to(self.root_path).as_posix()

    def _build_from_config(self) -> None:
~~~~~

### 下一步建议

阶段 1 已完成。下一步应进入 **阶段 2: 新持久化层 (New Persistence Layer)**。

具体任务：
1.  在 `stitcher-lang-sidecar` 中实现 `LockFileManager`，负责 `stitcher.lock` 的原子读写。
2.  在 `stitcher-lang-python` 中重写 `SURIGenerator`，实现新的 `URIGeneratorProtocol`，利用 `Workspace` 计算相对路径。
