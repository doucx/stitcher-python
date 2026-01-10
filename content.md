You are absolutely correct. My apologies. The cleanup plan was flawed because I deleted the files but failed to remove the references to them in the package's `__init__.py`. This is a classic refactoring error, and the test suite has correctly identified it.

The `ModuleNotFoundError` is a direct result of the `stitcher-python-adapter`'s `__init__.py` trying to import `PythonStubGenerator` from a file that no longer exists.

I will now generate a plan to fix this oversight.

## [WIP] fix(adapter): Remove dangling imports after stubgen refactor

### 错误分析

测试套件在收集阶段就因 `ModuleNotFoundError` 而崩溃。根本原因是在上一步的清理计划中，我虽然删除了 `packages/stitcher-python-adapter/src/stitcher/adapter/python/generator.py` 文件，但**忘记了更新**同级目录下的 `__init__.py` 文件。

这个 `__init__.py` 文件依然保留着 `from .generator import PythonStubGenerator` 这一行，并试图将 `PythonStubGenerator` 添加到 `__all__` 列表中。当测试框架导入任何依赖 `stitcher-python-adapter` 的模块时，Python 解释器会执行这个 `__init__.py`，并因找不到 `generator.py` 模块而立即失败。这个单一的错误点导致了整个测试导入链的崩溃。

### 用户需求

修复因清理冗余文件不彻底而导致的 `ModuleNotFoundError`，使测试套件能够正常运行。

### 评论

这是一个典型的重构后遗症，有力地说明了修改一个包的内部结构时，必须同步更新其公共 API 的暴露点（即 `__init__.py` 文件）。这个错误是我的疏忽，而测试套件的快速失败则证明了我们自动化验证体系的价值。修复这个问题将使 `stitcher-python-adapter` 包恢复内部一致性。

### 目标

1.  定位 `packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py` 文件。
2.  移除其中对 `generator.py` 模块的导入语句。
3.  从 `__all__` 列表中移除 `PythonStubGenerator`。

### 基本原理

我们将使用一个精确的 `patch_file` 操作来修正 `__init__.py`。`old_str` 将包含错误的导入语句和旧的 `__all__` 列表。`new_str` 将是移除了这两处引用后的正确版本。这是一个简单、直接且能根除问题的修复方案，它将使 `python-adapter` 包的公共接口与其物理文件结构重新保持一致。

### 标签

#intent/fix #flow/ready #priority/critical #comp/python-adapter #comp/tests #scope/core #task/domain/architecture #task/object/stubgen-package #task/action/cleanup #task/state/continue

---

### Script

#### Acts 1: 修正 `python-adapter` 的 `__init__.py`

我们将移除 `stitcher-python-adapter` 中对已删除模块的悬空引用。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python
from .docstring import (
    GriffeDocstringParser,
    GoogleDocstringRenderer,
    GoogleSerializer,
    NumpyDocstringRenderer,
    NumpySerializer,
    RawDocstringParser,
    RawSerializer,
    get_docstring_codec,
    get_docstring_serializer,
)
from .fingerprint import PythonFingerprintStrategy
from .generator import PythonStubGenerator
from .griffe_parser import GriffePythonParser
from .inspector import InspectionError, parse_plugin_entry
from .parser import PythonParser
from .transformer import PythonTransformer

__all__ = [
    # Core Python Adapter Components
    "GriffePythonParser",
    "InspectionError",
    "PythonFingerprintStrategy",
    "PythonParser",
    "PythonStubGenerator",
    "PythonTransformer",
    "parse_plugin_entry",
    # Docstring Sub-package
    "GriffeDocstringParser",
    "GoogleDocstringRenderer",
    "GoogleSerializer",
    "NumpyDocstringRenderer",
    "NumpySerializer",
    "RawDocstringParser",
    "RawSerializer",
    "get_docstring_codec",
    "get_docstring_serializer",
]
~~~~~
~~~~~python
from .docstring import (
    GriffeDocstringParser,
    GoogleDocstringRenderer,
    GoogleSerializer,
    NumpyDocstringRenderer,
    NumpySerializer,
    RawDocstringParser,
    RawSerializer,
    get_docstring_codec,
    get_docstring_serializer,
)
from .fingerprint import PythonFingerprintStrategy
from .griffe_parser import GriffePythonParser
from .inspector import InspectionError, parse_plugin_entry
from .parser import PythonParser
from .transformer import PythonTransformer

__all__ = [
    # Core Python Adapter Components
    "GriffePythonParser",
    "InspectionError",
    "PythonFingerprintStrategy",
    "PythonParser",
    "PythonTransformer",
    "parse_plugin_entry",
    # Docstring Sub-package
    "GriffeDocstringParser",
    "GoogleDocstringRenderer",
    "GoogleSerializer",
    "NumpyDocstringRenderer",
    "NumpySerializer",
    "RawDocstringParser",
    "RawSerializer",
    "get_docstring_codec",
    "get_docstring_serializer",
]
~~~~~

### 下一步建议

这个修复应该能够解决 `ModuleNotFoundError`，让测试套件恢复正常。

一旦测试通过，`stitcher-stubgen` 的架构重构任务就真正地、彻底地完成了。届时，我强烈建议你创建一个 `[COMMIT]` 计划，将整个重构过程（从创建新包到最后的清理和修复）作为一个原子提交，为项目留下清晰的演进历史。
