`RenameSymbolOperation` 无法重命名符号定义的原因是 `SemanticGraph` 在构建注册表时，由于递归逻辑排除了 `is_alias` 为真的模块，导致部分命名空间包结构下的子模块（如 `stitcher.common`）未被扫描。我将修改 `_build_registry` 方法，移除该限制并添加循环检测机制，确保所有子模块都能被正确遍历和索引。

## [WIP] fix: 修复 SemanticGraph 忽略命名空间子模块导致重命名失效的问题

### 错误分析

在 `test_debug_rename_failure_analysis` 测试中，我们发现 `RenameSymbolOperation` 未能重命名 `bus.py` 中的 `class MessageBus` 定义。调试日志显示：
1.  `SemanticGraph` 加载了 `stitcher` 包。
2.  但是 `Could not find 'stitcher.common.messaging.bus' directly`。
3.  `UsageRegistry` 中没有 `bus.py` 的记录（`Usages inside bus.py: 0`）。

**根本原因**：
`SemanticGraph._build_registry` 方法在递归遍历模块成员时，有一行检查：
```python
if isinstance(member, griffe.Module) and not member.is_alias:
    self._build_registry(member)
```
对于某些 Python 命名空间包（Namespace Packages），Griffe 可能会将子包（如 `stitcher.common`）标记为 `is_alias=True`（因为它可能被视为从路径中“导入”的）。当前的逻辑直接跳过了这些模块，导致 `bus.py` 所在的子树从未被扫描，因此其中的类定义从未被注册到 `UsageRegistry` 中。

**解决方案**：
1.  修改 `_build_registry`，**移除 `not member.is_alias` 的限制**。只要成员是 `griffe.Module`，我们就应该尝试进入构建索引。
2.  为了防止因移除限制而可能导致的无限递归（例如模块相互导入），引入一个 `visited` 集合来跟踪已处理的模块路径。

### 用户需求
修复重构引擎中的 Bug，确保 `RenameSymbolOperation` 不仅能重命名符号的引用，也能正确重命名符号的定义处（类名、函数名等），特别是在复杂的命名空间包结构中。

### 评论
这是一个关键的 Bug 修复。如果不修复，自动化重构将是不完整的，导致代码处于破坏状态（引用已更新但定义未更新，引发 `ImportError`）。

### 目标
1.  修改 `packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py`。
2.  更新 `_build_registry` 方法，支持递归遍历被标记为 Alias 的模块，并添加循环检测。

### 基本原理
通过放宽递归条件并增加循环保护，我们确保了 `SemanticGraph` 能够完整地遍历整个包结构，从而使 `_UsageVisitor` 有机会访问并索引所有源文件中的符号定义。这是所有基于图谱的重构操作（如重命名、移动）正确工作的基础。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #concept/history #scope/core #ai/instruct #task/domain/refactoring #task/object/semantic-graph #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复 SemanticGraph 遍历逻辑

我们将修改 `graph.py`，在 `_build_registry` 中添加 `visited` 参数，并移除对 `is_alias` 的排斥。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def load(self, package_name: str, submodules: bool = True) -> None:
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module
        self._griffe_loader.resolve_aliases()
        self._build_registry(module)

    def _build_registry(self, module: griffe.Module):
        for member in module.members.values():
            if isinstance(member, griffe.Module) and not member.is_alias:
                self._build_registry(member)
        if module.filepath:
            self._scan_module_usages(module)

    def _scan_module_usages(self, module: griffe.Module):
~~~~~
~~~~~python.new
    def load(self, package_name: str, submodules: bool = True) -> None:
        module = self._griffe_loader.load(package_name, submodules=submodules)
        self._modules[package_name] = module
        self._griffe_loader.resolve_aliases()
        self._build_registry(module)

    def _build_registry(
        self, module: griffe.Module, visited: Optional[Set[str]] = None
    ):
        if visited is None:
            visited = set()

        if module.path in visited:
            return
        visited.add(module.path)

        for member in module.members.values():
            if isinstance(member, griffe.Module):
                self._build_registry(member, visited)
        if module.filepath:
            self._scan_module_usages(module)

    def _scan_module_usages(self, module: griffe.Module):
~~~~~

#### Acts 2: 引入必要的 Set 类型导入

由于我们在 `_build_registry` 的签名中使用了 `Set`，我们需要确保它已被导入。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, DefaultDict
from collections import defaultdict
import griffe
~~~~~
~~~~~python.new
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Dict, Optional, DefaultDict, Set
from collections import defaultdict
import griffe
~~~~~

### 下一步建议

现在 `SemanticGraph` 应该能够正确遍历命名空间包了。建议运行 `test_debug_rename_failure_analysis` 以及其他相关的重构测试（如 `test_rename_symbol_definition.py`），验证修复是否有效，并确认没有引入死循环或性能退化。
