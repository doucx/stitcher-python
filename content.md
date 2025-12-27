您分析得非常准确，这正是一个典型的循环导入（circular import）问题，由我上一步的重构引入。我深表歉歉。

问题的根源在于我创建的依赖关系环：
1.  `stitcher.common.__init__.py` 尝试导入 `bus` 实例 (`from .messaging.bus import bus`)。
2.  为了加载 `bus`，Python 开始执行 `stitcher.common.messaging.bus.py`。
3.  在 `bus.py` 内部，代码又尝试从 `stitcher.common` 导入 `stitcher_nexus` (`from stitcher.common import stitcher_nexus as nexus`)。
4.  此时，`stitcher.common.__init__.py` 还没有执行完毕（它正停在导入 `bus` 的那一步），因此 `stitcher_nexus` 尚未在 `stitcher.common` 模块的命名空间中定义，导致了 `ImportError`。

**一句话概括：`common` 依赖 `bus`，而 `bus` 又反过来依赖 `common`，形成了死锁。**

正确的做法是打破这个循环。`MessageBus` 类不应该知道 `nexus` 实例来自哪里；它只需要一个实现了 `get` 方法的对象即可。我们将采用依赖注入的方式来解决这个问题：
1.  修改 `MessageBus` 类，让它的构造函数 (`__init__`) 接收一个 `nexus` 实例作为参数。
2.  将 `bus` 单例的创建过程从 `bus.py` 文件中移出。
3.  在 `stitcher.common.__init__.py` 中，先创建 `stitcher_nexus` 实例，然后创建 `bus` 实例，并将 `stitcher_nexus` *注入* 到 `bus` 中。
4.  最后，修复因 `MessageBus` 构造函数变更而受影响的测试代码。

这样，依赖关系就变成了单向的：`stitcher.common` -> `MessageBus` 类，循环被彻底打破。

## [WIP] fix: 通过依赖注入解决 circular import 问题

### 错误分析
上一个计划在 `stitcher-common` 中创建 `stitcher_nexus` 实例，但导致了 `stitcher.common` 和其子模块 `messaging.bus` 之间的循环导入。原因是 `bus.py` 试图从一个尚未完全初始化的 `stitcher.common` 模块中导入 `stitcher_nexus`。

### 用户需求
修复由于循环导入导致的 `ImportError`，使测试能够正常运行。

### 评论
这是一个经典的架构问题。通过将 `MessageBus` 对 `nexus` 的依赖关系从“拉取”（在模块内部导入）改为“推送”（通过构造函数注入），我们遵循了控制反转原则，不仅解决了循环导入，还使 `MessageBus` 组件更加解耦和易于测试。

### 目标
1.  重构 `MessageBus` 类，使其在构造时接收一个 `nexus` 依赖。
2.  在 `stitcher.common.__init__.py` 中统一创建和组装 `stitcher_nexus` 和 `bus` 单例。
3.  修复受 `MessageBus` 构造函数变更影响的单元测试。

### 基本原理
我们将把 `stitcher.common.__init__.py` 作为这两个核心单例的“组合根”。
1.  `MessageBus` 类将被修改为纯粹的业务逻辑，其依赖项 (`nexus`) 通过构造函数提供。
2.  `bus.py` 文件将只定义 `MessageBus` 类，不再创建全局单例 `bus`。
3.  `stitcher.common.__init__.py` 文件将首先创建 `stitcher_nexus`，然后导入 `MessageBus` *类*，最后用 `stitcher_nexus` 实例化 `MessageBus` 类来创建 `bus` 单例。这个清晰的、单向的创建流程将彻底消除循环依赖。

### 标签
#intent/fix #flow/ready #priority/critical #comp/common #scope/core #ai/instruct #task/domain/architecture #task/object/dependency-injection #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 重构 `MessageBus` 以接受依赖注入

我们将修改 `MessageBus` 类，使其不再从全局导入 `nexus`，而是在初始化时接收它。同时，我们将 `bus` 单例的创建移出此文件。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/messaging/bus.py
~~~~~
~~~~~python
from typing import Any, Optional, Union

from needle.pointer import SemanticPointer
from .protocols import Renderer


class MessageBus:
    def __init__(self, nexus_instance: Any):
        self._renderer: Optional[Renderer] = None
        self._nexus = nexus_instance

    def set_renderer(self, renderer: Renderer):
        self._renderer = renderer

    def _render(
        self, level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any
    ) -> None:
        if not self._renderer:
            return

        # Resolve the pointer to a string template using the injected nexus
        template = self._nexus.get(msg_id)

        # Format the final message
        try:
            message = template.format(**kwargs)
        except KeyError:
            # Fallback for formatting errors
            message = f"<formatting_error for '{str(msg_id)}'>"

        self._renderer.render(message, level)

    def info(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("info", msg_id, **kwargs)

    def success(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("success", msg_id, **kwargs)

    def warning(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("warning", msg_id, **kwargs)

    def error(self, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
        self._render("error", msg_id, **kwargs)

    def render_to_string(
        self, msg_id: Union[str, SemanticPointer], **kwargs: Any
    ) -> str:
        template = self._nexus.get(msg_id)
        try:
            return template.format(**kwargs)
        except KeyError:
            return f"<formatting_error for '{str(msg_id)}'>"


# The global singleton is now created in stitcher.common.__init__
~~~~~

#### Acts 2: 在 `stitcher-common` 中组装单例，打破循环

现在，`__init__.py` 将负责创建所有核心单例并正确地将它们连接在一起。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from pathlib import Path
from needle.nexus import OverlayNexus
from needle.loaders.fs_loader import FileSystemLoader
from .messaging.bus import MessageBus

# --- Composition Root for Stitcher's Core Services ---

# 1. Create the loader instance.
stitcher_loader = FileSystemLoader()

# 2. Create the nexus instance, injecting the loader.
stitcher_nexus = OverlayNexus(loaders=[stitcher_loader])

# 3. Create the bus instance, injecting the nexus.
bus = MessageBus(nexus_instance=stitcher_nexus)

# 4. Auto-register built-in assets for the 'common' package.
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

#### Acts 3: 修复 `test_message_bus` 单元测试

由于 `MessageBus` 的构造函数已更改，我们需要更新其单元测试以提供所需的 `nexus` 依赖。

~~~~~act
patch_file
packages/stitcher-common/tests/test_message_bus.py
~~~~~
~~~~~python.old
@pytest.fixture
def test_bus():
    return MessageBus()


def test_bus_does_not_fail_without_renderer(test_bus: MessageBus):
~~~~~
~~~~~python.new
class MockNexus:
    def get(self, key, **kwargs):
        return str(key)


@pytest.fixture
def test_bus():
    # Provide a mock nexus instance to satisfy the constructor
    return MessageBus(nexus_instance=MockNexus())


def test_bus_does_not_fail_without_renderer(test_bus: MessageBus):
~~~~~

### 下一步建议
这次的修复更加深入和彻底。在应用此计划后，循环导入问题应该会完全解决。请重新运行测试套件。如果一切顺利，我们就可以进入 `[COMMIT]` 阶段，完成这次重要的重构。
