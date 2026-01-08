简要回答

收到，这是修复 `ImportError` 的计划。

## [WIP] fix: 修正 Griffe 导入路径错误

### 错误分析

**症状**: `ModuleNotFoundError: No module named 'griffe.dataclasses'`
**原因**: 代码尝试从 `griffe.dataclasses` 导入 `DocstringSection` 等类，但根据你提供的 `griffe` 导出列表，这些类直接暴露在 `griffe` 顶级包中，或者 `griffe.dataclasses` 模块在当前安装的版本中不存在（或已被重构）。
**解决方案**: 将导入路径从 `griffe.dataclasses` 更改为 `griffe`。

### 用户需求

修复 `stitcher-python-adapter` 中由于错误的 `griffe` 导入路径导致的崩溃。

### 评论

这是一个典型的依赖库 API 变动或版本不匹配问题。直接从顶级包导入通常是更稳健的做法，尤其是当库显式地在 `__all__` 中导出了这些符号时。

### 目标

1.  修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/parsers.py`，修正导入语句。

### 基本原理

根据提供的 `__all__` 列表，所需的 `DocstringSection` 相关类均在 `griffe` 的顶层命名空间中可用。

### 标签

#intent/fix #flow/ready #priority/high #comp/adapter #task/domain/docstring #task/object/adapter #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修正 parsers.py 的导入

我们将从 `griffe` 直接导入所需的类，而不是 `griffe.dataclasses`。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/docstring/parsers.py
~~~~~
~~~~~python.old
import griffe
from griffe import Docstring, Parser
from griffe.dataclasses import (
    DocstringSection as GriffeSection,
    DocstringSectionAdmonition,
    DocstringSectionAttributes,
    DocstringSectionParameters,
    DocstringSectionReturns,
    DocstringSectionText,
    DocstringSectionYields,
    DocstringSectionRaises,
)

from stitcher.spec import (
~~~~~
~~~~~python.new
import griffe
from griffe import (
    Docstring,
    Parser,
    DocstringSection as GriffeSection,
    DocstringSectionAdmonition,
    DocstringSectionAttributes,
    DocstringSectionParameters,
    DocstringSectionReturns,
    DocstringSectionText,
    DocstringSectionYields,
    DocstringSectionRaises,
)

from stitcher.spec import (
~~~~~

### 下一步建议

修复此导入错误后，请再次运行测试以验证适配器层的功能。如果还有其他关于 `griffe` 内部结构的假设错误（例如属性名称变化），可能还需要进一步调整。
