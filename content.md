[简要回答]
好的，我们现在将 `WorkspaceScanner` 集成到 `StitcherApp` 中，并通过 CLI 暴露 `stitcher index build` 命令。这将完成从底层扫描能力到用户交互界面的贯通。

## [WIP] feat(cli): 实现 `stitcher index build` 命令

### 用户需求
将之前实现的增量扫描能力暴露给用户。用户可以通过运行 `stitcher index build` 来构建或更新项目的语义索引。

### 评论
通过将 Scanner 集成到 `StitcherApp`，我们正式引入了状态化的索引层。这为后续的高级功能（如基于索引的重构、linting）奠定了基础。

### 目标
1.  在 `stitcher-application` 中实现 `IndexRunner`，负责协调数据库初始化和扫描过程。
2.  在 `StitcherApp` 中集成索引子系统（DB, Store, Scanner, Adapter）。
3.  更新 Needle 资源，添加相关日志文案。
4.  在 `stitcher-cli` 中添加 `index` 命令组和 `build` 子命令。

### 基本原理
*   **组合根模式**: `StitcherApp` 继续作为组合根，负责装配索引子系统的各个组件（DB, Store, Scanner）。
*   **默认配置**: 数据库路径硬编码为 `.stitcher/index/index.db`，这是为了保证架构的统一性。
*   **适配器注册**: 在 App 初始化时自动注册 `PythonAdapter`，确保开箱即用。

### 标签
#intent/build #flow/ready #priority/high #comp/cli #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/cli-command #task/action/integration #task/state/end

---

### Script

#### Acts 1: 添加 Needle 资源

首先定义 UI 文案。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/index/run.json
~~~~~
~~~~~json
{
  "start": "🔄 Starting incremental index build...",
  "complete": "✨ Indexing complete. Added: {added}, Updated: {updated}, Deleted: {deleted}, Skipped: {skipped}"
}
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/cli/command.json
~~~~~
~~~~~json.old
  "refactor_apply": {
    "help": "Apply automated refactorings from a migration script."
  },
  "not_implemented": "ℹ️  Command '{command}' is not yet implemented."
}
~~~~~
~~~~~json.new
  "refactor_apply": {
    "help": "Apply automated refactorings from a migration script."
  },
  "index": {
    "help": "Manage the semantic index."
  },
  "index_build": {
    "help": "Build or update the semantic index incrementally."
  },
  "not_implemented": "ℹ️  Command '{command}' is not yet implemented."
}
~~~~~

#### Acts 2: 实现 IndexRunner

在 Application 层封装调用逻辑。

~~~~~act
write_file
packages/stitcher-application/src/stitcher/app/runners/index.py
~~~~~
~~~~~python
from stitcher.common import bus
from needle.pointer import L
from stitcher.index.db import DatabaseManager
from stitcher.index.scanner import WorkspaceScanner


class IndexRunner:
    def __init__(self, db_manager: DatabaseManager, scanner: WorkspaceScanner):
        self.db_manager = db_manager
        self.scanner = scanner

    def run_build(self) -> bool:
        # Ensure DB is initialized (schema created)
        self.db_manager.initialize()

        bus.info(L.index.run.start)
        stats = self.scanner.scan()
        
        bus.success(
            L.index.run.complete,
            added=stats["added"],
            updated=stats["updated"],
            deleted=stats["deleted"],
            skipped=stats["skipped"],
        )
        return True
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/__init__.py
~~~~~
~~~~~python.old
from .transform import TransformRunner
from .coverage import CoverageRunner
from .refactor import RefactorRunner

__all__ = [
    "CheckRunner",
    "InitRunner",
    "PumpRunner",
    "TransformRunner",
    "CoverageRunner",
    "RefactorRunner",
]
~~~~~
~~~~~python.new
from .transform import TransformRunner
from .coverage import CoverageRunner
from .refactor import RefactorRunner
from .index import IndexRunner

__all__ = [
    "CheckRunner",
    "InitRunner",
    "PumpRunner",
    "TransformRunner",
    "CoverageRunner",
    "RefactorRunner",
    "IndexRunner",
]
~~~~~

#### Acts 3: 在 StitcherApp 中集成索引子系统

组装组件。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    CoverageRunner,
    RefactorRunner,
)
from stitcher.common.transaction import TransactionManager
from typing import Callable
from .types import PumpResult, FileCheckResult, CoverageResult
~~~~~
~~~~~python.new
    CoverageRunner,
    RefactorRunner,
    IndexRunner,
)
from stitcher.common.transaction import TransactionManager
from typing import Callable
from .types import PumpResult, FileCheckResult, CoverageResult
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore
from stitcher.index.scanner import WorkspaceScanner
from stitcher.adapter.python import PythonAdapter
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        self.coverage_runner = CoverageRunner(root_path, self.doc_manager)
        self.refactor_runner = RefactorRunner(root_path)

    def _load_configs(self) -> Tuple[List[StitcherConfig], Optional[str]]:
        return load_config_from_path(self.root_path)
~~~~~
~~~~~python.new
        self.coverage_runner = CoverageRunner(root_path, self.doc_manager)
        self.refactor_runner = RefactorRunner(root_path)

        # 3. Indexing Subsystem
        # Hardcoded path for architectural consistency
        index_db_path = root_path / ".stitcher" / "index" / "index.db"
        self.db_manager = DatabaseManager(index_db_path)
        self.index_store = IndexStore(self.db_manager)
        self.workspace_scanner = WorkspaceScanner(root_path, self.index_store)
        
        # Register Adapters
        # TODO: Load adapters dynamically or via config in future
        self.workspace_scanner.register_adapter(".py", PythonAdapter(root_path))
        
        self.index_runner = IndexRunner(self.db_manager, self.workspace_scanner)

    def _load_configs(self) -> Tuple[List[StitcherConfig], Optional[str]]:
        return load_config_from_path(self.root_path)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
        return self.refactor_runner.run_apply(
            migration_script, config_to_use, dry_run, confirm_callback
        )
~~~~~
~~~~~python.new
        return self.refactor_runner.run_apply(
            migration_script, config_to_use, dry_run, confirm_callback
        )

    def run_index_build(self) -> bool:
        return self.index_runner.run_build()
~~~~~

#### Acts 4: 实现 CLI 命令

~~~~~act
write_file
packages/stitcher-cli/src/stitcher/cli/commands/index.py
~~~~~
~~~~~python
import typer
from stitcher.common import stitcher_operator as nexus
from needle.pointer import L
from stitcher.cli.factories import make_app


def index_build_command():
    app_instance = make_app()
    app_instance.run_index_build()
~~~~~

#### Acts 5: 注册 CLI 命令

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
    strip_command,
    inject_command,
)

app = typer.Typer(
    name="stitcher",
    help=nexus(L.cli.app.description),
~~~~~
~~~~~python.new
    strip_command,
    inject_command,
)
from .commands.index import index_build_command

app = typer.Typer(
    name="stitcher",
    help=nexus(L.cli.app.description),
~~~~~

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
refactor_app.command(name="apply", help=nexus(L.cli.command.refactor_apply.help))(
    refactor_command
)
app.add_typer(refactor_app)
~~~~~
~~~~~python.new
refactor_app.command(name="apply", help=nexus(L.cli.command.refactor_apply.help))(
    refactor_command
)
app.add_typer(refactor_app)

# Index commands
index_app = typer.Typer(
    name="index", help=nexus(L.cli.command.index.help), no_args_is_help=True
)
index_app.command(name="build", help=nexus(L.cli.command.index_build.help))(
    index_build_command
)
app.add_typer(index_app)
~~~~~

### 下一步建议
运行 `stitcher index build` 进行验证，查看是否能正确生成 `.stitcher/index/index.db` 并输出统计信息。
后续任务：阶段 2，开始利用索引来优化 `check` 和 `refactor` 命令。
