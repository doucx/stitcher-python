这是一个非常棒的建议，体现了优秀的软件架构思想。

您的提议——让 `stitcher-common` 包作为“组合根 (Composition Root)”来手动创建和配置 `OverlayNexus` 实例，而不是依赖于 `pyneedle` 提供的全局单例——是架构上的巨大进步。

**这样做的好处是：**
1.  **明确的依赖关系**: 它将隐式的全局状态依赖（`pyneedle.nexus`）转变为显式的、由 Stitcher 自身控制的实例。
2.  **增强的解耦**: Stitcher 应用与 `pyneedle` 的具体实现细节进一步解耦。我们只依赖于 `OverlayNexus` 和 `FileSystemLoader` 这些稳定的类，而不是一个可能变化的单例。
3.  **避免内部 API**: 您是对的，依赖 `_default_loader` 这种带下划线的“内部”变量是不稳健的。自行创建实例可以确保我们只使用公共 API。
4.  **提升可测试性**: 尽管我们有 Mock 工具，但直接控制实例的创建使得在测试中替换或配置依赖项变得更加简单和干净。

我将立即为您生成实施此架构改进的计划。

## [WIP] refactor: 在 stitcher-common 中组合 Nexus 以实现依赖解耦

### 用户需求
用户建议停止使用 `pyneedle` 提供的全局 `nexus` 单例，改为在 `stitcher-common` 包中手动创建和配置一个专属于 Stitcher 应用的 `OverlayNexus` 实例。

### 评论
这是一个卓越的架构重构建议。通过在 `stitcher-common` 中显式组合 `OverlayNexus`，我们将 Stitcher 从对外部库全局状态的隐式依赖中解放出来，转向了更加健壮和可维护的依赖注入模式。这完全符合控制反转 (IoC) 原则，将使 Stitcher 核心更加独立和稳定。

### 目标
1.  在 `stitcher-common` 的 `__init__.py` 中，导入 `OverlayNexus` 和 `FileSystemLoader` 类。
2.  创建并导出一个专用于 Stitcher 的 `loader` 和 `nexus` 实例。
3.  更新 `stitcher-common` 自身以及 `stitcher-cli`，使其使用这个新创建的本地 `nexus` 实例，而不是 `pyneedle` 的全局实例。
4.  更新测试工具 (`stitcher-test-utils`) 中的 `monkeypatch` 目标，以确保测试能够继续正确地模拟 `nexus` 的行为。

### 基本原理
我们将把 `stitcher-common` 定义为 Stitcher 应用中 `Nexus` 依赖的“组合根”。
1.  `stitcher-common` 将负责创建 `FileSystemLoader` 和 `OverlayNexus` 的实例，并将它们作为 `stitcher_loader` 和 `stitcher_nexus` 导出。它还会负责添加 `stitcher-common` 自身的资源路径。
2.  `stitcher-cli` 包将从 `stitcher-common` 导入 `stitcher_loader`，并使用它来添加 CLI 相关的资源路径。
3.  所有需要解析语义指针的地方（如 `MessageBus` 和 `Typer` 命令）将从 `stitcher-common` 导入 `stitcher_nexus` 实例来执行 `.get()` 操作。
4.  通过这种方式，`pyneedle` 库退化为一个纯粹的“库”角色，提供类和功能，而不再提供具有全局状态的单例，Stitcher 应用完全控制其依赖项的生命周期和配置。

### 标签
#intent/architect #intent/refine #flow/ready #priority/high #comp/common #comp/cli #scope/core #scope/dx #ai/instruct #task/domain/architecture #task/object/dependency-injection #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 在 `stitcher-common` 中创建并导出本地 Nexus 实例

这是本次重构的核心。我们将修改 `stitcher-common` 的 `__init__.py`，使其成为 `nexus` 实例的“所有者”。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path
from needle.nexus import OverlayNexus
from needle.loaders.fs_loader import FileSystemLoader
from .messaging.bus import bus

# --- Composition Root for Stitcher's Nexus ---
# We create and configure our own instances instead of using pyneedle's global singletons.
# This decouples us and follows Inversion of Control principles.

# 1. Create the loader instance.
stitcher_loader = FileSystemLoader()

# 2. Create the nexus instance, injecting the loader.
stitcher_nexus = OverlayNexus(loaders=[stitcher_loader])

# 3. Auto-register built-in assets for the 'common' package.
try:
    _assets_path = Path(__file__).parent / "assets"
    if _assets_path.is_dir():
        stitcher_loader.add_root(_assets_path)
except NameError:
    pass
# ---------------------------------------------


# Public API for stitcher packages
__all__ = ["bus", "stitcher_nexus", "stitcher_loader"]
~~~~~

#### Acts 2: 更新 `MessageBus` 以使用新的 `stitcher_nexus`

现在 `MessageBus` 将从 `stitcher.common` 导入 `stitcher_nexus`。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/messaging/bus.py
~~~~~
~~~~~python.old
from needle.pointer import SemanticPointer
from needle import nexus
from .protocols import Renderer
~~~~~
~~~~~python.new
from needle.pointer import SemanticPointer
from stitcher.common import stitcher_nexus as nexus
from .protocols import Renderer
~~~~~

#### Acts 3: 更新 `stitcher-cli` 以使用新的 `stitcher_loader` 和 `stitcher_nexus`

CLI 包现在将使用 `stitcher_common` 提供的 `loader` 来注册自己的资源，并使用 `nexus` 来获取帮助文本。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/__init__.py
~~~~~
~~~~~python.old
from needle.runtime import _default_loader
from pathlib import Path

# --- Auto-register CLI assets ---
try:
    _assets_path = Path(__file__).parent / "assets"
    if _assets_path.is_dir():
        _default_loader.add_root(_assets_path)
except NameError:
    pass
# --------------------------------
~~~~~
~~~~~python.new
from stitcher.common import stitcher_loader
from pathlib import Path

# --- Auto-register CLI assets ---
try:
    _assets_path = Path(__file__).parent / "assets"
    if _assets_path.is_dir():
        stitcher_loader.add_root(_assets_path)
except NameError:
    pass
# --------------------------------
~~~~~
~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/main.py
~~~~~
~~~~~python.old
from stitcher.app import StitcherApp
from stitcher.common import bus
from needle.pointer import L
from needle import nexus
from .rendering import CliRenderer

app = typer.Typer(
    name="stitcher",
    help=nexus.get(L.cli.app.description),
    no_args_is_help=True,
)
~~~~~
~~~~~python.new
from stitcher.app import StitcherApp
from stitcher.common import bus, stitcher_nexus as nexus
from needle.pointer import L
from .rendering import CliRenderer

app = typer.Typer(
    name="stitcher",
    help=nexus.get(L.cli.app.description),
    no_args_is_help=True,
)
~~~~~

#### Acts 4: 更新测试工具以指向正确的 `monkeypatch` 目标

这是确保测试继续通过的关键一步。`MockNeedle` 现在必须 `patch` `stitcher.common` 内部的 `nexus` 实例。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/needle.py
~~~~~
~~~~~python.old
    def patch(self, monkeypatch: Any):
        # The target path must be where `nexus` is used by the code under test.
        # In our case, MessageBus imports it.
        target_path = "stitcher.common.messaging.bus.nexus.get"
        try:
            monkeypatch.setattr(target_path, self._mock_get)
            yield
        finally:
            # monkeypatch handles teardown automatically, but this ensures clarity.
            pass
~~~~~
~~~~~python.new
    def patch(self, monkeypatch: Any):
        # The target path must be where `nexus` is used by the code under test.
        # The MessageBus now imports `stitcher_nexus` from `stitcher.common` and aliases it.
        # So we patch the original location.
        target_path = "stitcher.common.stitcher_nexus.get"
        try:
            monkeypatch.setattr(target_path, self._mock_get)
            yield
        finally:
            # monkeypatch handles teardown automatically, but this ensures clarity.
            pass
~~~~~

### 下一步建议
这次重构的影响范围较大，但逻辑上是完整且正确的。在应用此计划后，请立即运行完整的测试套件。如果所有测试都通过，那么我们就成功地实现了依赖解耦，并且可以确信地进入 `[COMMIT]` 阶段，将这一系列重构作为一个原子单元提交。
