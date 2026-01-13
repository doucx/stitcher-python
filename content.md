好的，我们来实施阶段 2：创建新的持久化层。这包括在 `stitcher-lang-sidecar` 中实现 `LockFileManager` 并重写 `stitcher-lang-python` 中的 SURI 生成器。

## [WIP] feat: 实现 LockFileManager 并重写 SURIGenerator

### 用户需求
1.  **`LockFileManager`**: 在 `stitcher-lang-sidecar` 包中创建一个新的 `LockFileManager` 类，实现 `LockManagerProtocol` 协议。它将负责 `stitcher.lock` 文件的原子化、格式化的 JSON 读写操作。
2.  **`PythonURIGenerator`**: 在 `stitcher-lang-python` 包中，用一个新的 `PythonURIGenerator` 类替换旧的 `SURIGenerator`。新类将实现 `URIGeneratorProtocol` 协议，并依赖外部传入的、相对于 Workspace Root 的路径来生成 SURI，消除内部的路径计算。

### 评论
这是 SURI/Lockfile 架构迁移的核心技术实现。通过 `LockFileManager`，我们将指纹持久化从成百上千个小文件的高 I/O 模式，转变为对单个 Lock 文件的高效内存操作和原子写入模式。同时，重写 `PythonURIGenerator` 以依赖 Workspace 提供的坐标，是确保 SURI 全局唯一的关键一步。

### 目标
1.  在 `stitcher-lang-sidecar` 中创建 `lock_manager.py` 文件，并实现 `LockFileManager` 类。
2.  更新 `stitcher-lang-sidecar` 的 `__init__.py` 以导出新类。
3.  重写 `stitcher-lang-python/src/stitcher/lang/python/uri.py` 文件内容，用 `PythonURIGenerator` 替换 `SURIGenerator`。
4.  更新 `stitcher-lang-python` 的 `__init__.py` 以导出新类。

### 基本原理
-   **原子化 I/O**: 对 `stitcher.lock` 的操作遵循“全量读取 -> 内存修改 -> 全量写入”的模式，这简化了状态管理，并天然地保证了单次操作的原子性。
-   **确定性序列化**: `LockFileManager` 在写入 JSON 时强制使用 `sort_keys=True`，这使得 `stitcher.lock` 文件在内容相同时的序列化结果是确定性的，极大地减少了 `git diff` 的噪音和合并冲突。
-   **职责分离**: 新的 `PythonURIGenerator` 只负责字符串拼接，将路径计算的职责完全交给了 `Workspace`，遵循了单一职责原则。

### 标签
#intent/build #flow/ready #priority/high #comp/build #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/suri-lockfile #task/action/phase-2-implementation #task/state/continue

---

### Script

#### Acts 1: 实现 `LockFileManager` (`stitcher-lang-sidecar`)

我们首先创建新的 `LockFileManager`，它将成为管理 `stitcher.lock` 的唯一入口。

~~~~~act
write_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/lock_manager.py
~~~~~
~~~~~python
import json
from pathlib import Path
from typing import Dict

from stitcher.spec import LockManagerProtocol, Fingerprint


class LockFileManager(LockManagerProtocol):
    """
    Manages the reading and writing of stitcher.lock files.
    This implementation is non-migratory and will not read from the legacy
    .stitcher/signatures directory.
    """

    LOCK_FILE_NAME = "stitcher.lock"

    def load(self, package_root: Path) -> Dict[str, Fingerprint]:
        lock_path = package_root / self.LOCK_FILE_NAME
        if not lock_path.exists():
            return {}

        try:
            with lock_path.open("r", encoding="utf-8") as f:
                data = json.load(f)

            raw_fingerprints = data.get("fingerprints", {})
            if not isinstance(raw_fingerprints, dict):
                return {}  # Invalid format

            return {
                suri: Fingerprint.from_dict(fp_data)
                for suri, fp_data in raw_fingerprints.items()
            }
        except (json.JSONDecodeError, OSError):
            # Log a warning in a real scenario
            return {}

    def save(self, package_root: Path, data: Dict[str, Fingerprint]) -> None:
        lock_path = package_root / self.LOCK_FILE_NAME
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        serializable_data = {
            suri: fp.to_dict() for suri, fp in data.items()
        }

        lock_content = {
            "version": "1.0",
            "fingerprints": serializable_data,
        }

        with lock_path.open("w", encoding="utf-8") as f:
            json.dump(lock_content, f, indent=2, sort_keys=True)
            f.write("\n")  # Ensure trailing newline
~~~~~

现在，导出这个新类。

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/__init__.py
~~~~~
~~~~~python.old
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .adapter import SidecarAdapter
from .parser import parse_doc_references, parse_signature_references
from .transform import SidecarTransformContext, SidecarTransformer

__all__ = [
    "SidecarAdapter",
    "parse_doc_references",
    "parse_signature_references",
    "SidecarTransformContext",
    "SidecarTransformer",
]
~~~~~
~~~~~python.new
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .adapter import SidecarAdapter
from .lock_manager import LockFileManager
from .parser import parse_doc_references, parse_signature_references
from .transform import SidecarTransformContext, SidecarTransformer

__all__ = [
    "SidecarAdapter",
    "LockFileManager",
    "parse_doc_references",
    "parse_signature_references",
    "SidecarTransformContext",
    "SidecarTransformer",
]
~~~~~

#### Acts 2: 重写 `SURIGenerator` (`stitcher-lang-python`)

接下来，我们用实现了新协议的 `PythonURIGenerator` 替换掉旧的 `SURIGenerator`。

~~~~~act
write_file
packages/stitcher-lang-python/src/stitcher/lang/python/uri.py
~~~~~
~~~~~python
from typing import Optional

from stitcher.spec.protocols import URIGeneratorProtocol


class PythonURIGenerator(URIGeneratorProtocol):
    """
    Python-specific implementation of the SURI Generator Protocol.
    This class expects workspace-relative paths and does no path calculation itself.
    """
    @property
    def scheme(self) -> str:
        return "py"

    def generate_file_uri(self, workspace_rel_path: str) -> str:
        return f"{self.scheme}://{workspace_rel_path}"

    def generate_symbol_uri(self, workspace_rel_path: str, fragment: str) -> str:
        return f"{self.scheme}://{workspace_rel_path}#{fragment}"

    @staticmethod
    def parse(suri: str) -> tuple[str, Optional[str]]:
        """
        Utility method to parse a SURI into its path and fragment components.
        Note: This is a utility and not part of the URIGeneratorProtocol.
        """
        scheme_prefix = "py://"
        if not suri.startswith(scheme_prefix):
            raise ValueError(f"Invalid Python SURI: {suri}")

        content = suri[len(scheme_prefix):]
        if "#" in content:
            path, fragment = content.split("#", 1)
            return path, fragment
        return content, None
~~~~~

最后，更新包的导出。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/__init__.py
~~~~~
~~~~~python.old
"""Python language support for Stitcher."""

from .adapter import PythonAdapter
from .fingerprint import PythonFingerprintStrategy
from .inspector import InspectionError, parse_plugin_entry
from .parser.griffe import GriffePythonParser
from .parser.cst import PythonParser
from .transform.facade import PythonTransformer
from .uri import SURIGenerator
from .refactor import PythonRefactoringStrategy

__all__ = [
    "PythonAdapter",
    "PythonFingerprintStrategy",
    "InspectionError",
    "parse_plugin_entry",
    "GriffePythonParser",
    "PythonParser",
    "PythonTransformer",
    "SURIGenerator",
    "PythonRefactoringStrategy",
]
~~~~~
~~~~~python.new
"""Python language support for Stitcher."""

from .adapter import PythonAdapter
from .fingerprint import PythonFingerprintStrategy
from .inspector import InspectionError, parse_plugin_entry
from .parser.griffe import GriffePythonParser
from .parser.cst import PythonParser
from .transform.facade import PythonTransformer
from .uri import PythonURIGenerator
from .refactor import PythonRefactoringStrategy

__all__ = [
    "PythonAdapter",
    "PythonFingerprintStrategy",
    "InspectionError",
    "parse_plugin_entry",
    "GriffePythonParser",
    "PythonParser",
    "PythonTransformer",
    "PythonURIGenerator",
    "PythonRefactoringStrategy",
]
~~~~~

### 下一步建议
阶段 2 已完成。基础设施已就位。现在可以进入 **阶段 3: 手术式替换 (The Great Switch)**。

具体任务：
1.  从 `stitcher-application` 和 `stitcher-common` 中彻底移除旧的 `SignatureManager`。
2.  修改 `StitcherApp` 的构造函数，注入新的 `LockFileManager` 和 `PythonURIGenerator`。
3.  适配 `InitRunner`、`PumpRunner` 和 `CheckRunner`，使其使用新的管理器和生命周期（load -> operate -> save）。
