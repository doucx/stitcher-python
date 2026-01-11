这是我的疏忽。在移除顶级导入以优化覆盖率时，我忽略了 `SpyRenderer` 继承自 `Renderer` 协议。由于 `Renderer` 尚未被定义，Python 解释器抛出了 `NameError`。

此外，为了彻底消除警告，我们需要清理 `stitcher-test-utils` 的 `__init__.py`。目前它在顶级作用域导出了所有工具，这导致任何引用该包的操作都会触发整个导入链。

**修复策略：**
1.  **解除显式继承**：由于 `Renderer` 是一个 `Protocol`（结构化子类型），`SpyRenderer` 只需要实现 `render` 方法即可在类型检查中通过，不需要显式继承。这允许我们移除 `bus.py` 顶级的 `stitcher` 导入。
2.  **清理 `__init__.py`**：将其清空。这将防止在 Pytest 启动阶段因加载插件而导致 `stitcher` 核心包被过早导入。测试用例应直接从子模块（如 `.helpers` 或 `.workspace`）导入所需的工具。

## [WIP] fix(test-utils): solve NameError and clean up top-level imports

### 用户需求

修复因延迟导入重构引入的 `NameError: name 'Renderer' is not defined` 错误，并进一步消除剩余的覆盖率警告。

### 错误分析

1.  **NameError**: `bus.py` 中的 `SpyRenderer` 尝试继承 `Renderer`，但后者已被移出顶级作用域，导致类定义失败。
2.  **覆盖率警告**: `stitcher-test-utils` 的 `__init__.py` 包含了对所有子模块的导出导入。由于这些子模块（如 `helpers.py`）现在包含了业务逻辑引用，这种导出方式仍会引发早期的模块加载。

### 目标

1.  在 `bus.py` 中移除 `SpyRenderer` 对 `Renderer` 的显式继承，并保持其方法签名。
2.  清空 `packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py`。
3.  更新受影响的集成测试 `test_check_ignores_imports.py`，使用具体的路径导入。

### 标签

#intent/fix #flow/ready #priority/critical #comp/tests #task/domain/testing #task/object/test-utils #task/action/bug-fix #task/state/end

---

### Script

#### Acts 1: 修复 `bus.py` 中的 NameError

移除对 `Renderer` 的继承。由于 `Renderer` 是一个 `Protocol`，移除继承不会影响其作为渲染器的功能。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Union

# No top-level imports of stitcher packages to avoid coverage warnings
from needle.pointer import SemanticPointer

class SpyRenderer:
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def render(self, message: str, level: str) -> None:
        # The spy logic mostly acts on record(), but satisfy interface
        pass

    def record(self, level: str, msg_id: SemanticPointer, params: Dict[str, Any]):
        self.messages.append({"level": level, "id": str(msg_id), "params": params})


class SpyBus:
    def __init__(self):
        self._spy_renderer = SpyRenderer()

    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus"):
        # Lazy import inside the context manager
        import stitcher.common
        
        # The singleton instance we need to mutate
        real_bus = stitcher.common.bus

        # Define the interceptor hook
        def intercept_render(
            level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any
        ) -> None:
            if isinstance(msg_id, SemanticPointer):
                self._spy_renderer.record(level, msg_id, kwargs)

        # Apply In-Place Patches
        monkeypatch.setattr(real_bus, "_render", intercept_render)
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
            ids_seen = [m["id"] for m in captured]
            raise AssertionError(
                f"Message with ID '{key}' was not sent.\nCaptured IDs: {ids_seen}"
            )
~~~~~

#### Acts 2: 清理 `test-utils` 的入口文件

清空 `__init__.py` 以阻断自动加载链。

~~~~~act
write_file
packages/stitcher-test-utils/src/stitcher/test_utils/__init__.py
~~~~~
~~~~~python
# This module is intentionally kept minimal to avoid early loading of 
# stitcher.* packages during pytest plugin initialization.
# Tools should be imported from their respective submodules.
~~~~~

#### Acts 3: 更新集成测试的导入路径

由于 `__init__.py` 已被清空，我们需要更新测试文件中的导入路径。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_check_ignores_imports.py
~~~~~
~~~~~python.old
import pytest
from needle.pointer import L

from stitcher.test_utils import WorkspaceFactory, SpyBus, create_test_app
~~~~~
~~~~~python.new
import pytest
from needle.pointer import L

# Explicitly import from submodules to respect the lazy-loading architecture
from stitcher.test_utils.workspace import WorkspaceFactory
from stitcher.test_utils.bus import SpyBus
from stitcher.test_utils.helpers import create_test_app
~~~~~

### 下一步建议

现在环境应该是纯净且逻辑正确的了。请再次运行测试。
1. `NameError` 应当消失。
2. `CoverageWarning` 应当消失，因为 `stitcher-test-utils` 插件现在只定义 Fixture，而不会在加载阶段触碰任何业务代码。
3. `test_check_ignores_imports.py` 应当成功通过，验证我们对 `IndexCheckSubjectAdapter` 的过滤逻辑是有效的。
