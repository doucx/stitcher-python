好的，我将启动这场深度的“架构纯化”行动。我们将把所有的反馈资产、国际化工厂逻辑以及全局单例 `bus` 全部迁移到 `stitcher-bus` 包中。

这将使 `stitcher-bus` 成为名副其实的项目反馈中枢。

## [WIP] refactor: 迁移 I18N 资产与工厂逻辑至 stitcher-bus

### 用户需求
将所有的 I18N JSON 资产、`pyneedle` 工厂配置逻辑以及全局 `bus` 单例从 `stitcher-common` 物理迁移至 `stitcher-bus`。创建迁移脚本以更新全项目的引用路径。

### 评论
这是一次关键的重构。通过将“通道”（Bus）与“内容”（Assets/I18N）合并，我们消除了一个模糊的中间层。`stitcher-bus` 现在负责所有的用户交互沟通，而 `stitcher-common` 仅保留无副作用的实用工具。这符合“正规军”工程标准中的**真理单一来源 (SSoT)** 原则。

### 目标
1.  **物理移动**: 将 `assets/needle` 目录及其内容迁移到 `packages/stitcher-bus/src/stitcher/bus/assets`。
2.  **提取工厂逻辑**: 在 `stitcher-bus` 中创建 `factory.py`，承载多语言探测和 `pyneedle` 操作符组装逻辑。
3.  **配置单例**: 在 `stitcher-bus` 的 `__init__.py` 中实例化并导出全局 `bus`。
4.  **清理旧包**: 移除 `stitcher-common` 中已迁移的代码。
5.  **更新依赖**: 确保 `stitcher-bus` 的 `pyproject.toml` 包含资产文件。
6.  **准备迁移脚本**: 创建用于更新全项目 FQN 引用的 `refactor apply` 脚本。

### 基本原理
我们利用命名空间包的特性，在物理位置变更后，通过 `refactor apply` 的语义重命名能力，将所有 `from stitcher.common import bus` 自动更新为 `from stitcher.bus import bus`。这样可以确保这种大规模的跨包重构是安全、准确且可验证的。

### 标签
#intent/refine #flow/ready #priority/high 
#comp/build #comp/common #comp/bus #concept/state #scope/core 
#ai/instruct
#task/domain/refactoring #task/object/i18n-hub #task/action/consolidation #task/state/continue

---

### Script

#### Acts 1: 物理移动资产目录

将所有多语言 JSON 文件迁移到新的宿主包。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/stitcher-bus/src/stitcher/bus/assets
mv packages/stitcher-common/src/stitcher/common/assets/needle packages/stitcher-bus/src/stitcher/bus/assets/
~~~~~

#### Acts 2: 在 stitcher-bus 中实现工厂逻辑

创建 `factory.py` 以解耦 I18N 的组装过程。

~~~~~act
write_file
packages/stitcher-bus/src/stitcher/bus/factory.py
~~~~~
~~~~~python
import os
from pathlib import Path
from typing import Dict
from needle.pointer import L
from needle.operators import I18NFactoryOperator, OverlayOperator
from needle.runtime import _find_project_root

from .bus import FeedbackBus

# 1. Config Sources
# Asset paths are now relative to this file in stitcher-bus
_project_root = _find_project_root()
_bus_assets_root = Path(__file__).parent / "assets"

# 2. Factories
# Note: User overrides still live in project_root/.stitcher/needle
_user_factory = I18NFactoryOperator(_project_root / ".stitcher")
_default_factory = I18NFactoryOperator(_bus_assets_root)

# 3. Dynamic Pipeline with Caching
_operator_cache: Dict[str, OverlayOperator] = {}


def _detect_lang() -> str:
    # 1. Explicit override
    stitcher_lang = os.getenv("STITCHER_LANG")
    if stitcher_lang:
        return stitcher_lang

    # 2. System LANG (e.g. "zh_CN.UTF-8" -> "zh")
    sys_lang = os.getenv("LANG")
    if sys_lang:
        base_lang = sys_lang.split(".")[0].split("_")[0]
        if base_lang:
            return base_lang

    return "en"


def get_current_renderer() -> OverlayOperator:
    lang_code = _detect_lang()

    if lang_code in _operator_cache:
        return _operator_cache[lang_code]

    lang_ptr = getattr(L, lang_code)

    user_op = _user_factory(lang_ptr)
    default_op = _default_factory(lang_ptr)

    # Priority: User > Default
    pipeline = OverlayOperator([user_op, default_op])

    _operator_cache[lang_code] = pipeline
    return pipeline


def stitcher_operator(key):
    renderer = get_current_renderer()
    return renderer(key)


# Initialize the global singleton
bus = FeedbackBus(operator=stitcher_operator)
~~~~~

#### Acts 3: 更新 stitcher-bus 入口并导出单例

~~~~~act
write_file
packages/stitcher-bus/src/stitcher/bus/__init__.py
~~~~~
~~~~~python
"""
Stitcher-Bus: Event and message orchestration for the Stitcher ecosystem.
"""
from .factory import bus, stitcher_operator

__all__ = ["bus", "stitcher_operator"]
~~~~~

#### Acts 4: 清理 stitcher-common 的入口文件

保留实用工具，移除已迁移的 Bus 实例化逻辑。

~~~~~act
write_file
packages/stitcher-common/src/stitcher/common/__init__.py
~~~~~
~~~~~python
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

#### Acts 5: 更新 stitcher-bus 包配置以包含资产

~~~~~act
patch_file
packages/stitcher-bus/pyproject.toml
~~~~~
~~~~~toml.old
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
~~~~~
~~~~~toml.new
[tool.hatch.build.targets.wheel]
packages = ["src/stitcher"]
include = ["/src/stitcher/bus/assets"]
~~~~~

#### Acts 6: 创建全项目引用更新脚本

这个迁移脚本将负责把所有代码中的旧 Bus 引用重定向到新位置。

~~~~~act
write_file
migrations/005_update_bus_fqn_references.py
~~~~~
~~~~~python
from stitcher.refactor.migration import MigrationSpec, Rename

def upgrade(spec: MigrationSpec):
    """
    Updates all project references from the old bus location in common
    to the new dedicated bus package.
    """
    # This will update all 'from stitcher.common import bus' 
    # to 'from stitcher.bus import bus' throughout the workspace.
    spec.add(Rename("stitcher.common.bus", "stitcher.bus.bus"))
    
    # Also update the operator if used directly
    spec.add(Rename("stitcher.common.stitcher_operator", "stitcher.bus.stitcher_operator"))
~~~~~

### 下一步建议
1.  **执行重构**: 运行 `stitcher refactor apply migrations/005_update_bus_fqn_references.py`。
2.  **验证迁移**: 运行 `pytest`。特别注意 `stitcher-bus` 中的新测试，确保它们现在能够找到位于新路径下的 JSON 资产。
3.  **检查打包**: 运行 `uv build`（或尝试安装包），确认 `assets/` 确实被包含在分发包中。
