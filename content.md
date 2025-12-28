好的，我明白。这是一个典型的重构后遗症。

你的诊断是正确的。在我之前的重构中，我们做出了一个重要的架构决定：

1.  **`pyneedle-runtime` 不再暴露 `_default_loader`**: 为了让 `pyneedle` 成为一个纯粹的、无副作用的基础库，我们移除了 `_default_loader` 这个具有应用特定含义的全局变量。它的 `__all__` 中现在只包含通用的工具，如 `nexus` 和 `_find_project_root`。
2.  **`stitcher-common` 负责组合**: `stitcher-common` 包现在负责创建和组合加载器，形成了应用专属的 `stitcher_nexus` 和 `stitcher_loader`。

然而，我们遗漏了一个地方：顶层的 `pyneedle` 包（`packages/pyneedle/src/needle/__init__.py`）仍然在尝试从 `needle.runtime` 导入并重新导出这个已经被移除的 `_default_loader`。这导致了你看到的 `ImportError`。

解决方案很简单，就是让顶层 `pyneedle` 包的公开 API 与我们新的架构决策保持一致：移除对 `_default_loader` 的引用。

## [WIP] fix(pyneedle): 移除对已废弃的 _default_loader 的引用

### 错误分析
`stitcher check` 命令在启动时因 `ImportError` 而失败。根源在于顶层的 `pyneedle` 包在其 `__init__.py` 文件中，试图从 `needle.runtime` 导入并重新导出 `_default_loader`。然而，在最近的架构重构中，`_default_loader` 作为一个应用级的概念已被从通用的 `needle.runtime` 模块中移除，导致导入失败。

### 用户需求
修复此 `ImportError`，使应用可以正常启动。

### 评论
这是一个简单的清理任务，旨在完成我们之前进行的架构分离。通过从顶层包的公共 API 中移除这个悬空的引用，我们使 `pyneedle` 的接口与其作为通用基础库的新角色完全保持一致。

### 目标
1.  修改 `packages/pyneedle/src/needle/__init__.py` 文件。
2.  从 `from needle.runtime ...` 导入语句中移除 `_default_loader`。
3.  从 `__all__` 列表中移除 `"_default_loader"`。

### 基本原理
应用程序的入口点不应依赖一个已经被架构性废弃的内部变量。通过清理这个顶层 `__init__.py`，我们完成了 `pyneedle` 库与其应用（`stitcher`）之间的解耦。

### 标签
#intent/fix #flow/ready #priority/high #comp/interfaces #comp/runtime #scope/api #dx #task/domain/storage #task/object/loader-architecture #task/action/refactor #task/state/end

---

### Script

#### Acts 1: 清理顶层 `pyneedle` 包的 API

我们将编辑 `pyneedle` 的主 `__init__.py` 文件，移除对 `_default_loader` 的所有引用。

~~~~~act
patch_file
packages/pyneedle/src/needle/__init__.py
~~~~~
~~~~~python.old
# Now that the full 'needle' namespace is assembled, we can safely import from it.
from needle.pointer import L, SemanticPointer, PointerSet
from needle.runtime import nexus, _default_loader
from needle.spec import (
    NexusProtocol,
    ResourceLoaderProtocol,
    SemanticPointerProtocol,
    PointerSetProtocol,
)

__all__ = [
    "L",
    "SemanticPointer",
    "PointerSet",
    "nexus",
    "_default_loader",
    "NexusProtocol",
    "ResourceLoaderProtocol",
    "SemanticPointerProtocol",
    "PointerSetProtocol",
]
~~~~~
~~~~~python.new
# Now that the full 'needle' namespace is assembled, we can safely import from it.
from needle.pointer import L, SemanticPointer, PointerSet
from needle.runtime import nexus
from needle.spec import (
    NexusProtocol,
    ResourceLoaderProtocol,
    SemanticPointerProtocol,
    PointerSetProtocol,
)

__all__ = [
    "L",
    "SemanticPointer",
    "PointerSet",
    "nexus",
    "NexusProtocol",
    "ResourceLoaderProtocol",
    "SemanticPointerProtocol",
    "PointerSetProtocol",
]
~~~~~
