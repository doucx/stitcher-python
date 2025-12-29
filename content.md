## [WIP] fix: 移除 OverlayNexus 并修复 SemanticPointerProtocol 导入

### 摘要头
## [WIP] fix(runtime&common): 移除废弃的 OverlayNexus 并修正协议导入

### 用户需求
1.  **"焦土政策" (Scorched Earth Policy)**: 根据路线图，彻底移除对已删除的 `OverlayNexus` 的引用。
2.  **降级替换**: 将原本的全局 `nexus` 对象降级为 `OverlayOperator`。
3.  **修复导入**: 解决 `stitcher-common` 中 `SemanticPointerProtocol` 的导入路径错误（延续上一步未完成的修复）。

### 评论
这是一个涉及多个包的架构一致性修复。我们正在从“有状态的 Nexus 加载器”模型迁移到“函数式的 Operator 算子”模型。此时出现的 `ImportError` 均源于旧代码引用了已被移除或迁移的符号。

### 目标
1.  修改 `pyneedle-runtime/src/needle/runtime.py`: 将 `OverlayNexus` 替换为 `OverlayOperator`，并更新实例化参数。
2.  修改 `stitcher-common/src/stitcher/common/__init__.py`: 修正 `SemanticPointerProtocol` 的导入源。

### 基本原理
1.  **Runtime 修复**: `OverlayNexus` 已从 `pyneedle-nexus` 包中移除。为了保持 `needle.runtime` 模块的导入兼容性（防止导出符号 `nexus` 消失导致更多错误），我们将其替换为新的 `OverlayOperator`。由于 `OverlayOperator` 接收 `operators` 而非 `loaders`，我们需要调整构造函数调用。
2.  **Common 修复**: `SemanticPointerProtocol` 定义在 `needle.spec` 中，而非 `needle.pointer`。分离这两个导入符合新的包结构规范。

### 标签
#intent/fix #flow/ready #priority/critical #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/refactor #task/object/overlay-nexus #task/action/remove #task/state/continue

---

### Script

#### Acts 2: 在 runtime 中替换 OverlayNexus 为 OverlayOperator

接着执行“焦土政策”，移除 `runtime.py` 对 `OverlayNexus` 的依赖，将其替换为新的 `OverlayOperator`。

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/runtime.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional
from needle.pointer import L, SemanticPointer, PointerSet
from needle.nexus import OverlayNexus


def _find_project_root(start_dir: Optional[Path] = None) -> Path:
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional
from needle.pointer import L, SemanticPointer, PointerSet
from needle.nexus import OverlayOperator


def _find_project_root(start_dir: Optional[Path] = None) -> Path:
~~~~~

~~~~~act
patch_file
packages/pyneedle-runtime/src/needle/runtime.py
~~~~~
~~~~~python
# --- Global Singleton Instance ---
# This is a generic, side-effect-free instance.
# Applications should compose their own nexus with specific loaders.
nexus = OverlayNexus(loaders=[])
# ---------------------------------
~~~~~
~~~~~python
# --- Global Singleton Instance ---
# This is a generic, side-effect-free instance.
# Applications should compose their own nexus with specific operators.
nexus = OverlayOperator(operators=[])
# ---------------------------------
~~~~~

### 下一步建议
执行此计划后，主要的 `ImportError` 应当消除。请再次运行测试。如果遇到关于 `I18NFactoryOperator` 或其他算子的新错误，我们将继续清理剩余的旧架构引用。
