好的，我们继续执行路线图的**任务 2.3**。

这是整个重构工作的“接线”环节。我们将修改 `refactor` 命令的入口点，用我们新创建的 `Workspace` 和 `SidecarManager` 服务替换掉所有旧的、硬编码的引导逻辑。

## [WIP] refactor: 在 CLI 引导流程中集成 Workspace 和 SidecarManager

### 用户需求

根据重构路线图，实施第二阶段的任务 2.3：
更新 `stitcher-cli` 中的 `refactor_command` 函数。移除其中所有硬编码的包发现和 `SemanticGraph` 初始化逻辑，替换为一个正确的、遵循我们新架构的引导序列：`Workspace` -> `SidecarManager` -> `SemanticGraph` -> `RefactorContext`。

### 评论

这是让我们的新架构真正生效的关键一步。通过在 CLI 命令这个“应用根”中组装我们的服务，我们完成了控制反转的闭环。此后，所有底层的重构操作都将通过 `RefactorContext` 接收到完全配置好的、由真实项目元数据驱动的依赖，从而彻底解决了原始实现的脆弱性问题。

### 目标

1.  **导入新组件**: 在 `refactor.py` 中导入 `Workspace` 和 `SidecarManager`。
2.  **重构引导序列**: 彻底修改 `refactor_command` 函数的开头部分，按照 `Workspace` -> `SidecarManager` -> `SemanticGraph` 的顺序创建实例。
3.  **移除旧逻辑**: 删除所有手动扫描 `packages` 目录以发现和加载包的硬编码循环。
4.  **动态加载**: 用一个新的、更简洁的循环替换旧逻辑，该循环从 `Workspace` 实例中获取所有发现的顶级包名并加载它们。
5.  **注入依赖**: 使用所有新创建的服务实例来初始化一个功能完备的 `RefactorContext`。

### 基本原理

我们将遵循“组合根”（Composition Root）的设计模式。应用程序的入口点（在这里是 `refactor_command`）是唯一负责创建和“连接”所有核心服务的地方。

1.  `Workspace` 首先被创建，它会立即扫描并理解整个项目的结构。
2.  `SidecarManager` 接着被创建。
3.  `SemanticGraph` 在创建时接收 `Workspace` 实例，从而获得了准确的搜索路径。
4.  我们遍历 `workspace.import_to_source_dirs.keys()` 来加载所有发现的顶级包，确保 `SemanticGraph` 包含了完整的语义信息。
5.  最后，所有这些服务都被注入到 `RefactorContext` 中。这个上下文对象随后被传递给 `Planner`，整个系统的依赖关系就以一种干净、解耦的方式建立起来了。

### 标签

#intent/refine #flow/ready #priority/high #comp/refactor #comp/cli #concept/dependency-injection #scope/core #ai/instruct #task/domain/refactor-engine #task/object/refactor-context #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 `refactor.py` 的导入

首先，我们更新 `refactor.py` 的导入语句，引入我们需要的 `Workspace` 和 `SidecarManager`，并移除不再需要的 `tomllib`。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python.old
import typer
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib

from stitcher.common import bus, stitcher_operator as nexus
from needle.pointer import L
from stitcher.refactor.engine import (
    SemanticGraph,
    RefactorContext,
    Planner,
    TransactionManager,
)
from stitcher.refactor.migration import MigrationLoader, MigrationError
~~~~~
~~~~~python.new
import typer
from pathlib import Path


from stitcher.common import bus, stitcher_operator as nexus
from needle.pointer import L
from stitcher.refactor.engine import (
    SemanticGraph,
    RefactorContext,
    Planner,
    TransactionManager,
)
from stitcher.refactor.migration import MigrationLoader, MigrationError
from stitcher.refactor.workspace import Workspace
from stitcher.refactor.sidecar.manager import SidecarManager
~~~~~

#### Acts 2: 重构 `refactor_command` 的引导逻辑

现在，我们用新的服务组合逻辑替换掉旧的、硬编码的初始化过程。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python.old
    root_path = Path.cwd()

    try:
        # 1. Load the complete semantic graph
        bus.info(L.refactor.run.loading_graph)
        graph = SemanticGraph(root_path)

        # Discover packages to load from the monorepo structure
        packages_dir = root_path / "packages"
        if packages_dir.is_dir():
            for pkg_path in packages_dir.iterdir():
                pyproject_path = pkg_path / "pyproject.toml"
                if pyproject_path.exists():
                    with pyproject_path.open("rb") as f:
                        data = tomllib.load(f)
                        pkg_name = data.get("project", {}).get("name")
                        if pkg_name:
                            graph.load(pkg_name)

        ctx = RefactorContext(graph)

        # 2. Load and plan the migration
        bus.info(L.refactor.run.planning)
~~~~~
~~~~~python.new
    root_path = Path.cwd()

    try:
        # 1. Bootstrap services
        bus.info(L.refactor.run.loading_graph)
        workspace = Workspace(root_path)
        sidecar_manager = SidecarManager(root_path)
        graph = SemanticGraph(workspace)

        # Load all packages discovered by the workspace
        for pkg_name in workspace.import_to_source_dirs.keys():
            graph.load(pkg_name)

        ctx = RefactorContext(
            workspace=workspace, graph=graph, sidecar_manager=sidecar_manager
        )

        # 2. Load and plan the migration
        bus.info(L.refactor.run.planning)
~~~~~

### 下一步建议

我们已经成功地将新的架构集成到了 CLI 入口点。现在，整个系统的引导流程是健壮且元数据驱动的。

路线图的下一个，也是第二阶段的最后一步，是**任务 2.4: 重构所有 `AbstractOperation` 子类**。我们将修改 `MoveFileOperation`、`MoveDirectoryOperation` 等类，让它们开始使用 `RefactorContext` 中提供的 `sidecar_manager`，从而彻底消除它们内部的硬编码路径逻辑。如果你同意，我将开始准备该计划。
