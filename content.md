简要回答

是的，这个错误是上一步重构的直接后果。我删除了 `raw_parser.py` 并将 `RawDocstringParser` 移到了 `parsers.py` 中，但忘记了更新 `stitcher-python-adapter` 包的 `__init__.py` 文件以反映这一变化。

我将立即修复这个导入路径。

## [WIP] fix: 修正因文件重构导致的导入错误

### 错误分析

**症状**: `ModuleNotFoundError: No module named 'stitcher.adapter.python.docstring.raw_parser'`
**原因**: 在上一个计划中，`raw_parser.py` 文件被删除，其内容被合并到了 `parsers.py`。然而，`packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py` 文件仍然尝试从旧的、已不存在的路径导入 `RawDocstringParser`。
**解决方案**: 更新 `__init__.py`，使其从新的 `docstring` 子包（通过其 `__init__.py`）导入 `RawDocstringParser` 和我们新创建的 `GriffeDocstringParser`。

### 用户需求

修复因 `raw_parser.py` 文件被删除而导致的 `ModuleNotFoundError`。

### 评论

这是一个典型的重构后遗留问题。在移动或重命名模块时，必须同步更新所有引用它的地方。幸运的是，Python 的导入错误追溯信息非常清晰，可以快速定位问题。

### 目标

1.  修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py` 以修复导入路径。
2.  同时，将新创建的 `GriffeDocstringParser` 也导出，以便上层应用可以使用它。

### 基本原理

我们将修改 `.../adapter/python/__init__.py`，使其不再直接引用 `docstring` 子包的内部模块（如 `raw_parser.py`），而是从该子包的 `__init__.py` 中导入其公开的 API。这符合良好的包设计原则。

### 标签

#intent/fix #flow/ready #priority/high #comp/adapter #task/domain/docstring #task/object/adapter #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 更新 `stitcher-python-adapter` 的导出

我们将修复 `__init__.py` 中的导入语句，并更新 `__all__` 列表以包含新的解析器。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python.old
from .parser import PythonParser
from .transformer import PythonTransformer
from .generator import PythonStubGenerator
from .fingerprint import PythonFingerprintStrategy
from .inspector import parse_plugin_entry, InspectionError
from .griffe_parser import GriffePythonParser
from .docstring.raw_parser import RawDocstringParser

__all__ = [
    "RawDocstringParser",
    "PythonParser",
    "PythonTransformer",
    "PythonStubGenerator",
    "PythonFingerprintStrategy",
    "parse_plugin_entry",
    "InspectionError",
    "GriffePythonParser",
]
~~~~~
~~~~~python.new
from .parser import PythonParser
from .transformer import PythonTransformer
from .generator import PythonStubGenerator
from .fingerprint import PythonFingerprintStrategy
from .inspector import parse_plugin_entry, InspectionError
from .griffe_parser import GriffePythonParser
from .docstring import RawDocstringParser, GriffeDocstringParser

__all__ = [
    "RawDocstringParser",
    "GriffeDocstringParser",
    "PythonParser",
    "PythonTransformer",
    "PythonStubGenerator",
    "PythonFingerprintStrategy",
    "parse_plugin_entry",
    "InspectionError",
    "GriffePythonParser",
]
~~~~~

### 下一步建议

导入问题已解决。现在请重新运行测试。如果测试通过，我们就可以继续实施路线图的 **阶段 2: 存储层升级 (The Storage Layer)**。
