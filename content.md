好的，这是一个非常合理的架构重构。将核心业务逻辑从 CLI 层下沉到 Application 层是标准的整洁架构实践，可以提高逻辑的可复用性和可测试性。

我将生成一个计划来实现这一重构。

## [WIP] refactor(arch): 将重构逻辑从 CLI 移至 Application 层

### 用户需求

将 `stitcher refactor` 命令的核心业务逻辑从 `stitcher-cli` 包中迁移到 `stitcher-application` 包中，使 CLI 层只作为 Application 层的薄封装。

### 评论

这是一个关键的架构改进。当前 `refactor` 命令的实现逻辑（如图谱加载、计划生成、事务管理）都直接写在 CLI 命令函数中，这违反了关注点分离原则。

将这些核心逻辑封装到 Application 层的 `RefactorRunner` 中，可以带来以下好处：
1.  **可测试性**：可以独立测试 `RefactorRunner` 的业务逻辑，而无需模拟 Typer/Click 的交互。
2.  **可复用性**：未来如果提供其他入口（如 API 服务），可以直接复用 `RefactorRunner`。
3.  **清晰的边界**：CLI 层只负责处理用户输入、调用 Application 服务并呈现结果，职责更加单一。

### 目标

1.  在 `stitcher-application` 中创建一个新的 `RefactorRunner` 类，用于封装所有重构逻辑。
2.  将 `stitcher-refactor` 添加为 `stitcher-application` 的依赖。
3.  在 `StitcherApp` 核心类中集成并暴露 `RefactorRunner` 的功能。
4.  简化 `stitcher-cli` 中的 `refactor_command`，使其调用 `StitcherApp` 的新方法，并只处理用户交互（如预览、确认）和最终的事务提交。

### 基本原理

我们将遵循“依赖倒置”和“关注点分离”的原则。

1.  **创建 Runner**：在 `stitcher-application/src/stitcher/app/runners/` 目录下创建一个新的 `refactor.py` 文件，定义 `RefactorRunner`。这个 Runner 将在其构造函数中接收所有必要的依赖（如图谱、计划器等），并提供一个 `run` 方法来执行核心的重构分析和计划生成。`run` 方法将返回一个填充好操作的 `TransactionManager` 实例。
2.  **集成到 App**：在 `StitcherApp` 的 `__init__` 中，我们将实例化 `RefactorRunner` 及其依赖。然后，`StitcherApp` 将提供一个 `run_refactor` 方法，该方法会调用 `refactor_runner.run()` 并返回 `TransactionManager`。
3.  **简化 CLI**：CLI 中的 `refactor_command` 将不再关心如何加载图谱或生成计划。它会调用 `app_instance.run_refactor()` 来获取 `TransactionManager`，然后利用这个管理器来执行预览 (`tm.preview()`)、确认 (`typer.confirm`) 和提交 (`tm.commit()`) 等与用户界面紧密集成的操作。

这种方式将业务逻辑（做什么）与界面逻辑（如何展示和确认）完美地分离开来。

### 标签

#intent/refine #flow/ready #priority/high #comp/cli #comp/application #scope/core #scope/api #ai/instruct #task/domain/architecture #task/object/refactor-logic #task/action/relocation #task/state/begin

---

### Script

#### Acts 1: 在 Application 层创建新的 `RefactorRunner`

我们首先创建 `RefactorRunner`，它将包含从 CLI 迁移过来的核心逻辑。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/refactor.py
~~~~~
~~~~~python
from pathlib import Path

from stitcher.common import bus
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


class RefactorRunner:
    def __init__(
        self,
        workspace: Workspace,
        sidecar_manager: SidecarManager,
        graph: SemanticGraph,
        loader: MigrationLoader,
        planner: Planner,
        tm: TransactionManager,
    ):
        self.workspace = workspace
        self.sidecar_manager = sidecar_manager
        self.graph = graph
        self.loader = loader
        self.planner = planner
        self.tm = tm

    def run(self, migration_script: Path) -> TransactionManager:
        bus.info(L.refactor.run.loading_graph)
        pkg_names = list(self.workspace.import_to_source_dirs.keys())
        for pkg_name in pkg_names:
            self.graph.load(pkg_name)

        ctx = RefactorContext(
            workspace=self.workspace,
            graph=self.graph,
            sidecar_manager=self.sidecar_manager,
        )

        bus.info(L.refactor.run.planning)
        spec = self.loader.load_from_path(migration_script)
        file_ops = self.planner.plan(spec, ctx)

        if not file_ops:
            bus.success(L.refactor.run.no_ops)
            return self.tm

        for op in file_ops:
            if op.__class__.__name__ == "WriteFileOp":
                self.tm.add_write(op.path, op.content)
            elif op.__class__.__name__ == "MoveFileOp":
                self.tm.add_move(op.path, op.dest)
            elif op.__class__.__name__ == "DeleteFileOp":
                self.tm.add_delete_file(op.path)
            elif op.__class__.__name__ == "DeleteDirectoryOp":
                self.tm.add_delete_dir(op.path)

        return self.tm
~~~~~

#### Acts 2: 在 `runners` 包中注册新的 `RefactorRunner`

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/__init__.py
~~~~~
~~~~~python.old
from .check import CheckRunner
from .generate import GenerateRunner
from .init import InitRunner
from .pump import PumpRunner
from .transform import TransformRunner
from .coverage import CoverageRunner

__all__ = [
    "CheckRunner",
    "GenerateRunner",
    "InitRunner",
    "PumpRunner",
    "TransformRunner",
    "CoverageRunner",
]
~~~~~
~~~~~python.new
from .check import CheckRunner
from .generate import GenerateRunner
from .init import InitRunner
from .pump import PumpRunner
from .transform import TransformRunner
from .coverage import CoverageRunner
from .refactor import RefactorRunner

__all__ = [
    "CheckRunner",
    "GenerateRunner",
    "InitRunner",
    "PumpRunner",
    "TransformRunner",
    "CoverageRunner",
    "RefactorRunner",
]
~~~~~

#### Acts 3: 更新 Application 包的依赖

`stitcher-application` 现在需要 `stitcher-refactor` 提供的服务。

~~~~~act
patch_file
packages/stitcher-application/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-config",
    "stitcher-python-adapter",
    "pyneedle",
]
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-spec",
    "stitcher-common",
    "stitcher-config",
    "stitcher-python-adapter",
    "stitcher-refactor",
    "pyneedle",
]
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-config = { workspace = true }
stitcher-python-adapter = { workspace = true }
pyneedle = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-config = { workspace = true }
stitcher-python-adapter = { workspace = true }
stitcher-refactor = { workspace = true }
pyneedle = { workspace = true }
~~~~~

#### Acts 4: 将 `RefactorRunner` 集成到 `StitcherApp` 核心

现在我们在 `StitcherApp` 中组装并暴露重构功能。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
from .runners import (
    CheckRunner,
    GenerateRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
)
from .types import PumpResult, FileCheckResult, CoverageResult
from stitcher.adapter.python.docstring import (
    get_docstring_codec,
    get_docstring_serializer,
)
~~~~~
~~~~~python.new
from stitcher.refactor.engine import (
    TransactionManager,
    SemanticGraph,
    Planner,
    RefactorContext,
)
from stitcher.refactor.migration import MigrationLoader
from stitcher.refactor.workspace import Workspace
from stitcher.refactor.sidecar.manager import SidecarManager

from .runners import (
    CheckRunner,
    GenerateRunner,
    InitRunner,
    PumpRunner,
    TransformRunner,
    CoverageRunner,
    RefactorRunner,
)
from .types import PumpResult, FileCheckResult, CoverageResult
from stitcher.adapter.python.docstring import (
    get_docstring_codec,
    get_docstring_serializer,
)
~~~~~
~~~~~python.old
        self.transform_runner = TransformRunner(
            root_path, self.doc_manager, transformer
        )
        self.coverage_runner = CoverageRunner(root_path, self.doc_manager)

    def _load_configs(self) -> Tuple[List[StitcherConfig], Optional[str]]:
~~~~~
~~~~~python.new
        self.transform_runner = TransformRunner(
            root_path, self.doc_manager, transformer
        )
        self.coverage_runner = CoverageRunner(root_path, self.doc_manager)

        # 3. Refactor Services & Runner
        self.workspace = Workspace(root_path)
        self.sidecar_manager = SidecarManager(root_path)
        self.graph = SemanticGraph(self.workspace)
        self.loader = MigrationLoader()
        self.planner = Planner()
        self.tm = TransactionManager(root_path)
        self.refactor_runner = RefactorRunner(
            self.workspace,
            self.sidecar_manager,
            self.graph,
            self.loader,
            self.planner,
            self.tm,
        )

    def _load_configs(self) -> Tuple[List[StitcherConfig], Optional[str]]:
~~~~~
~~~~~python.old
    def run_cov(self) -> bool:
        configs, _ = self._load_configs()
        all_results: List[CoverageResult] = []

        for config in configs:
            modules = self._configure_and_scan(config)
            results = self.coverage_runner.run_batch(modules)
            all_results.extend(results)

        self.coverage_runner.report(all_results)
        return True
~~~~~
~~~~~python.new
    def run_cov(self) -> bool:
        configs, _ = self._load_configs()
        all_results: List[CoverageResult] = []

        for config in configs:
            modules = self._configure_and_scan(config)
            results = self.coverage_runner.run_batch(modules)
            all_results.extend(results)

        self.coverage_runner.report(all_results)
        return True

    def run_refactor(self, migration_script: Path) -> TransactionManager:
        return self.refactor_runner.run(migration_script)
~~~~~

#### Acts 5: 简化 CLI 命令以调用 Application 层

最后，我们将 `refactor_command` 简化为一个薄封装。由于改动较大，我们直接使用 `write_file`。

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/commands/refactor.py
~~~~~
~~~~~python
import typer
from pathlib import Path

from stitcher.common import bus, stitcher_operator as nexus
from needle.pointer import L
from stitcher.refactor.engine import TransactionManager
from stitcher.refactor.migration import MigrationError
from stitcher.cli.factories import make_app


def refactor_command(
    migration_script: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help=nexus(L.cli.option.refactor_script_path.help),
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help=nexus(L.cli.option.refactor_dry_run.help),
    ),
    yes: bool = typer.Option(
        False,
        "-y",
        "--yes",
        help=nexus(L.cli.option.refactor_yes.help),
    ),
):
    try:
        # 1. Bootstrap the application
        app_instance = make_app()

        # 2. Run the core logic via the application layer
        tm: TransactionManager = app_instance.run_refactor(migration_script)

        if tm.pending_count == 0:
            # The runner already reports L.refactor.run.no_ops
            return

        # 3. Handle CLI-specific interactions (Preview and Confirm)
        bus.warning(L.refactor.run.preview_header, count=tm.pending_count)
        for desc in tm.preview():
            typer.echo(f"  {desc}")

        if dry_run:
            return

        # 4. Execute
        confirmed = yes or typer.confirm(nexus(L.refactor.run.confirm), default=False)

        if not confirmed:
            bus.error(L.refactor.run.aborted)
            raise typer.Exit(code=1)

        bus.info(L.refactor.run.applying)
        tm.commit()
        bus.success(L.refactor.run.success, count=len(tm.preview()))

    except (MigrationError, FileNotFoundError) as e:
        bus.error(L.error.generic, error=str(e))
        raise typer.Exit(code=1)
    except Exception as e:
        bus.error(L.error.generic, error=f"An unexpected error occurred: {e}")
        raise typer.Exit(code=1)
~~~~~

### 下一步建议

我们已经完成了代码的重构和迁移。现在，最合适的下一步是创建一个 `[COMMIT]` 计划，将这些架构改进作为一个原子性的提交保存到版本控制中。如果你同意，我将立即生成这个提交计划。
