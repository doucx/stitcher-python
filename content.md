简要回答：
好的，我们将继续执行 Phase 2，实现 `pyneedle-pointer` 包。这是 `L` (Pointer) 和 `Ls` (PointerSet) 的具体实现层，它将赋予系统“语义代数”的能力。

## [WIP] feat: 实现 pyneedle-pointer 及语义代数核心

### 用户需求
创建 `pyneedle-pointer` 包，实现 `SemanticPointer` (L) 和 `PointerSet` (Ls)。
1.  **SemanticPointer (L)**: 必须实现 `pyneedle-spec` 定义的协议，支持点号访问、动态路径拼接 (`+`, `/`) 和集合分发 (`*`)。
2.  **PointerSet (Ls)**: 必须继承自 Python 原生 `set`，并实现广播机制（对集合内的所有指针批量应用路径运算）。
3.  **文档**: 所有类和方法必须包含详细的文档字符串，为后续 Stitcher 提取做准备。

### 评论
将 `PointerSet` 引入核心是一个重大升级。它允许开发者以声明式的方式操作“语义域”（Semantic Domains），例如一次性获取用户权限矩阵的所有 Key。通过运算符重载实现的代数系统（Algebraic System）将使代码极具表现力。

### 目标
1.  创建 `packages/pyneedle-pointer` 结构。
2.  实现 `src/needle/pointer/core.py`：包含 `SemanticPointer` 类。
3.  实现 `src/needle/pointer/set.py`：包含 `PointerSet` 类。
4.  在 `src/needle/pointer/__init__.py` 中导出 `L` 单例和相关类。

### 基本原理
*   **循环依赖处理**: `SemanticPointer` 的 `__mul__` 操作会产生 `PointerSet`，而 `PointerSet` 包含 `SemanticPointer`。为了保持模块清晰，我们将它们分文件存放，并在方法内部进行延迟导入（Lazy Import）以解决循环依赖。
*   **不可变性**: `SemanticPointer` 依然保持“伪不可变”特性，所有操作均返回新实例，确保线程安全和逻辑无副作用。
*   **继承 Set**: `PointerSet` 直接继承 `set`，使其能无缝接入 Python 的集合生态（如 `union`, `intersection`, `in` 操作），降低学习成本。

### 标签
#intent/build #flow/ready #priority/high
#comp/runtime #concept/state #scope/core
#task/domain/runtime #task/object/pyneedle-pointer #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 初始化包结构
创建目录结构。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/pyneedle-pointer/src/needle/pointer
~~~~~

#### Acts 2: 配置 pyproject.toml
定义依赖关系，确保依赖于 `pyneedle-spec`。

~~~~~act
write_file
packages/pyneedle-pointer/pyproject.toml
~~~~~
~~~~~toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "pyneedle-pointer"
version = "0.1.0"
description = "Standard implementation of Semantic Pointers (L) for PyNeedle."
requires-python = ">=3.10"
dependencies = [
    "pyneedle-spec",
]

[tool.hatch.build.targets.wheel]
packages = ["src/needle"]

[tool.uv.sources]
pyneedle-spec = { workspace = true }
~~~~~

#### Acts 3: 实现 SemanticPointer (L)
这是核心原子。注意 `__mul__` 方法对 `PointerSet` 的延迟导入。

~~~~~act
write_file
packages/pyneedle-pointer/src/needle/pointer/core.py
~~~~~
~~~~~python
from typing import Any, Union, Iterable, TYPE_CHECKING
from needle.spec import SemanticPointerProtocol, PointerSetProtocol

if TYPE_CHECKING:
    from .set import PointerSet


class SemanticPointer(SemanticPointerProtocol):
    """
    Standard implementation of the Semantic Pointer (L).

    It represents a path in the semantic universe.
    Instances are immutable; operations return new instances.
    """

    __slots__ = ("_path",)

    def __init__(self, path: str = ""):
        # Internal storage of the dot-separated path
        self._path = path

    def __getattr__(self, name: str) -> "SemanticPointer":
        """
        Syntactic sugar for path extension via dot notation.
        L.auth.login -> SemanticPointer("auth.login")
        """
        new_path = f"{self._path}.{name}" if self._path else name
        return SemanticPointer(new_path)

    def __str__(self) -> str:
        return self._path

    def __repr__(self) -> str:
        return f"<L: '{self._path}'>" if self._path else "<L: (root)>"

    def __eq__(self, other: Any) -> bool:
        """
        Equality check. Supports string comparison for convenience.
        L.a == "a" is True.
        """
        if isinstance(other, SemanticPointer):
            return self._path == other._path
        return str(other) == self._path

    def __hash__(self) -> int:
        return hash(self._path)

    def _join(self, other: Union[str, "SemanticPointerProtocol"]) -> "SemanticPointer":
        """
        Internal helper to join current path with a suffix.
        Handles dot trimming to avoid double dots.
        """
        suffix = str(other).strip(".")
        if not suffix:
            return self
        
        new_path = f"{self._path}.{suffix}" if self._path else suffix
        return SemanticPointer(new_path)

    def __add__(self, other: Union[str, "SemanticPointerProtocol"]) -> "SemanticPointer":
        """
        Operator '+': Concatenate semantics.
        L.error + 404 -> L.error.404
        """
        return self._join(other)

    def __truediv__(self, other: Union[str, "SemanticPointerProtocol"]) -> "SemanticPointer":
        """
        Operator '/': Path-like composition.
        L.auth / "login" -> L.auth.login
        """
        return self._join(other)

    def __mul__(self, other: Iterable[str]) -> "PointerSetProtocol":
        """
        Operator '*': Dimensions expansion / Distribution.
        Creates a PointerSet by applying suffixes to the current pointer.
        
        L.user * {"name", "age"} -> {L.user.name, L.user.age}
        """
        # Lazy import to avoid circular dependency at module level
        from .set import PointerSet
        
        return PointerSet(self / item for item in other)
~~~~~

#### Acts 4: 实现 PointerSet (Ls)
实现集合广播逻辑。

~~~~~act
write_file
packages/pyneedle-pointer/src/needle/pointer/set.py
~~~~~
~~~~~python
from typing import Set, Iterable, Union, TYPE_CHECKING
from needle.spec import PointerSetProtocol, SemanticPointerProtocol

if TYPE_CHECKING:
    from .core import SemanticPointer


class PointerSet(Set["SemanticPointer"], PointerSetProtocol):
    """
    A collection of Semantic Pointers that supports algebraic broadcasting.
    
    Inherits from built-in set, so standard set operations (union, difference) work as expected.
    """

    def __truediv__(self, other: Union[str, "SemanticPointerProtocol"]) -> "PointerSet":
        """
        Operator '/': Broadcasts the join operation to all members.
        
        {L.a, L.b} / "end" -> {L.a.end, L.b.end}
        """
        # We assume elements are SemanticPointers which support __truediv__
        return PointerSet(p / other for p in self)

    def __add__(self, other: Union[str, "SemanticPointerProtocol"]) -> "PointerSet":
        """
        Operator '+': Broadcasts the add operation to all members.
        Same as __truediv__ but for '+' operator preference.
        """
        return PointerSet(p + other for p in self)

    def __mul__(self, other: Iterable[str]) -> "PointerSet":
        """
        Operator '*': Cartesian Product composition.
        
        {L.a, L.b} * {"1", "2"} -> {L.a.1, L.a.2, L.b.1, L.b.2}
        """
        new_set = PointerSet()
        for p in self:
            # p * other returns a PointerSet (from SemanticPointer.__mul__)
            # We union these sets together
            new_set.update(p * other)
        return new_set
~~~~~

#### Acts 5: 导出 API
在 `__init__.py` 中实例化根对象 `L`，并导出所有内容。

~~~~~act
write_file
packages/pyneedle-pointer/src/needle/pointer/__init__.py
~~~~~
~~~~~python
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .core import SemanticPointer
from .set import PointerSet

# The Global Root Pointer
L = SemanticPointer()

__all__ = ["L", "SemanticPointer", "PointerSet"]
~~~~~

### 下一步建议
我们已经完成了协议定义和原子实现。接下来，我们需要构建 **Phase 3: 内核构建 (pyneedle-nexus)**。这将引入 `OverlayNexus` 和 `ChainMap` 引擎，将这些指针真正连接到数据上。
