好的，我们现在进行 **阶段一：功能平移** 的核心清理工作。

根据你的 `rg` 分析，我们需要在物理删除 `stitcher-bus` 之前，将所有业务代码和测试工具的引用安全地重定向到 `stitcher.common.bus`。

## [WIP] refactor(bus): 全局重定向与旧总线清理

### 错误分析
在执行替换前，我们需要解决一个**契约缺失**：
原有的 `stitcher-bus` 导出了 `stitcher_operator` (作为 `nexus`)，而我们之前创建的 `stitcher.common.bus` 仅导出了 `bus`。这会导致 CLI 层的多个命令因找不到 `nexus` 而崩溃。

### 用户需求
1.  完善 `stitcher.common.bus` 的导出接口，补齐 `stitcher_operator`。
2.  使用 `sed` 批量替换所有 Python 文件中的 import 路径。
3.  适配 `CliRenderer` 和 `SpyBus` 到 `pyneedle-bus` 的新协议（如 `RendererProtocol` 和 `present` 方法）。
4.  彻底删除 `packages/stitcher-bus`。

### 目标
1.  更新 `packages/stitcher-common/src/stitcher/common/bus.py`。
2.  批量修改 `application`, `cli`, `stubgen`, `common`, `test-utils` 中的引用。
3.  修复测试工具 `SpyBus` 的拦截逻辑（从 `_render` 切换到 `present`）。
4.  移除旧包目录。

### 基本原理
我们采用“最小惊讶原则”。通过在 `stitcher.common.bus` 中提供一个名为 `stitcher_operator` 的包装函数（它内部调用 `bus.render_to_string`），我们可以让上层 CLI 代码无需任何逻辑改动即可继续工作。对于测试工具 `SpyBus`，由于 `pyneedle.bus.FeedbackBus` 使用 `present` 作为分发入口，我们需要同步调整 Monkeypatch 的目标。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/common #comp/cli #comp/tests #scope/core
#ai/instruct
#task/domain/bus #task/object/refactoring #task/action/cleanup #task/state/continue

---

### Script

#### Acts 1: 完善 `stitcher-common` 的总线入口

补齐 `stitcher_operator` 导出，确保 CLI 的 `as nexus` 语法不被破坏。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/bus.py
~~~~~
~~~~~python.old
from pathlib import Path
from needle.bus import bus, message_store

# 1. 定位资产根目录 (在此前的 Acts 中已搬迁至此)
# assets 文件夹直接包含 needle/ 子目录
_assets_root = Path(__file__).parent / "assets"

# 2. 注册资产路径到 MessageStore
# 这允许 FeedbackBus 能够找到 L.check.file.fail 等指针对应的翻译模板
if _assets_root.exists():
    message_store.register_asset_root(_assets_root)

# 3. 导出全局单例，供下游业务使用
# 这里的 bus 实际上是 pyneedle.bus.feedback.FeedbackBus 的实例
__all__ = ["bus"]
~~~~~
~~~~~python.new
from pathlib import Path
from typing import Union, Any
from needle.bus import bus, message_store
from needle.spec import SemanticPointerProtocol

# 1. 定位资产根目录
_assets_root = Path(__file__).parent / "assets"

# 2. 注册资产路径到 MessageStore
if _assets_root.exists():
    message_store.register_asset_root(_assets_root)

# 3. 补齐 stitcher_operator (nexus) 接口
def stitcher_operator(key: Union[str, SemanticPointerProtocol], **kwargs: Any) -> str:
    """包装 pyneedle-bus 的渲染逻辑，保持与旧版 stitcher_operator 兼容。"""
    return bus.render_to_string(key, **kwargs)

# 4. 导出全局单例和操作符
__all__ = ["bus", "stitcher_operator"]
~~~~~

#### Acts 2: 批量替换 Import 路径

使用 `run_command` 和 `sed` 执行全局替换。

~~~~~act
run_command
~~~~~
~~~~~
# 替换 from stitcher.bus import ... 为 from stitcher.common.bus import ...
find packages -name "*.py" -exec sed -i 's/from stitcher\.bus/from stitcher\.common\.bus/g' {} +

# 替换 import stitcher.bus 为 import stitcher.common.bus
find packages -name "*.py" -exec sed -i 's/import stitcher\.bus/import stitcher\.common\.bus/g' {} +
~~~~~

#### Acts 3: 适配 CLI 渲染协议

`pyneedle-bus` 的协议名称为 `RendererProtocol`。

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/rendering.py
~~~~~
~~~~~python.old
import typer
from stitcher.common.bus.protocols import Renderer
from enum import Enum
~~~~~
~~~~~python.new
import typer
from needle.spec import RendererProtocol as Renderer
from enum import Enum
~~~~~

#### Acts 4: 重构 `SpyBus` 测试工具

`pyneedle-bus` 使用 `present` 方法进行消息呈现。我们需要修改 `SpyBus` 的拦截点。

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
# Import the actual singleton to patch it in-place
import stitcher.common
from stitcher.common.bus.protocols import Renderer
from needle.pointer import SemanticPointer
~~~~~
~~~~~python.new
# Import the actual singleton to patch it in-place
import stitcher.common
from needle.spec import RendererProtocol as Renderer
from needle.pointer import SemanticPointer
~~~~~
~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.bus.bus"):
        real_bus = stitcher.bus.bus

        def intercept_render(
            level: str, msg_id: Union[str, SemanticPointer], **kwargs: Any
        ) -> None:
            # This is the critical change. We now simulate the filtering logic
            # of the CliRenderer before deciding to record the message.
            renderer = real_bus._renderer
            if not renderer:
                return

            # Get the loglevel value from the actual renderer instance
            # Assumes the renderer has a 'loglevel_value' attribute.
            loglevel_value = getattr(renderer, "loglevel_value", 0)

            # Perform the filtering
            if LEVEL_MAP.get(level, 0) < loglevel_value:
                return

            # If the message passes the filter, record it.
            if isinstance(msg_id, SemanticPointer):
                self._spy_renderer.record(level, msg_id, kwargs)

        # We still patch _render, but now our patch is context-aware.
        monkeypatch.setattr(real_bus, "_render", intercept_render)

        # It's good practice to also set our spy renderer, though the logic
        # now primarily relies on intercepting _render.
        monkeypatch.setattr(real_bus, "_renderer", self._spy_renderer)

        yield self
~~~~~
~~~~~python.new
    @contextmanager
    def patch(self, monkeypatch: Any, target: str = "stitcher.common.bus.bus"):
        real_bus = stitcher.common.bus.bus

        def intercept_present(
            ptr: Union[str, SemanticPointer], level: str = "info", **kwargs: Any
        ) -> None:
            # This is the critical change. We now simulate the filtering logic
            # of the CliRenderer before deciding to record the message.
            renderer = real_bus._renderer
            if not renderer:
                return

            # Get the loglevel value from the actual renderer instance
            loglevel_value = getattr(renderer, "loglevel_value", 0)

            # Perform the filtering
            if LEVEL_MAP.get(level, 0) < loglevel_value:
                return

            # If the message passes the filter, record it.
            if isinstance(ptr, SemanticPointer):
                self._spy_renderer.record(level, ptr, kwargs)

        # In pyneedle-bus, the entry point is 'present' instead of '_render'
        monkeypatch.setattr(real_bus, "present", intercept_present)

        # Ensure our spy renderer is set
        monkeypatch.setattr(real_bus, "_renderer", self._spy_renderer)

        yield self
~~~~~

#### Acts 5: 删除旧的总线包

现在可以安全地移除 `stitcher-bus` 目录。

~~~~~act
run_command
~~~~~
~~~~~
rm -rf packages/stitcher-bus
~~~~~

### 下一步建议
恭喜，**阶段一：功能平移** 已基本完成。我们已经将 Stitcher 的心脏从一个私有实现置换为了 `pyneedle-bus` 的通用实现。

现在建议执行以下验证：
1.  再次运行 `uv run pytest packages --prerelease=allow`。
2.  检查 `packages/stitcher-bus/tests/unit/test_message_bus.py` 是否需要被迁移到 `stitcher-common` 或 `stitcher-test-utils` 下作为集成测试。
3.  如果一切正常，我们可以进入 **阶段二**：开始在 `AnalysisEngine` 中引入 `EventBus` 以支持流式反馈。
