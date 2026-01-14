好的，进入 Quipu 模式。

您的分析完全正确。这些是真实存在的、由不恰当的包结构和 `__init__.py` 文件中的循环导入引起的架构级循环依赖。它们严重破坏了系统的模块化和可维护性。

我将生成一个计划，通过两个核心策略来解决这些问题：

1.  **依赖倒置 (Dependency Inversion)**: 将 `stitcher-application` 包中的通用服务（`DocumentManager`, `ScannerService` 等）移动到一个更高层级的、更中立的位置，以便 `stitcher-application` 和 `stitcher-stubgen` 都可以单向地依赖它们，从而打破跨包循环。
2.  **解耦包初始化**: 简化 `stitcher.app` 和 `stitcher.cli` 包的 `__init__.py` 文件，移除其中对核心对象的导入。这将防止在包初始化阶段过早地加载实现细节，从而打破包内的循环导入。

这个计划将遵循高保真工程公理，旨在彻底根除架构异味，而非采取临时变通。

## [WIP] fix(architecture): Resolve circular dependencies across application, stubgen, and cli packages

### 错误分析

静态分析工具检测到了三组主要的循环依赖，它们并非误报，而是由当前的包结构和导入策略引起的真实架构问题：

1.  **`stitcher-application` 与 `stitcher-stubgen` 的跨包循环**:
    *   `stitcher-application`在其核心 `StitcherApp` 中导入并使用了 `stitcher-stubgen` 提供的 `StubgenService`。
    *   与此同时，`stitcher-stubgen` 为了执行其任务，又需要从 `stitcher.app.services` 中导入 `ScannerService` 和 `DocumentManager`。
    *   这就形成了一个 A -> B -> A 的经典跨包循环，表明 `ScannerService` 和 `DocumentManager` 这些通用服务被错误地放置在了应用层的实现细节中。

2.  **`stitcher-application` 内部的初始化循环**:
    *   `stitcher/app/__init__.py` 文件试图通过 `from .core import StitcherApp` 来暴露核心应用类，以便于外部导入。
    *   然而，`app/core.py` (即 `StitcherApp`) 是一个“组合根”，它需要导入并组装项目中的许多其他组件，例如位于 `app/runners/` 下的各个 Runner。
    *   这些 Runner 的子模块（如 `resolver.py`）又需要导入应用层的其他部分（如 `app/handlers`）。
    *   当外部模块执行 `import stitcher.app` 时，`__init__.py` 开始执行，加载 `core.py`，`core.py` 加载 `runners`，`runners` 加载 `resolver`，`resolver` 又尝试导入 `stitcher.app.handlers`，这会重新触发对 `stitcher.app` 包的加载，而此时该包正在初始化过程中，从而导致循环。

3.  **`stitcher-cli` 内部的初始化循环**:
    *   这与 `stitcher-application` 的问题如出一辙。`cli/__init__.py` 导入了 `main.app`。
    *   `cli/main.py` 导入了 `cli/commands/*` 中的所有命令函数。
    *   而这些命令函数又通过 `from stitcher.cli.factories import make_app` 绝对路径导入，这会重新触发对 `stitcher.cli` 包的加载，形成循环。

### 用户需求

修复 `stitcher check` 命令报告的所有架构级循环依赖错误。

### 评论

这是一个至关重要的架构重构。解决循环依赖将极大地提高代码库的健康度、可测试性和可维护性。它使得各个组件可以被独立地理解和修改，而不会产生不可预见的副作用，完全符合“高保真工程公理”中对严格分层和清晰边界的要求。

### 目标

1.  将 `stitcher.app.services` 目录重构为一个独立的、位于 `stitcher` 命名空间下的 `stitcher.services` 包。
2.  更新所有相关模块，使其从新的 `stitcher.services` 路径导入 `DocumentManager`, `ScannerService`, 和 `DocstringMerger`。
3.  简化 `stitcher-application/src/stitcher/app/__init__.py`，移除对 `StitcherApp` 的导入。
4.  简化 `stitcher-cli/src/stitcher/cli/__init__.py`，移除对 `app` 的导入。
5.  最终使 `stitcher check` 不再报告任何架构错误。

### 基本原理

本计划遵循“依赖倒置原则”。`ScannerService` 和 `DocumentManager` 是比 `StitcherApp` 和 `StubgenService` 更底层、更通用的服务。将它们从应用实现层 (`app/services`) 移动到一个平级的服务层 (`services`)，可以打破错误的依赖关系。`application` 和 `stubgen` 都将变成这些通用服务的客户端，而服务本身对上层应用一无所知。

同时，通过简化 `__init__.py` 文件，我们遵循了“显式优于隐式”的原则。包的 `__init__.py` 不应成为一个复杂的 API 聚合器，这会掩盖真实的依赖关系并引发初始化问题。调用者应该明确地从它们需要的具体模块（如 `stitcher.app.core`）导入对象。

### 标签

#intent/refine #flow/ready #priority/high #comp/application #comp/cli #concept/dependency-graph #scope/core #scope/dx #ai/brainstorm #task/domain/architecture #task/object/circular-dependency #task/action/elimination #task/state/begin

---

### Script

#### Acts 1: 重构 Services 目录

我们将 `services` 从 `app` 的子目录提升为 `stitcher` 的一个顶级子目录，使其成为一个独立的、可被其他组件依赖的服务层。

~~~~~act
run_command
~~~~~
~~~~~bash
mv packages/stitcher-application/src/stitcher/app/services packages/stitcher-application/src/stitcher/services
~~~~~

接下来，在新的 `services` 目录中创建一个 `__init__.py` 文件，使其成为一个合法的 Python 包。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/services/__init__.py
~~~~~
~~~~~python
from .doc_manager import DocumentManager
from .scanner import ScannerService
from .merger import DocstringMerger

__all__ = [
    "DocumentManager",
    "ScannerService",
    "DocstringMerger",
]
~~~~~

#### Acts 2: 更新 `stitcher-stubgen` 的导入路径

现在 `services` 已经移动，我们需要更新 `stitcher-stubgen` 中对这些服务的导入路径。

~~~~~act
patch_file
packages/stitcher-stubgen/src/stitcher/stubgen/__init__.py
~~~~~
~~~~~python.old
from stitcher.app.services import (
    ScannerService,
    DocumentManager,
)
~~~~~
~~~~~python.new
from stitcher.services import (
    ScannerService,
    DocumentManager,
)
~~~~~

~~~~~act
patch_file
packages/stitcher-stubgen/src/stitcher/stubgen/runners.py
~~~~~
~~~~~python.old
from stitcher.app.services import (
    DocumentManager,
    ScannerService,
)
~~~~~
~~~~~python.new
from stitcher.services import (
    DocumentManager,
    ScannerService,
)
~~~~~

#### Acts 3: 更新 `stitcher-application` 的导入路径

同样，更新 `stitcher-application` 内部对 `services` 的引用。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from stitcher.app.services import (
    DocumentManager,
    ScannerService,
    DocstringMerger,
)
~~~~~
~~~~~python.new
from stitcher.services import (
    DocumentManager,
    ScannerService,
    DocstringMerger,
)
~~~~~

#### Acts 4: 解耦 `stitcher-application` 的 `__init__.py`

简化 `app/__init__.py`，打破内部初始化循环。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 5: 解耦 `stitcher-cli` 的 `__init__.py`

简化 `cli/__init__.py`，打破CLI层面的内部初始化循环。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

### 下一步建议

在应用此计划后，架构循环依赖问题应该已经得到解决。

我强烈建议您立即再次运行 `stitcher check` 命令。这不仅可以验证我们的修复是否成功，还可以确保在重构过程中没有引入新的问题。如果检查通过，我们就可以继续处理其他任务或将这些架构改进作为一个完整的单元提交。
