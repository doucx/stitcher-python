## [FIX] refactor(cli): 适配 Renderer 协议以支持 kwargs 透传

### 错误分析
`pyneedle-bus` 的 `FeedbackBus` 会将所有模板参数透传给 `Renderer`，以便支持高级渲染场景。然而，Stitcher 的 `CliRenderer` 和测试用的 `SpyRenderer` 的 `render` 方法签名过于严格，导致接收到额外参数时崩溃。

### 用户需求
修改 `CliRenderer` 和 `SpyRenderer` 的 `render` 方法签名，使其能够接收并（暂时）忽略多余的关键字参数。

### 评论
这是协议升级中的常见问题。`RendererProtocol` 在 PyNeedle 中被定义为 `def render(self, message: str, level: str = "info", **kwargs: Any) -> None:`，我们需要严格遵守此契约。

### 目标
1.  修改 `packages/stitcher-cli/src/stitcher/cli/rendering.py` 中的 `CliRenderer`。
2.  修改 `packages/stitcher-test-utils/src/stitcher/test_utils/bus.py` 中的 `SpyRenderer`。

### 基本原理
简单地为 `render` 方法添加 `**kwargs: Any` 参数即可解决此问题。

### 标签
#intent/fix #flow/ready #priority/high 
#comp/cli #comp/tests #scope/core
#ai/instruct
#task/domain/bus #task/object/renderer #task/action/fix-signature #task/state/continue

---

### Script

#### Acts 1: 修复 `CliRenderer`

~~~~~act
patch_file
packages/stitcher-cli/src/stitcher/cli/rendering.py
~~~~~
~~~~~python.old
class CliRenderer(Renderer):
    def __init__(self, loglevel: LogLevel = LogLevel.INFO):
        self.loglevel_value = LEVEL_MAP[loglevel.value]

    def render(self, message: str, level: str):
        if LEVEL_MAP.get(level, 0) < self.loglevel_value:
            return

        color = None
~~~~~
~~~~~python.new
from typing import Any

class CliRenderer(Renderer):
    def __init__(self, loglevel: LogLevel = LogLevel.INFO):
        self.loglevel_value = LEVEL_MAP[loglevel.value]

    def render(self, message: str, level: str, **kwargs: Any):
        if LEVEL_MAP.get(level, 0) < self.loglevel_value:
            return

        color = None
~~~~~

#### Acts 2: 修复 `SpyRenderer`

~~~~~act
patch_file
packages/stitcher-test-utils/src/stitcher/test_utils/bus.py
~~~~~
~~~~~python.old
class SpyRenderer(Renderer):
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def render(self, message: str, level: str) -> None:
        # The spy logic mostly acts on record(), but satisfy interface
        pass

    def record(self, level: str, msg_id: SemanticPointer, params: Dict[str, Any]):
~~~~~
~~~~~python.new
class SpyRenderer(Renderer):
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []

    def render(self, message: str, level: str, **kwargs: Any) -> None:
        # The spy logic mostly acts on record(), but satisfy interface
        pass

    def record(self, level: str, msg_id: SemanticPointer, params: Dict[str, Any]):
~~~~~

### 下一步建议
这次修复应该能解决所有的 `TypeError`。请再次运行测试。如果测试全部通过，我们就可以自信地宣布 **阶段一：功能平移** 圆满完成。接下来我们将进入激动人心的 **阶段二：引入 EventBus**。
