Of course. The test collection failed with a `ModuleNotFoundError`, which is a classic runtime symptom of the very namespace vs. regular package conflict we were trying to solve for the static analyzer.

My previous refactoring correctly structured the files for a static analyzer, but I missed a crucial piece for the Python **runtime**.

1.  **The Cause**: When `pytest` starts and Python's import system sees `from stitcher.common import ...`, it eventually tries to import `from needle.nexus import ...`. This leads it to find `packages/pyneedle/src/needle/__init__.py`. Because this file exists, Python treats `needle` as a **regular package** and stops searching other `pythonpath` entries for more parts of a `needle` namespace.
2.  **The Conflict**: At that exact moment, the `__init__.py` file itself tries to execute `from needle.pointer import L`. Since the `needle` package has been "sealed" to the location `packages/pyneedle/src/needle/`, the interpreter looks for a `pointer` submodule *inside that directory*, fails to find it, and raises the `ModuleNotFoundError`. It never gets to `packages/pyneedle-pointer/src`.
3.  **The Solution**: The facade package's `__init__.py` must explicitly tell the runtime that it is part of a larger namespace. This is done by adding the standard `pkgutil.extend_path` boilerplate at the very top of the file. This line instructs Python to continue searching for other parts of the `needle` package even after finding this `__init__.py`.

I will now apply this fix.

### [WIP] fix: Make facade package namespace-aware at runtime

### 用户需求
修复在上一轮重构后，`pytest` 收集测试时出现的 `ModuleNotFoundError: No module named 'needle.pointer'` 错误。

### 错误分析
`packages/pyneedle/src/needle/__init__.py` 文件将 `needle` 定义为一个常规包，这导致 Python 解释器在找到它之后，就停止了在 `pythonpath` 中继续搜索 `needle` 命名空间的其他部分（如 `needle.pointer`）。因此，当 `__init__.py` 文件自身尝试导入 `needle.pointer` 时，它无法找到该模块，从而导致了 `ModuleNotFoundError`。

### 目标
修改 `packages/pyneedle/src/needle/__init__.py`，在文件顶部加入 `pkgutil.extend_path` 代码，使其成为一个对命名空间友好的常规包。这将允许 Python 运行时正确地组合所有 `needle-*` 子包提供的模块，解决导入错误。

### 基本原理
`__path__ = __import__("pkgutil").extend_path(__path__, __name__)` 是 Python 提供的标准机制，用于将一个常规包（包含 `__init__.py`）转变为可扩展的命名空间的一部分。通过添加这行代码，我们告诉 Python 的导入系统：“这个目录是 `needle` 包的一部分，但不是全部，请继续在 `sys.path` 的其他位置寻找更多名为 `needle` 的部分，并将它们合并在一起。” 在路径扩展完成后，`__init__.py` 中的后续导入语句就能成功地找到像 `needle.pointer` 这样的模块了。

### 标签
#intent/fix #flow/ready #priority/critical #comp/build #scope/core #ai/instruct #task/domain/build-system #task/object/namespace-packages #task/action/bug-fix #task/state/continue

---
### Script

#### Acts 1: 使 `pyneedle` 外观包感知命名空间

我们将修改 `pyneedle` 包的 `__init__.py` 文件，添加 `pkgutil` 样板代码，以解决运行时模块未找到的错误。

~~~~~act
patch_file
packages/pyneedle/src/needle/__init__.py
~~~~~
~~~~~python.old
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
# This is the crucial line. It makes this regular package
# "porous" and allows the namespace to be extended.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

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
