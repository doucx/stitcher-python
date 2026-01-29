这是一个关键的转折点。我们正在将“如何加载资源”这一**应用级策略**从基础设施（Needle）收回到应用（Stitcher）手中。

通过这个重构，`stitcher-common` 不再只是被动地向 Bus 注册路径，而是主动地扫描环境、选择语言、组装 Operator 链，并最终将其“挂载”到总线上。

## [WIP] refactor(common): 重构 stitcher-common 总线组装逻辑，实现 Operator 显式注入

### 用户需求
适配 `pyneedle-bus` 0.1.1 的接口变更。在 `stitcher-common` 中实现资产加载、语言检测和 Operator 组装，并注入到 `FeedbackBus` 中。

### 评论
通过这次重构，Stitcher 获得了对自身 I18n 逻辑的绝对控制权。我们不再依赖 Needle 内部黑盒式的语言检测，而是可以根据 Stitcher 的具体需求（例如支持 `STITCHER_LANG` 环境变量）来定制加载行为。这正是 **HFEA v1.0** 中“架构不可腐蚀性”的体现。

### 目标
1.  **实现语言检测**：将原 `MessageStore` 的检测逻辑迁移至 `stitcher-common`。
2.  **组装 Operator**：使用 `I18NFactoryOperator` 和 `OverlayOperator` 构建 Stitcher 的专属 Nexus。
3.  **注入总线**：调用 `bus.set_operator` 完成初始化。
4.  **保持兼容**：确保 `stitcher_operator` 接口依然可用且支持模板格式化。

### 基本原理
根据 **HFEA v1.0** 的“基础设施优先”原则，我们将 `stitcher-common/bus.py` 升级为一个真正的 **Composition Root (组装根)**。它负责将低层的 `pyneedle-runtime` 组件组合成高层的 `FeedbackBus` 服务。

### 标签
#intent/refine #flow/ready #priority/high
#comp/interfaces #concept/executor #scope/core
#ai/brainstorm
#task/domain/bus
#task/object/stitcher-assembly
#task/action/refactor
#task/state/continue

---

### Script

#### Acts 1: 重构 stitcher-common 的 bus.py

我们将彻底重写 `bus.py`，移除对不存在的 `message_store` 的引用，并建立新的组装逻辑。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/bus.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import Union, Any

from needle.bus import bus
from needle.operators import I18NFactoryOperator, OverlayOperator
from needle.runtime import nexus as global_nexus
from needle.spec import SemanticPointerProtocol


def _detect_lang() -> str:
    """检测系统或环境变量中定义的语言。"""
    # 1. 显式覆盖
    env_lang = os.getenv("NEEDLE_LANG") or os.getenv("STITCHER_LANG")
    if env_lang:
        return env_lang

    # 2. 系统 LANG 变量 (例如 en_US.UTF-8 -> en)
    sys_lang = os.getenv("LANG")
    if sys_lang:
        base_lang = sys_lang.split(".")[0].split("_")[0]
        if base_lang:
            return base_lang

    return "en"


# 1. 定位资产根目录与语言
_assets_root = Path(__file__).parent / "assets"
_lang = _detect_lang()

# 2. 组装 Stitcher 专属的 Operator
# I18NFactoryOperator 负责根据语言代码从资产目录加载 FileSystemOperator
_factory = I18NFactoryOperator(_assets_root)
_stitcher_i18n = _factory(_lang)

# 3. 构造 Nexus (层叠 Operator)
# 优先级：Stitcher 本地资产 > 全局默认 Nexus
_nexus = OverlayOperator([_stitcher_i18n, global_nexus])

# 4. 注入到全局反馈总线
# 这样 bus.present(), bus.info() 等方法就能使用组装好的解析逻辑
bus.set_operator(_nexus)


# 5. 定义 stitcher_operator (Nexus) 接口
# 此接口用于在 CLI 或代码中直接获取渲染后的字符串
def stitcher_operator(key: Union[str, SemanticPointerProtocol], **kwargs: Any) -> str:
    """
    Stitcher 的核心字符串解析器。
    它包装了 bus.render_to_string，提供从 Pointer 到最终格式化字符串的转换。
    """
    return bus.render_to_string(key, **kwargs)


# 6. 导出全局单例和操作符
__all__ = ["bus", "stitcher_operator"]
~~~~~

### 下一步建议

我们已经成功修复了 Stitcher 的总线组装。现在，`stitcher-cli` 应该能够再次正常启动并正确显示 I18n 文本了。

**目前整体架构已经非常漂亮了**：
*   **Needle (Infrastructure)**：只提供协议 (`spec`)、基本的 Pointer 实现 (`pointer`)、原子化的 Operator 零件 (`runtime`) 和纯粹的消息通道 (`bus`)。
*   **Stitcher (Application)**：负责扫描自己的资产，并利用 Needle 的零件组装出符合自己业务逻辑的总线实例。

**接下来的行动建议**：
1.  **验证**：我们可以尝试运行一个 Stitcher 的 CLI 命令（例如 `stitcher --help`），确保它没有崩溃且能正确显示描述。
2.  **清理**：如果验证通过，我们可以清理一些不再需要的残留代码（如果有的话）。

由于目前的重构已经覆盖了核心路径，我建议先执行一次全面的 `git status` 审查，准备生成 `[COMMIT]` 计划。
