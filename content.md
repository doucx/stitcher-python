好的，我们正式启动 **“从启发式猜测到确定性链接”** 路线图的第一阶段。

此计划将专注于 **Phase A: 统一 FQN 计算逻辑**。我们将创建一个单一、权威的工具函数，用于将文件路径转换为 Python 的完全限定名称 (FQN)，并重构 `refactor` 和 `index` 两个包来使用它。这为后续的架构统一奠定了坚实的基础。

## [WIP] refactor(analysis): 集中化 FQN 计算逻辑

### 错误分析

无。这是一项主动的架构重构，而非错误修复。

### 用户需求

创建一个单一事实来源 (SSoT)，用于将文件系统路径转换为 Python 的完全限定名称 (FQN)，以消除在 `refactor` 和 `index` 包中重复且可能不一致的逻辑。

### 评论

这是“确定性链接”宏大路线图中的关键第一步。它遵循了 DRY 和 HFEA 公理中的 SSoT 原则，通过将核心命名约定算法集中化，减少了维护开销，并防止了未来因命名方案不一致而导致的棘手错误。这是一次基础性的、高价值的清理工作。

### 目标

1.  在 `stitcher-python-analysis` 包中创建一个新的工具模块 `utils.py`。
2.  在该模块中实现一个健壮的、经过单元测试的 `path_to_logical_fqn` 函数。
3.  重构 `stitcher-refactor` 包，使其调用这个新的集中化函数。
4.  重构 `stitcher-python-adapter` (服务于 `stitcher-index`)，使其也调用该函数。
5.  移除旧的、重复的 FQN 计算实现。

### 基本原理

通过将路径到 FQN 的转换逻辑集中到 `stitcher-python-analysis` 包中，我们建立了一个可测试的、规范的算法。现在，重构引擎和索引引擎将使用完全相同的“命名语言”，这是实现更复杂的扫描-链接 (Scan-Link) 架构的绝对先决条件。此举消除了代码重复和两个系统之间语义漂移的风险。

### 标签

#intent/refine #flow/ready #priority/high #comp/refactor #comp/index #comp/python-analysis #comp/tests #scope/dx #ai/delegate #task/domain/architecture #task/object/component-unification #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 创建 FQN 工具模块及其单元测试

我们首先在 `stitcher-python-analysis` 包中创建新的 `utils.py` 模块，并为其编写全面的单元测试，确保它能正确处理各种路径格式，包括 `__init__.py` 文件。

~~~~~act
write_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/utils.py
~~~~~
~~~~~python
def path_to_logical_fqn(rel_path_str: str) -> str:
    """
    Converts a relative file path string into a Python Fully Qualified Name (FQN).

    - 'src/my_pkg/module.py' -> 'my_pkg.module'
    - 'my_pkg/__init__.py' -> 'my_pkg'
    """
    # Normalize path separators to dots
    fqn = rel_path_str.replace("/", ".")

    # Strip .py extension
    if fqn.endswith(".py"):
        fqn = fqn[:-3]

    # Handle __init__ files (e.g., 'pkg.__init__' -> 'pkg')
    if fqn.endswith(".__init__"):
        fqn = fqn[: -len(".__init__")]

    return fqn
~~~~~
~~~~~act
write_file
packages/stitcher-python-analysis/tests/unit/test_utils.py
~~~~~
~~~~~python
import pytest
from stitcher.python.analysis.utils import path_to_logical_fqn


@pytest.mark.parametrize(
    "input_path, expected_fqn",
    [
        ("src/my_pkg/module.py", "src.my_pkg.module"),
        ("my_pkg/module.py", "my_pkg.module"),
        ("my_pkg/__init__.py", "my_pkg"),
        ("toplevel.py", "toplevel"),
        ("a/b/c/__init__.py", "a.b.c"),
        # Edge case: No extension
        ("a/b/c", "a.b.c"),
    ],
)
def test_path_to_logical_fqn(input_path, expected_fqn):
    assert path_to_logical_fqn(input_path) == expected_fqn
~~~~~

#### Acts 2: 重构 `stitcher-refactor`

接下来，我们将 `stitcher-refactor` 中的 `_path_to_fqn` 方法替换为对新工具的调用。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/operations/base.py
~~~~~
~~~~~python.old
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class SidecarUpdateMixin:
    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
        base_path = None
        for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
            try:
                path.relative_to(sp)
                base_path = sp
                break
            except ValueError:
                continue

        if base_path is None:
            return None

        rel_path = path.relative_to(base_path)
        parts = list(rel_path.parts)

        if parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        elif parts[-1].endswith(".pyi"):
            parts[-1] = parts[-1][:-4]

        if parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts:
            return ""

        return ".".join(parts)
~~~~~
~~~~~python.new
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pathlib import Path

from stitcher.python.analysis.utils import path_to_logical_fqn
from stitcher.refactor.engine.context import RefactorContext
from stitcher.refactor.engine.intent import RefactorIntent


class SidecarUpdateMixin:
    def _path_to_fqn(self, path: Path, search_paths: List[Path]) -> Optional[str]:
        base_path = None
        for sp in sorted(search_paths, key=lambda p: len(p.parts), reverse=True):
            try:
                path.relative_to(sp)
                base_path = sp
                break
            except ValueError:
                continue

        if base_path is None:
            return None

        rel_path = path.relative_to(base_path)
        return path_to_logical_fqn(rel_path.as_posix())
~~~~~

#### Acts 3: 重构 `stitcher-python-adapter`

最后，我们更新 `PythonAdapter`，使其在为 `stitcher-index` 解析符号时使用相同的 FQN 计算逻辑。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
from stitcher.python.analysis.cst.usage_visitor import UsageScanVisitor, UsageRegistry
from .uri import SURIGenerator
~~~~~
~~~~~python.new
from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
from stitcher.python.analysis.cst.usage_visitor import UsageScanVisitor, UsageRegistry
from stitcher.python.analysis.utils import path_to_logical_fqn
from .uri import SURIGenerator
~~~~~
~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
        # Pre-calculate logical FQN for the module
        logical_module_fqn = rel_path.replace("/", ".").replace(".py", "")
        if logical_module_fqn.endswith(".__init__"):
            logical_module_fqn = logical_module_fqn[: -len(".__init__")]
~~~~~
~~~~~python.new
        # Pre-calculate logical FQN for the module
        logical_module_fqn = path_to_logical_fqn(rel_path)
~~~~~

### 下一步建议

我们已经成功地将 FQN 计算逻辑集中化，为后续的重构铺平了道路。

下一步，我们将执行 **Phase B: 抽象作用域构建器 (Scope Builder Abstraction)**。这将涉及在 `stitcher-python-analysis` 中创建另一个共享组件 `ScopeAnalyzer`，用于标准化 `local_symbols` 映射表的生成过程。这将进一步消除 `refactor` 和 `index` 之间的逻辑重复。
