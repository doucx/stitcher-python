分析完毕。你的 `pytest` 错误报告非常清晰，它揭示了一个比类型冲突更深层次的架构缺陷：**包之间的循环依赖**。

我之前的计划在 `stitcher-analysis` 的 `engine.py` 中引入了 `from stitcher.app.services import Differ`，这违反了 HFEA 协议的**严格分层原则**。`analysis` 包作为更底层的能力提供者，绝对不能反向依赖于使用它的 `application` 包。

同时，第二个 `ModuleNotFoundError` 表明我在删除 `analyzer.py` 后，忘记清理其对应的测试文件，这是一个计划完整性的失误。

我将立即生成一个修正计划，从根本上解决这个架构问题。

## [WIP] fix: 通过重定位 Differ 服务解决循环依赖

### 错误分析

**1. 循环依赖 (Circular Import)**:
这是最严重的问题。`pytest` 的第一个错误回溯清晰地展示了依赖环路：
`test_consistency_engine` -> `analysis.engine` -> `app.services.Differ` -> `app.core` -> `app.runner` -> `analysis.engine`
这个环路使得 Python 的导入系统崩溃。根本原因在于 `Differ` 服务被错误地放置在了高层的 `application` 包中。`Differ` 本身是一个通用的、无状态的工具，它的正确位置应该是在 `stitcher-common` 包里，这样 `application` 和 `analysis`都可以安全地依赖它，而不会形成环路。

**2. 孤立的测试文件 (Orphaned Test File)**:
`pytest` 的第二个错误 `ModuleNotFoundError: No module named 'stitcher.app.runners.check.analyzer'` 发生的原因是：在我之前的计划中，我删除了源文件 `analyzer.py`，但遗漏了删除其对应的测试文件 `test_check_analyzer.py`。这个测试文件现在成了一个“孤儿”，试图导入一个不再存在的模块。

### 用户需求

修复因在 `stitcher-analysis` 中引入对 `stitcher-application` 的依赖而导致的循环导入错误，并清理因重构而产生的孤立测试文件。

### 评论

这是一个典型的架构重构中遇到的问题。它强调了服务和工具的归属权必须明确。将 `Differ` 这样的通用工具下沉到 `stitcher-common` 包，是实现“高内聚、低耦合”的正确实践。此举不仅能修复当前的循环依赖，还能使 `Differ` 服务在未来被其他新包复用，从而提升了代码库的整体健康度。

### 目标

1.  删除孤立的测试文件 `test_check_analyzer.py`。
2.  将 `Differ` 服务的实现从 `stitcher-application` 物理移动到 `stitcher-common`。
3.  更新 `stitcher-application` 和 `stitcher-analysis` 中的 `__init__.py` 文件和导入语句，以反映 `Differ` 的新位置。
4.  确保 `ConsistencyEngine` 从 `stitcher-common` 导入 `Differ`，从而打破循环依赖。

### 基本原理

我们将执行一次“服务重定位”操作。首先，清理无效的测试文件。然后，将 `differ.py` 文件从 `app/services` 目录移动到 `common/services` 目录。接着，我们会像整理书架一样，更新 `app` 和 `common` 两个包的“目录”（`__init__.py`），移除旧的导出并添加新的导出。最后，我们回到问题的起点——`consistency/engine.py`，将其导入语句指向 `Differ` 在 `stitcher-common` 中的新家。这个过程会从物理上切断两个包之间不健康的依赖关系，使架构恢复到正确的单向依赖流。

### 标签

#intent/fix #flow/ready #priority/critical #comp/application #comp/analysis #comp/common #concept/architecture #scope/core #ai/instruct #task/domain/testing #task/object/dependency-graph #task/action/refactor #task-state/continue

---

### Script

#### Acts 1: 清理孤立的测试文件

首先，我们删除已无用的 `test_check_analyzer.py`。

~~~~~act
delete_file
packages/stitcher-application/tests/unit/runners/check/test_check_analyzer.py
~~~~~

#### Acts 2: 将 `Differ` 服务重定位到 `stitcher-common`

现在，我们将 `Differ` 移动到正确的分层位置，并更新所有相关的导入和导出。

首先，移动 `differ.py` 文件本身。

~~~~~act
move_file
packages/stitcher-application/src/stitcher/app/services/differ.py
packages/stitcher-common/src/stitcher/common/services/differ.py
~~~~~

接着，从 `stitcher-application` 的 `services` 导出中移除 `Differ`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/__init__.py
~~~~~
~~~~~python.old
from .doc_manager import DocumentManager
from .signature_manager import SignatureManager
from .scanner import ScannerService
from .differ import Differ
from .merger import DocstringMerger

__all__ = [
    "DocumentManager",
    "SignatureManager",
    "ScannerService",
    "Differ",
    "DocstringMerger",
]
~~~~~
~~~~~python.new
from .doc_manager import DocumentManager
from .signature_manager import SignatureManager
from .scanner import ScannerService
from .merger import DocstringMerger

__all__ = [
    "DocumentManager",
    "SignatureManager",
    "ScannerService",
    "DocstringMerger",
]
~~~~~

然后，在 `stitcher-common` 的 `services` 中添加 `Differ` 的导出。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/services/__init__.py
~~~~~
~~~~~python
from .asset_path_resolver import AssetPathResolver
from .differ import Differ

__all__ = ["AssetPathResolver", "Differ"]
~~~~~

最后，更新 `ConsistencyEngine` 的导入语句，使其从 `stitcher-common` 导入 `Differ`，从而打破循环依赖。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/engines/consistency/engine.py
~~~~~
~~~~~python.old
from typing import List

from stitcher.app.services import Differ
from stitcher.spec import DifferProtocol
~~~~~
~~~~~python.new
from typing import List

from stitcher.common.services import Differ
from stitcher.spec import DifferProtocol
~~~~~

### 下一步建议

我们已经从根本上解决了循环依赖问题，并清理了相关的测试文件。现在，整个架构的依赖关系是健康的。

我建议再次运行 `pytest` 和 `pyright` 来验证修复的有效性。一旦通过，我们就可以继续进行**提取 Pump 逻辑**的任务。
