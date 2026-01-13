你的分析完全正确，我的诊断存在疏漏。我陷入了单元测试思维的陷阱：我为 `find_workspace_root` 函数本身添加了正确的行为和测试，但**我完全忽略了在应用程序的实际启动路径中调用它**。

这是一个典型的集成疏忽，也是“正规军工程标准”中“确定性路径追踪”原则的一个反面教材。系统在启动时没有追踪到正确的根路径，而是走了一条看似简单的“捷径”（`Path.cwd()`）。

**错误根源分析**:

1.  `stitcher-cli` 中的 `commands/*.py` 文件调用 `factories.make_app()`。
2.  `factories.make_app()` 调用 `factories.get_project_root()`，后者简单地返回 `Path.cwd()`。
3.  `make_app()` 随后用这个 `Path.cwd()` 路径去初始化 `StitcherApp`。
4.  `StitcherApp` 接收这个路径，并用它初始化 `Workspace`。
5.  `Workspace` 类本身并不会去*寻找*根，它只是*接受*一个被指定的根。
6.  因此，我们精心加固的 `find_workspace_root` 函数从未被调用，`WorkspaceNotFoundError` 自然也从未被抛出。系统愉快地将临时测试目录或 `~/tmp/o` 当作了项目根目录，并继续执行。

现在，我们将纠正这个集成错误，确保应用程序的启动流程是确定且正确的。

## [WIP] fix: 集成工作区根目录发现逻辑到应用启动路径

### 错误分析
上一个计划中创建的 `find_workspace_root` 函数虽然逻辑正确，但并未在 `stitcher-cli` 的应用工厂 (`make_app`) 中被实际调用。工厂函数错误地使用了 `Path.cwd()` 作为 `StitcherApp` 的根目录，绕过了所有健壮性检查，导致在无效目录中运行时命令依然“成功”执行，这与预期行为完全相反。

### 用户需求
修改 `make_app` 工厂函数，强制它在创建 `StitcherApp` 实例之前，必须先调用 `find_workspace_root` 来确定一个有效的项目根目录。如果找不到，则应让 `WorkspaceNotFoundError` 自然抛出，由上层命令捕获。

### 评论
这是一个关键的修复，它将我们之前定义的确定性原则真正地应用到了系统的入口点。通过在“组合根 (Composition Root)”处解决路径问题，我们确保了整个应用程序实例都在一个已知且有效的上下文中运行。

### 目标
1.  修改 `stitcher.cli.factories.make_app` 函数。
2.  移除多余的 `get_project_root` 函数。
3.  确保 `make_app` 调用 `find_workspace_root` 并使用其返回值来实例化 `StitcherApp`。
4.  重新运行测试，确认 `test_command_fails_gracefully_outside_workspace` 现在可以通过。

### 基本原理
应用程序的正确性始于其初始化。通过将根目录的发现和验证逻辑移至应用实例化的最前端，我们遵循了“先验证，后执行”的安全原则，从根本上杜绝了在错误上下文中操作的可能性。

### 标签
#intent/fix #flow/ready #priority/critical 
#comp/cli #comp/workspace #scope/core 
#ai/refine
#task/domain/workspace #task/object/root-discovery #task/action/hardening #task/state/continue

---

### Script

#### Acts 1: 修正应用工厂 `make_app`

这是唯一的、也是最关键的修改。我们将 `find_workspace_root` 集成到 `make_app` 中，并移除不再需要的 `get_project_root`。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/factories.py
~~~~~
~~~~~python.old
import sys
from pathlib import Path
from typing import Optional

from stitcher.app import StitcherApp
from stitcher.spec.interaction import InteractionHandler
from stitcher.common import stitcher_operator as nexus
from stitcher.lang.python import (
    GriffePythonParser,
    PythonTransformer,
    PythonFingerprintStrategy,
)

from .handlers import TyperInteractionHandler
from .interactive import TyperInteractiveRenderer


def get_project_root() -> Path:
    return Path.cwd()


def make_interaction_handler(
    non_interactive: bool = False,
    auto_resolve_mode: bool = False,
) -> Optional[InteractionHandler]:
    if sys.stdin.isatty() and not non_interactive and not auto_resolve_mode:
        renderer = TyperInteractiveRenderer(nexus)
        return TyperInteractionHandler(renderer)
    return None


def make_app(
    handler: Optional[InteractionHandler] = None,
) -> StitcherApp:
    # Composition Root: Assemble the dependencies
    # UNIFIED: Always use Griffe for analysis
    parser = GriffePythonParser()

    transformer = PythonTransformer()
    strategy = PythonFingerprintStrategy()

    return StitcherApp(
        root_path=get_project_root(),
        parser=parser,
        transformer=transformer,
        fingerprint_strategy=strategy,
        interaction_handler=handler,
    )
~~~~~
~~~~~python.new
import sys
from pathlib import Path
from typing import Optional

from stitcher.app import StitcherApp
from stitcher.spec.interaction import InteractionHandler
from stitcher.common import stitcher_operator as nexus
from stitcher.lang.python import (
    GriffePythonParser,
    PythonTransformer,
    PythonFingerprintStrategy,
)
from stitcher.workspace.workspace import find_workspace_root

from .handlers import TyperInteractionHandler
from .interactive import TyperInteractiveRenderer


def make_interaction_handler(
    non_interactive: bool = False,
    auto_resolve_mode: bool = False,
) -> Optional[InteractionHandler]:
    if sys.stdin.isatty() and not non_interactive and not auto_resolve_mode:
        renderer = TyperInteractiveRenderer(nexus)
        return TyperInteractionHandler(renderer)
    return None


def make_app(
    handler: Optional[InteractionHandler] = None,
) -> StitcherApp:
    # Composition Root: Assemble the dependencies
    
    # 1. Determine the true workspace root. This may raise WorkspaceNotFoundError,
    # which is caught by the command functions.
    project_root = find_workspace_root(Path.cwd())

    # 2. UNIFIED: Always use Griffe for analysis
    parser = GriffePythonParser()

    transformer = PythonTransformer()
    strategy = PythonFingerprintStrategy()

    return StitcherApp(
        root_path=project_root,
        parser=parser,
        transformer=transformer,
        fingerprint_strategy=strategy,
        interaction_handler=handler,
    )
~~~~~

### 下一步建议

这个修复应该能让之前失败的测试 `test_command_fails_gracefully_outside_workspace` 成功通过。我们已经确保了系统在无效环境中会明确且优雅地失败。

现在，我们重新回到宏观计划的正轨，处理最高优先级的架构债务：

- **完成依赖注入 (P0)**: 在 `StitcherApp` 组装阶段创建 `URIGeneratorProtocol` 的单例，并将其通过构造函数注入到所有需要它的下游组件（如 `SidecarTransformer`, `Planner`, `Adapter`）中，彻底消除硬编码的 `PythonURIGenerator()` 实例化。
