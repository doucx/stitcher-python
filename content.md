好的，现在我们开始在 `stitcher-common` 中建立新的总线入口。这将作为整个 Stitcher 系统与 `pyneedle-bus` 之间的桥梁，并负责加载我们刚刚搬迁的资产。

## [WIP] feat(common): 建立基于 pyneedle-bus 的总线入口

### 用户需求
在 `stitcher-common` 中创建一个新的总线入口模块，集成 `pyneedle-bus` 并自动加载 Stitcher 的 I18n 资源，从而取代原有的 `stitcher-bus` 包。

### 评论
通过在 `stitcher-common` 内部建立入口，我们可以实现“无痛替换”：业务代码只需要微调 import 路径，而不需要感知底层 `FeedbackBus` 实现的彻底改变。同时，利用 `MessageStore` 的 `register_asset_root` 机制，我们完美解决了资产加载路径随包位置变化的问题。

### 目标
1.  修改 `stitcher-common` 的依赖，用 `pyneedle-bus` 替换 `stitcher-bus`。
2.  创建 `packages/stitcher-common/src/stitcher/common/bus.py`，实现资产自动注册逻辑。
3.  更新 `stitcher-common` 的导出接口，确保 `bus` 可以被全局访问。

### 基本原理
我们在 `bus.py` 中利用 Python 的 `__file__` 属性定位当前包内的 `assets` 文件夹，并调用 `message_store.register_asset_root`。这确保了无论 Stitcher 被安装在哪里，总线都能准确找到其翻译模板。我们导出的 `bus` 实例将直接来自 `pyneedle-bus`，从而开启了未来使用 `EventBus` 和 `LogBridge` 的可能性。

### 标签
#intent/build #flow/ready #priority/high 
#comp/common #concept/config #scope/api
#ai/instruct
#task/domain/bus #task/object/entrypoint #task/action/build #task/state/continue

---

### Script

#### Acts 1: 更新 `stitcher-common` 的依赖项

我们将移除对 `stitcher-bus` 的依赖，并添加 `pyneedle-bus`。

~~~~~act
patch_file
packages/stitcher-common/pyproject.toml
~~~~~
~~~~~toml.old
[project]
name = "stitcher-common"
version = "0.1.0"
description = "Common utilities and protocols for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "stitcher-bus",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
include = ["/src/stitcher/common/assets"]

[tool.uv.sources]
stitcher-bus = { workspace = true }
~~~~~
~~~~~toml.new
[project]
name = "stitcher-common"
version = "0.1.0"
description = "Common utilities and protocols for Stitcher."
requires-python = ">=3.10"
dependencies = [
    "pyneedle-bus ~= 0.1.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
include = ["/src/stitcher/common/assets"]

[tool.uv.sources]
~~~~~

#### Acts 2: 创建新的总线桥接模块

该模块负责将 `pyneedle-bus` 的单例与 Stitcher 的本地资产绑定。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/bus.py
~~~~~
~~~~~python
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

#### Acts 3: 更新包的导出声明

更新 `__init__.py`，使开发者可以通过 `stitcher.common.bus` 访问总线。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python.old
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .formatting import format_docstring, parse_docstring
from stitcher.spec.persistence import DocumentAdapter

# Note: The global 'bus' has been moved to stitcher.bus.
# Please use 'from stitcher.bus import bus' instead.

__all__ = [
    "format_docstring",
    "parse_docstring",
    "DocumentAdapter",
]
~~~~~
~~~~~python.new
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .formatting import format_docstring, parse_docstring
from stitcher.spec.persistence import DocumentAdapter
from .bus import bus

# Note: The global 'bus' is now powered by pyneedle-bus.
# It is recommended to use 'from stitcher.common.bus import bus'.

__all__ = [
    "format_docstring",
    "parse_docstring",
    "DocumentAdapter",
    "bus",
]
~~~~~

### 下一步建议
现在新的总线架构已在 `stitcher-common` 中就绪。下一步我们将进入最耗时的步骤：**全局清理与替换**。我们需要遍历所有引用了 `stitcher.bus` 的文件（如 `CheckReporter`, `PumpExecutor`, `StitcherApp` 等），将它们的 import 路径重定向到 `stitcher.common.bus`。

完成后，我们就可以安全地删除 `packages/stitcher-bus` 目录并验证功能是否依然正常。如果你准备好了，我可以开始生成全局替换的计划。
