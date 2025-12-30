简要回答
测试失败的根本原因是测试工具 `SpyBus` 试图通过 Monkeypatch 替换 `stitcher.common.bus` 模块属性，但应用代码（如 `basics.py`, `check.py`）使用了 `from stitcher.common import bus` 直接导入了对象引用，导致测试中的 Patch 无法影响已被导入的一致性引用。解决方案是修改 `SpyBus.patch`，改为对 `stitcher.common.bus` **单例实例本身** 的方法进行 Monkeypatch (In-place Patching)。

## [WIP] fix(tests): 修复 SpyBus 无法拦截已导入 Bus 实例消息的问题

### 错误分析
所有失败的测试都表现为 `AssertionError: Message with ID '...' was not sent.`。

1.  **架构原因**: `stitcher` 的 CLI 和 Runner 模块（如 `check.py`, `pump.py`）通常使用 `from stitcher.common import bus` 导入消息总线。这意味着它们持有的是 `bus` 对象在导入时刻的引用。
2.  **测试工具缺陷**: 现有的 `SpyBus.patch` 实现使用了 `monkeypatch.setattr(target, self._test_bus)`。这仅仅修改了 `stitcher.common` 模块上的 `bus` 属性指向。
3.  **冲突**: 对于那些在 Patch 之前已经导入了 `bus` 的模块，它们仍然指向旧的 `MessageBus` 实例。因此，当代码执行 `bus.success(...)` 时，调用的是未被 Mock 的旧实例，消息从未到达 `SpyBus` 的记录器，导致断言失败。
4.  **解决方案**: 既然无法控制导入顺序或修改应用代码的导入方式，`SpyBus` 必须修改 **现有的单例对象** (In-place mutation)，而不是替换它。我们需要 Patch `bus` 实例的 `_render` 方法和 `_renderer` 属性。

### 用户需求
修复测试套件中的大量断言错误，确保系统集成测试能够正确捕获和验证通过消息总线发送的业务信号。

### 评论
这是一个经典的 Python单例测试陷阱。修复此问题将一次性绿化大部分集成测试。这种修改只涉及测试工具库 (`stitcher-test-utils`)，风险极低且收益巨大。

### 目标
1.  重构 `packages/stitcher-test-utils/src/stitcher/test_utils/bus.py`。
2.  移除 `PatchedMessageBus` 类（不再需要创建新实例）。
3.  修改 `SpyBus.patch` 方法，使其直接在 `stitcher.common.bus` 实例上挂载拦截逻辑。

### 基本原理
通过 `monkeypatch.setattr(instance, "method_name", new_method)`，我们可以临时修改运行时的单例实例行为。这样无论应用代码是通过 `from module import obj` 还是 `import module; module.obj` 访问该对象，调用的都是同一个被 Patch 过的方法。

### 标签
#intent/fix #flow/ready #priority/critical
#comp/tests #concept/state #scope/core
#ai/instruct
#task/domain/testing #task/object/spy-bus #task/action/refactor #task/state/begin

---

### Script

#### Acts 1: 重构 SpyBus 以支持实例级 Patch

我们将重写 `packages/stitcher-test-utils/src/stitcher/test_utils/bus.py`。新的实现将引入 `stitcher.common.bus` 单例，并定义一个拦截函数在 `patch` 上下文中替换单例的 `_render` 方法。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

# Import the actual singleton to patch it in-place
import stitcher.common
from stitcher.common.messaging.protocols import Renderer
from needle.pointer import SemanticPointer


class SpyRenderer(Renderer):
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def render(self, message: str, level: str) -> None:
        # The spy logic mostly acts on record(), but satisfy interface
        pass

    def record(self, level: str, msg_id: SemanticPointer, params: Dict[str, Any]):
        self.messages.append({"level": level, "id": str(msg_id), "params": params})


class SpyBus:
    """
    A Test Utility that spies on the global stitcher.common.bus singleton.
    
    Instead of replacing the bus instance (which fails if modules have already 
    imported the instance via 'from stitcher.common import bus'), 
    this utility patches the instance methods directly.
    """
    
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus"):
        """
        Patches the global bus to capture messages.
        
        Args:
            monkeypatch: The pytest monkeypatch fixture.
            target: Kept for compatibility with existing tests, but functionally 
                    we always patch the singleton instance found at stitcher.common.bus.
        """
        # The singleton instance we need to mutate
        real_bus = stitcher.common.bus

        # Define the interceptor hook
        def intercept_render(level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any) -> None:
            # 1. Capture the semantic pointer
            if isinstance(msg_id, SemanticPointer):
                self._spy_renderer.record(level, msg_id, kwargs)
            
            # 2. We deliberately DO NOT call the original _render logic here
            # because we don't want tests spamming stdout, and we don't 
            # want to rely on the real renderer (CLI) being configured.

        # Apply In-Place Patches using monkeypatch (handles restoration automatically)
        # 1. Swap the _render method to intercept calls
        monkeypatch.setattr(real_bus, "_render", intercept_render)
        
        # 2. Swap the _renderer to our spy (though intercept_render mostly handles logic,
        # setting this ensures internal checks for valid renderer pass if needed)
        monkeypatch.setattr(real_bus, "_renderer", self._spy_renderer)

        yield self

    def get_messages(self) -> List[Dict[str, Any]]:
        return self._spy_renderer.messages

    def assert_id_called(self, msg_id: SemanticPointer, level: Optional[str] = None):
        key = str(msg_id)
        found = False
        captured = self.get_messages()
        
        for msg in captured:
            if msg["id"] == key and (level is None or msg["level"] == level):
                found = True
                break

        if not found:
            # Enhanced error message for debugging
            ids_seen = [m["id"] for m in captured]
            raise AssertionError(
                f"Message with ID '{key}' was not sent.\n"
                f"Captured IDs: {ids_seen}"
            )
~~~~~

### 下一步建议
通过此修复，大部分由于 Mock 失效导致的 Message ID 断言错误应该会消失。建议在应用此更改后重新运行 `pytest` 确认效果。如果仍有其他类型的错误（如数据逻辑错误），则需要单独处理。
