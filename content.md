## [WIP] feat: 阶段二 Part 2 - 适配 MessageBus 至 Operator 协议

### 用户需求
1.  **更新 MessageBus**: 修改 `MessageBus` 类，使其依赖注入的对象从 `NexusProtocol` 变更为 `OperatorProtocol`。这意味着将内部所有的 `.get()` 调用替换为 `__call__()` (即直接调用实例)。
2.  **清理组合根**: 在 `stitcher-common` 中移除临时的 `StitcherOperatorProxy`，直接传递动态解析函数。
3.  **修复相关测试**: 如果单元测试中使用了 MockNexus，需要将其更新为 MockOperator。

### 评论
这将完成架构链条的最后一环。至此，从底层的 `FileSystemOperator` 到顶层的 `MessageBus`，全都运行在统一的函数式算子接口之上。

### 目标
1.  修改 `stitcher/common/messaging/bus.py`。
2.  清理 `stitcher/common/__init__.py`。
3.  更新 `stitcher/common/tests/unit/test_message_bus.py`。

### 基本原理
*   **依赖倒置**: `MessageBus` 不应关心它是从哪里获取消息模板的，它只需要一个 `Callable[[SemanticPointer], str]`。这正是 `OperatorProtocol` 的定义。
*   **代码简化**: `self._nexus.get(msg_id)` -> `self._operator(msg_id)`。

### 标签
#intent/refine #flow/ready #priority/high #comp/runtime #comp/common #concept/message-bus #scope/core #ai/instruct #task/domain/core #task/object/message-bus #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: 更新 MessageBus 依赖

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/messaging/bus.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
from typing import Any, Optional, Union, Callable

from needle.pointer import SemanticPointer
from .protocols import Renderer


class MessageBus:
    def __init__(self, operator: Callable[[Union[str, SemanticPointer]], str]):
        self._renderer: Optional[Renderer] = None
        self._operator = operator

    def set_renderer(self, renderer: Renderer):
        self._renderer = renderer

    def _render(
        self, level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any
    ) -> None:
        if not self._renderer:
            return

        # Resolve the pointer to a string template using the injected operator
        template = self._operator(msg_id)
        
        # Handle lookup failure gracefully
        if template is None:
            template = str(msg_id)

        # Format the final message
        try:
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/messaging/bus.py
~~~~~
~~~~~python.old
    def render_to_string(
        self, msg_id: Union[str, SemanticPointer], **kwargs: Any
    ) -> str:
        template = self._nexus.get(msg_id)
        try:
            return template.format(**kwargs)
        except KeyError:
            return f"<formatting_error for '{str(msg_id)}'>"
~~~~~
~~~~~python.new
    def render_to_string(
        self, msg_id: Union[str, SemanticPointer], **kwargs: Any
    ) -> str:
        template = self._operator(msg_id)
        if template is None:
            return str(msg_id)
            
        try:
            return template.format(**kwargs)
        except KeyError:
            return f"<formatting_error for '{str(msg_id)}'>"
~~~~~

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/messaging/bus.stitcher.yaml
~~~~~
~~~~~yaml.old
"MessageBus": |-
  Coordinates message resolution and rendering.
"MessageBus.__init__": |-
  Initializes the bus with a nexus instance for message lookup.
"MessageBus.error": |-
~~~~~
~~~~~yaml.new
"MessageBus": |-
  Coordinates message resolution and rendering.
"MessageBus.__init__": |-
  Initializes the bus with an operator (callable) for message lookup.
"MessageBus.error": |-
~~~~~

#### Acts 2: 清理组合根

移除 Proxy，传递闭包。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python.old
# To adapt to MessageBus which expects an object with `.get()` (Legacy) or `__call__` (New),
# we need to make sure MessageBus is updated. 
# For now, let's create a proxy object that acts as the "Stitcher Operator".

class StitcherOperatorProxy:
    def __call__(self, key):
        renderer = get_current_renderer()
        return renderer(key)
    
    # Legacy compat if MessageBus still calls get()
    def get(self, key):
        return self.__call__(key)

stitcher_operator = StitcherOperatorProxy()
bus = MessageBus(nexus_instance=stitcher_operator)
~~~~~
~~~~~python.new
# 4. Message Bus
# We pass a lambda that delegates to the current renderer.
# This ensures that we always use the latest operator from the cache (or rebuild it if cache cleared).
# Using a simple function instead of a Proxy class.

def stitcher_operator(key):
    renderer = get_current_renderer()
    return renderer(key)

bus = MessageBus(operator=stitcher_operator)
~~~~~

#### Acts 3: 更新测试

更新 `test_message_bus.py` 以反映新的构造函数和 `MockNexus` 的移除。

~~~~~act
patch_file
packages/stitcher-common/tests/unit/test_message_bus.py
~~~~~
~~~~~python.old
import pytest
from stitcher.common.messaging.bus import MessageBus
from stitcher.common.messaging.protocols import Renderer
from needle.pointer import L
from stitcher.test_utils.nexus import MockNexus


class MockRenderer(Renderer):
    def __init__(self):
        self.messages = []

    def render(self, message: str, level: str) -> None:
        self.messages.append({"level": level, "message": message})


def test_bus_does_not_fail_without_renderer():
    # Arrange: A bus with a basic mock nexus
    bus = MessageBus(nexus_instance=MockNexus({}))
    try:
        # Act
        bus.info("some.id")
    except Exception as e:
        pytest.fail(f"MessageBus raised an exception without a renderer: {e}")


def test_bus_forwards_to_renderer():
    # Arrange
    mock_renderer = MockRenderer()
    # Directly inject a MockNexus instance configured for this test
    mock_nexus = MockNexus({"greeting": "Hello {name}"})
    bus = MessageBus(nexus_instance=mock_nexus)
    bus.set_renderer(mock_renderer)

    # Act
    bus.info(L.greeting, name="World")
    bus.success(L.greeting, name="Stitcher")

    # Assert
    assert len(mock_renderer.messages) == 2
    assert mock_renderer.messages[0] == {"level": "info", "message": "Hello World"}
    assert mock_renderer.messages[1] == {
        "level": "success",
        "message": "Hello Stitcher",
    }


def test_bus_identity_fallback():
    # Arrange
    mock_renderer = MockRenderer()
    # Inject a MockNexus with no templates to test fallback
    mock_nexus = MockNexus({})
    bus = MessageBus(nexus_instance=mock_nexus)
    bus.set_renderer(mock_renderer)

    # Act
    bus.info(L.nonexistent.key)

    # Assert
    assert len(mock_renderer.messages) == 1
    assert mock_renderer.messages[0] == {"level": "info", "message": "nonexistent.key"}
~~~~~
~~~~~python.new
import pytest
from stitcher.common.messaging.bus import MessageBus
from stitcher.common.messaging.protocols import Renderer
from needle.pointer import L
from needle.operators import DictOperator


class MockRenderer(Renderer):
    def __init__(self):
        self.messages = []

    def render(self, message: str, level: str) -> None:
        self.messages.append({"level": level, "message": message})


def test_bus_does_not_fail_without_renderer():
    # Arrange: A bus with a simple DictOperator
    bus = MessageBus(operator=DictOperator({}))
    try:
        # Act
        bus.info("some.id")
    except Exception as e:
        pytest.fail(f"MessageBus raised an exception without a renderer: {e}")


def test_bus_forwards_to_renderer():
    # Arrange
    mock_renderer = MockRenderer()
    # Use DictOperator as the message source
    operator = DictOperator({"greeting": "Hello {name}"})
    bus = MessageBus(operator=operator)
    bus.set_renderer(mock_renderer)

    # Act
    bus.info(L.greeting, name="World")
    bus.success(L.greeting, name="Stitcher")

    # Assert
    assert len(mock_renderer.messages) == 2
    assert mock_renderer.messages[0] == {"level": "info", "message": "Hello World"}
    assert mock_renderer.messages[1] == {
        "level": "success",
        "message": "Hello Stitcher",
    }


def test_bus_identity_fallback():
    # Arrange
    mock_renderer = MockRenderer()
    # Missing key in DictOperator returns None -> Bus falls back to identity
    operator = DictOperator({})
    bus = MessageBus(operator=operator)
    bus.set_renderer(mock_renderer)

    # Act
    bus.info(L.nonexistent.key)

    # Assert
    assert len(mock_renderer.messages) == 1
    assert mock_renderer.messages[0] == {"level": "info", "message": "nonexistent.key"}
~~~~~

#### Acts 4: 清理 Test Utils

由于 `MockNexus` 不再被需要（`DictOperator` 已完美替代其功能），我们应将其从 `stitcher-test-utils` 中移除，保持代码库整洁。假设该文件存在于 `packages/stitcher-test-utils/src/stitcher/test_utils/nexus.py` (基于之前的导入推断)。

（注：如果不确定文件是否存在，可以先不删，或者用 `check_files_exist` 确认。为了安全起见，我会先尝试列出文件）

~~~~~act
list_files
packages/stitcher-test-utils/src/stitcher/test_utils
~~~~~

### 下一步建议
如果 Act 4 确认了 MockNexus 文件的存在，我将在下一个计划中将其删除。否则，我们将进入 **阶段三**，即实现高阶算子 `ThemeOperator` 并全面推广新架构。
另外，注意 `stitcher-common/__init__.py` 中的 `stitcher_loader` 被暂时移除了。如果项目中还有代码依赖它来进行写入操作（如 `init` 命令），它们现在会报错。我们需要在后续计划中重新引入**写入能力**。这是新架构尚未完全覆盖的部分（目前只实现了只读管道）。
