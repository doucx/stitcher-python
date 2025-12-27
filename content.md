简要回答
这是一个典型的导出遗漏问题。虽然我在 `protocols.py` 中定义了 `WritableResourceLoaderProtocol`，但我忘记更新 `pyneedle-spec` 包的入口文件 `__init__.py` 来公开这个新协议，导致其他模块无法导入它。

我将修复 `pyneedle-spec` 的导出列表。

## [WIP] fix(spec): 导出 WritableResourceLoaderProtocol

### 错误分析
**ImportError**: `cannot import name 'WritableResourceLoaderProtocol' from 'needle.spec'`
**原因**: 新增的协议类 `WritableResourceLoaderProtocol` 虽然在 `protocols.py` 中定义了，但未被添加到 `packages/pyneedle-spec/src/needle/spec/__init__.py` 的 `__all__` 列表中。Python 的模块系统无法从包的顶层命名空间找到它。

### 用户需求
修复导入错误，使 `nexus` 模块能正常加载。

### 评论
这是重构过程中常见的疏忽。修复非常直接。

### 目标
在 `packages/pyneedle-spec/src/needle/spec/__init__.py` 中显式导出 `WritableResourceLoaderProtocol`。

### 基本原理
Python 包的最佳实践是通过 `__init__.py` 暴露公共 API。

### 标签
#intent/fix #flow/ready #priority/critical #comp/interfaces #scope/core #ai/instruct #task/domain/core-runtime #task/object/nexus-loader #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 更新 Spec 包的导出列表

~~~~~act
patch_file
packages/pyneedle-spec/src/needle/spec/__init__.py
~~~~~
~~~~~python.old
from .protocols import (
    SemanticPointerProtocol,
    PointerSetProtocol,
    ResourceLoaderProtocol,
    NexusProtocol,
)

__all__ = [
    "SemanticPointerProtocol",
    "PointerSetProtocol",
    "ResourceLoaderProtocol",
    "NexusProtocol",
]
~~~~~
~~~~~python.new
from .protocols import (
    SemanticPointerProtocol,
    PointerSetProtocol,
    ResourceLoaderProtocol,
    WritableResourceLoaderProtocol,
    NexusProtocol,
)

__all__ = [
    "SemanticPointerProtocol",
    "PointerSetProtocol",
    "ResourceLoaderProtocol",
    "WritableResourceLoaderProtocol",
    "NexusProtocol",
]
~~~~~
