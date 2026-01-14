分析显示，这组循环依赖是由 **“贪婪包枢纽 (Greedy Package Hub)”** 模式引起的。这在复杂的 Python 项目中是一个非常隐蔽的架构陷阱。

这次循环的拓扑结构如下：

1.  **枢纽点 (Hub)**: `stitcher/app/runners/__init__.py` 试图作为一个便捷的出口，通过 `from .check import CheckRunner` 等语句导出所有的 Runner。
2.  **触发点 (Trigger)**: `StitcherApp` (`core.py`) 导入了这个枢纽：`from .runners import CheckRunner`。
3.  **绝对路径陷阱**: `runners/check/runner.py` 中使用了绝对导入：
    ```python
    from stitcher.app.runners.check.resolver import CheckResolver
    ```
4.  **死锁逻辑**:
    *   当 Python 执行 `core.py` 时，它触碰了 `stitcher.app.runners`。
    *   `stitcher.app.runners` 的 `__init__.py` 开始执行，它尝试加载 `stitcher.app.runners.check`。
    *   `check/__init__.py` 尝试加载 `check/runner.py`。
    *   `runner.py` 执行到绝对导入 `from stitcher.app.runners.check.resolver ...` 时，Python 解释器必须确保其父包 `stitcher.app.runners` 已完成初始化。
    *   **由于 `stitcher.app.runners` 正卡在第一步（等待 `CheckRunner` 导入），系统进入循环死锁。**

为了符合 **“高保真工程公理 (HFEA)”** 中关于“确定性路径”和“零启发式策略”的要求，我们必须拆除所有的“贪婪枢纽”，将导入路径扁平化。

## [WIP] fix(arch): eliminate greedy package hubs in runners to break circular deadlocks

### 错误分析
检测到的循环依赖源于 `stitcher.app.runners` 及其子包试图在 `__init__.py` 中自动导出成员。这种“便捷性”在大型项目中会导致严重的初始化死锁，尤其是在组合根 (`StitcherApp`) 需要引用这些成员时。

### 用户需求
彻底修复 `stitcher check` 报告的 `runners/check` 循环依赖。

### 评论
包的 `__init__.py` 应该尽可能保持纯净，仅作为命名空间的声明。任何在 `__init__.py` 中执行的逻辑导入都相当于在系统的血管中埋下血栓。通过将导入直接指向叶子模块，我们可以释放系统的初始化压力，实现确定性的加载顺序。

### 目标
1.  清理 `stitcher/app/runners/` 及其子目录（`check`, `pump`）下的 `__init__.py` 文件，移除所有逻辑导入。
2.  更新 `StitcherApp` (`core.py`)，使其直接从叶子模块（如 `runners.check.runner`）导入所需的类。
3.  在 `runners/check/runner.py` 中将绝对导入改为相对导入，以进一步隔离初始化副作用。

### 基本原理
通过移除包级别的“重导出 (Re-exports)”，我们切断了包初始化与模块加载之间的强制耦合。这意味着加载一个具体的 Runner 模块不再需要其父包完成对 *所有* Runner 的预加载。

### 标签
#intent/refine #flow/ready #priority/high #comp/application #concept/initialization-order #scope/core #ai/instruct #task/domain/architecture #task/object/greedy-init-hub #task/action/flattening #task/state/continue

---

### Script

#### Acts 1: 清理 Runners 及其子包的 `__init__.py`

我们将移除这些文件中的所有贪婪导入，只保留基本的命名空间支持。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/check/__init__.py
~~~~~
~~~~~python
# This directory is a package.
~~~~~

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/pump/__init__.py
~~~~~
~~~~~python
# This directory is a package.
~~~~~

#### Acts 2: 更新 `StitcherApp` 的导入路径

现在我们需要让 `StitcherApp` 直接从物理文件导入类，而不是通过已清理的 `__init__.py`。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from .runners import (
    CheckRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
    IndexRunner,
)
~~~~~
~~~~~python.new
from .runners.check.runner import CheckRunner
from .runners.init import InitRunner
from .runners.pump.runner import PumpRunner
from .runners.transform import TransformRunner
from .runners.coverage import CoverageRunner
from .runners.refactor import RefactorRunner
from .runners.index import IndexRunner
~~~~~

#### Acts 3: 优化 `CheckRunner` 的内部导入

将绝对导入改为相对导入，彻底消除对父包初始化状态的依赖。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
from stitcher.app.runners.check.resolver import CheckResolver
from stitcher.app.runners.check.reporter import CheckReporter
~~~~~
~~~~~python.new
from .resolver import CheckResolver
from .reporter import CheckReporter
~~~~~

### 下一步建议
- **执行架构检查**: 运行 `stitcher check`。现在所有的循环依赖路径应该都被切断了。
- **清理其他 Runner 子包**: 检查 `init`, `transform` 等其他子包是否也存在类似的贪婪 `__init__.py`，并按此模式清理。
- **提交变更**: 如果检查通过，创建一个新的 `[COMMIT]` 计划。
