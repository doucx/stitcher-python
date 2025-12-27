这是对测试工具链的一次重要清理。我们将消除命名混淆，使测试工具与 `pyneedle` 的 `Nexus` 概念保持一致，并修复因 `MessageBus` 构造函数变更而导致的 `SpyBus` 初始化错误。

## [WIP] fix: 重构测试工具以匹配 Nexus 语义和依赖注入

### 错误分析
1.  **命名混淆**: `MockNeedle` 类名过时且具有误导性，它实际上模拟的是 `Nexus` 组件。且它缺少 `get` 方法（只有 `_mock_get`），导致 `MessageBus` 调用失败。
2.  **SpyBus 初始化失败**: `SpyBus` 内部实例化的 `PatchedMessageBus` 继承自 `MessageBus`，但没有在初始化时传入必须的 `nexus_instance` 参数，导致所有依赖 `SpyBus` 的集成测试全部崩溃。

### 用户需求
1.  将 `MockNeedle` 重命名为 `MockNexus`，并确保其提供 `nexus.get` 接口。
2.  修复 `SpyBus` 以适应依赖注入。
3.  修复所有相关测试错误。

### 评论
这次重构将彻底理顺测试基础设施。`MockNexus` 将成为一个真正的、符合接口规范的模拟对象，而 `SpyBus` 将通过组合这个模拟对象来正确地实例化被测系统。

### 目标
1.  重构 `stitcher-test-utils`:
    *   将 `needle.py` 重命名为 `nexus.py`。
    *   将 `MockNeedle` 类重命名为 `MockNexus`，并实现标准的 `.get()` 方法。
2.  修复 `SpyBus`:
    *   在 `SpyBus` 初始化时，创建一个 `MockNexus` 实例并注入到内部的 `PatchedMessageBus` 中。
3.  更新所有测试引用:
    *   更新 `stitcher-common` 的单元测试。
    *   更新 `stitcher-test-utils` 的导出。

### 基本原理
我们将 `MockNexus` 定义为一个简单的字典包装器，其 `.get()` 方法执行查找或回退到键本身。`SpyBus` 作为测试替身，不需要真实的 `Nexus` 逻辑，只需要一个能让 `MessageBus` 正常运行且不报错的桩 (Stub)。因此，在 `SpyBus` 内部注入一个空的 `MockNexus` 是最干净的解决方案。

### 标签
#intent/fix #intent/refine #flow/ready #priority/critical #comp/tests #scope/dx #ai/instruct #task/domain/testing #task/object/test-doubles #task/action/rename #task/state/continue

---

### Script

#### Acts 1: 重命名并重构 Mock 工具 (Needle -> Nexus)

我们将 `needle.py` 移动并重构为 `nexus.py`，实现 `MockNexus` 类。

~~~~~act
run_command
~~~~~
~~~~~bash
mv packages/stitcher-test-utils/src/stitcher/test_utils/needle.py packages/stitcher-test-utils/src/stitcher/test_utils/nexus.py
~~~~~

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/nexus.py
~~~~~
~~~~~python
from contextlib import contextmanager
from typing import Dict, Any


class MockNexus:
    def __init__(self, templates: Dict[str, str]):
        self._templates = templates

    def get(self, key: Any, **kwargs: Any) -> str:
        """Standard Nexus interface implementation."""
        key_str = str(key)
        return self._templates.get(key_str, key_str)

    @contextmanager
    def patch(self, monkeypatch: Any):
        """
        Legacy patch method.
        Prefer constructor injection (Dependency Injection) where possible.
        This patches the 'stitcher_nexus' used by the global bus if needed.
        """
        target_path = "stitcher.common.stitcher_nexus.get"
        try:
            monkeypatch.setattr(target_path, self.get)
            yield
        finally:
            pass
~~~~~

#### Acts 2: 修复 `SpyBus` 初始化逻辑

`SpyBus` 需要为它内部的 `MessageBus` 提供一个 `nexus` 实例。我们将给它一个默认的 `MockNexus`。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
from stitcher.common.messaging.bus import MessageBus
from stitcher.common.messaging.protocols import Renderer
from needle.pointer import SemanticPointer

# Store the original bus instance from stitcher.common
~~~~~
~~~~~python.new
from stitcher.common.messaging.bus import MessageBus
from stitcher.common.messaging.protocols import Renderer
from needle.pointer import SemanticPointer
from .nexus import MockNexus

# Store the original bus instance from stitcher.common
~~~~~
~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()
        # Create a new bus instance that uses our special renderer
        self._test_bus = PatchedMessageBus()
        self._test_bus.set_renderer(self._spy_renderer)
~~~~~
~~~~~python.new
class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()
        # Create a new bus instance that uses our special renderer.
        # We inject a MockNexus because SpyBus doesn't care about the actual text templates,
        # it only records the semantic IDs and params.
        self._test_bus = PatchedMessageBus(nexus_instance=MockNexus({}))
        self._test_bus.set_renderer(self._spy_renderer)
~~~~~

#### Acts 3: 更新 `stitcher-test-utils` 的导出

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py
~~~~~
~~~~~python.old
from .bus import SpyBus
from .needle import MockNeedle
from .workspace import WorkspaceFactory

__all__ = ["SpyBus", "MockNeedle", "WorkspaceFactory"]
~~~~~
~~~~~python.new
from .bus import SpyBus
from .nexus import MockNexus
from .workspace import WorkspaceFactory

__all__ = ["SpyBus", "MockNexus", "WorkspaceFactory"]
~~~~~

#### Acts 4: 修复 `stitcher-common` 单元测试

更新测试代码以使用新的类名和导入路径。

~~~~~act
write_file
packages/stitcher-common/tests/test_message_bus.py
~~~~~
~~~~~python
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

### 下一步建议
这次重构应该解决了所有由于 API 变更、命名混淆和初始化参数缺失导致的测试失败。现在，测试基础设施与新的架构设计是同步的。请运行全部测试。如果全部通过，我将生成提交计划。
