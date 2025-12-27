简要回答
这是一个经典的“命名空间包冲突”问题。`pyneedle` 使用了显式的 `pkgutil` 命名空间风格，而 `pyneedle-runtime` 和 `pyneedle-nexus` 似乎缺失了对应的 `src/needle/__init__.py` 文件（或者变成了隐式命名空间），导致 Python 的导入系统在遍历 `needle` 命名空间时发生混乱（`KeyError: 'needle'`）。

此外，`needle.loaders` 作为一个目录被导入，也需要一个 `__init__.py` 将其标识为常规包。

我将为这些子包补全缺失的 `__init__.py` 文件。

## [WIP] fix(runtime): 修复命名空间包冲突与缺失的初始化文件

### 错误分析
**KeyError: 'needle'**: 发生在 `importlib` 内部。
**原因**: Python 不允许“显式命名空间包”（包含 `__init__.py` 和 `pkgutil`）与“隐式命名空间包”（无 `__init__.py`）混合使用。`pyneedle` 主包使用了显式风格，因此所有贡献 `needle` 命名空间的子包（如 `runtime`, `nexus`）必须同样包含带有 `pkgutil.extend_path` 的 `__init__.py`。

### 用户需求
修复导入错误，使测试套件能正常加载 `needle.loaders`。

### 目标
1.  在 `packages/pyneedle-runtime/src/needle/__init__.py` 中添加 `pkgutil` 命名空间声明。
2.  在 `packages/pyneedle-nexus/src/needle/__init__.py` 中添加 `pkgutil` 命名空间声明。
3.  创建 `packages/pyneedle-runtime/src/needle/loaders/__init__.py` 以将 `loaders` 标识为常规 Python 包。

### 标签
#intent/fix #flow/ready #priority/critical #comp/build #scope/core #ai/instruct #task/domain/core-runtime #task/object/namespace-pkg #task/action/fix #task/state/continue

---

### Script

#### Acts 1: 修复 PyNeedle Runtime 的命名空间
为 `runtime` 包添加顶层 `__init__.py`。

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~

#### Acts 2: 修复 PyNeedle Runtime Loaders 包
将 `loaders` 目录标记为 Python 包。

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/loaders/__init__.py
~~~~~
~~~~~python
from .fs_loader import FileSystemLoader
from .json_handler import JsonHandler
from .protocols import FileHandlerProtocol

__all__ = ["FileSystemLoader", "JsonHandler", "FileHandlerProtocol"]
~~~~~

#### Acts 3: 修复 PyNeedle Nexus 的命名空间
为 `nexus` 包添加顶层 `__init__.py`，防止同样的错误发生在 Nexus 模块上。

~~~~~act
write_file
packages/pyneedle-nexus/src/needle/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)
~~~~~
