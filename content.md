好的，我们正式进入路线图的**阶段二**。第一步是演进 `RefactorContext`，将其打造为我们依赖注入策略的核心。

## [WIP] refactor: 演进 RefactorContext 以注入 Workspace 和 SidecarManager

### 用户需求

根据重构路线图，实施第二阶段的任务 2.1：
将 `Workspace` 和 `SidecarManager` 实例添加到 `RefactorContext` 数据类中，使其成为所有重构操作共享的、包含完整上下文的服务容器。

### 评论

这是一个虽小但至关重要的架构重构。通过将 `Workspace` 和 `SidecarManager` 注入到 `RefactorContext` 中，我们正式确立了依赖注入模式。`RefactorContext` 不再仅仅是一个数据持有者，而是变成了一个“服务定位器”，为所有下游操作提供了访问项目元数据和路径解析逻辑的统一入口。这极大地简化了后续的重构工作，并增强了系统的可扩展性。

### 目标

1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/context.py` 文件。
2.  在 `RefactorContext` dataclass 中添加 `workspace: Workspace` 和 `sidecar_manager: SidecarManager` 两个新字段。

### 基本原理

我们将遵循依赖注入的设计模式。`RefactorContext` 将作为所有共享服务（如 `SemanticGraph`、`Workspace`）的中央载体。在应用程序的引导阶段（`refactor_command`），我们会创建这些服务的单例，并将它们统一注入到 `RefactorContext` 实例中。

然后，这个包含了所有必要依赖的 `RefactorContext` 实例将被传递给所有需要它们的地方（如 `Planner` 和 `AbstractOperation` 子类）。这种方法避免了在函数签名中传递大量参数（"parameter drilling"），并使得在未来添加新的共享服务变得异常简单——只需将其添加到 `RefactorContext` 即可，而无需修改大量现有代码的签名。

### 标签

#intent/refine #flow/ready #priority/high #comp/refactor #concept/dependency-injection #scope/core #ai/instruct #task/domain/refactor-engine #task/object/refactor-context #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 扩展 `RefactorContext`

我们将修改 `context.py` 文件，导入 `Workspace` 和 `SidecarManager`，并将它们添加为 `RefactorContext` 的新成员。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/context.py
~~~~~
~~~~~python.old
from dataclasses import dataclass
from .graph import SemanticGraph


@dataclass
class RefactorContext:
    graph: SemanticGraph
~~~~~
~~~~~python.new
from dataclasses import dataclass

from stitcher.refactor.sidecar.manager import SidecarManager
from stitcher.refactor.workspace import Workspace
from .graph import SemanticGraph


@dataclass
class RefactorContext:
    workspace: Workspace
    graph: SemanticGraph
    sidecar_manager: SidecarManager
~~~~~

### 下一步建议

`RefactorContext` 现在已经准备好承载我们新的服务了。

下一步，我们将执行**任务 2.2: 重构 `SemanticGraph`**。我们将修改 `SemanticGraph` 的构造函数，使其不再接收 `root_path` 并进行路径猜测，而是直接接收一个 `Workspace` 实例，并从该实例获取权威的搜索路径列表。如果你同意，我将开始准备该计划。
