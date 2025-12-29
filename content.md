## [WIP] feat: 阶段一 - 定义 OperatorProtocol 并实现基础算子

### 用户需求
根据 [实施路线图：PyNeedle 函数式内核演进](../../archive/路线图/实施路线图：PyNeedle%20函数式内核演进.md) 的第一阶段要求：
1.  在 `pyneedle-spec` 中定义核心协议 `OperatorProtocol`。
2.  在 `pyneedle-runtime` 中实现基础配置算子 `DictOperator`。
3.  在 `pyneedle-runtime` 中实现基础执行算子 `FileSystemOperator`。

### 评论
这是 PyNeedle 架构向函数式内核演进的关键第一步。我们将引入“算子 (Operator)”这一核心概念，它统一了配置和执行的接口。具体的实现遵循“构造即配置，调用即执行”的原则。

### 目标
1.  **定义协议**: 创建 `OperatorProtocol`，规范所有算子的 `__call__` 行为。
2.  **实现 DictOperator**: 一个简单的、基于内存字典的配置提供者。
3.  **实现 FileSystemOperator**: 一个纯粹的、基于文件系统的资源执行器，支持按需加载（Lazy Loading）。

### 基本原理
*   **OperatorProtocol**: 使用 Python 的 `Protocol` 定义鸭子类型接口，确保系统的松耦合与类型安全。
*   **DictOperator**: 作为配置管道的起点，它将静态字典转换为可流动的配置数据。
*   **FileSystemOperator**: 不同于旧的 `FileSystemLoader`（它一次性扫描所有文件），新的 Operator 将专注于**单一职责**和**即时查找**。它接收一个明确的根目录，并根据 SemanticPointer 的第一个分段（Segment）来定位 JSON 文件，这不仅提高了性能（无需启动时扫描），也使得逻辑更加清晰。它将复用现有的 `JsonHandler` 来处理文件解析。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #comp/spec #concept/executor #scope/core #ai/instruct #task/domain/core #task/object/operators #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 定义核心协议

首先在 `pyneedle-spec` 中定义 `OperatorProtocol`。这是一个泛型协议，允许算子接受任意键并返回任意值，但在实践中我们主要使用 `SemanticPointer -> str` (执行器) 和 `str -> Any` (配置器)。

~~~~~act
patch_file
packages/pyneedle-spec/src/needle/spec/protocols.py
~~~~~
~~~~~python.old
    def reload(self, domain: str | None = None) -> None: ...
~~~~~
~~~~~python.new
    def reload(self, domain: str | None = None) -> None: ...


class OperatorProtocol(Protocol):
    """
    The unified interface for all operators (Config, Factory, Executor).
    An operator is an object that is configured at initialization and
    generates a result when called.
    """

    def __call__(self, key: Any) -> Any: ...
~~~~~

~~~~~act
write_file
packages/pyneedle-spec/src/needle/spec/protocols.stitcher.yaml
~~~~~
~~~~~yaml
"FileHandlerProtocol": |-
  Protocol for file handlers that can parse specific formats like JSON, YAML, etc.
"FileHandlerProtocol.load": |-
  Parses the file and returns its content as a dictionary.
"FileHandlerProtocol.match": |-
  Returns True if this handler can process the given file path.
"NexusProtocol": |-
  Defines the contract for the runtime central hub (Nexus).
"NexusProtocol.reload": |-
  Clears internal caches and forces a reload of resources.

  Args:
      domain: If provided, only reload that specific domain.
            If None, reload all.
"OperatorProtocol": |-
  The unified interface for all operators in the functional kernel.
  
  Unlike Loaders which mix configuration, policy, and fetching, 
  Operators follow the "Builder is the Product" philosophy:
  - __init__: Handles configuration (context injection).
  - __call__: Handles execution (stateless transformation).
"OperatorProtocol.__call__": |-
  Executes the operator's logic.
  
  For Config Operators: key=str, returns Any.
  For Factory Operators: key=SemanticPointer, returns Operator.
  For Executor Operators: key=SemanticPointer, returns str.
"PointerSetProtocol": |-
  Defines the contract for a set of Semantic Pointers (Ls).

  It represents a 'Semantic Domain' or 'Surface' rather than a single point.
"PointerSetProtocol.__add__": |-
  Operator '+': Broadcasts the add operation to all members.
"PointerSetProtocol.__iter__": |-
  Iterating over the set yields individual SemanticPointers.
"PointerSetProtocol.__mul__": |-
  Operator '*': Broadcasts a cartesian product operation.
"PointerSetProtocol.__or__": |-
  Operator '|': Unions two PointerSets.
"PointerSetProtocol.__truediv__": |-
  Operator '/': Broadcasts the join operation to all members of the set.
  Example: {L.a, L.b} / "end" -> {L.a.end, L.b.end}
"ResourceLoaderProtocol": |-
  Defines the contract for loading raw resource data.
"ResourceLoaderProtocol.load": |-
  Loads resources for a specific domain.

  Args:
      domain: The target domain (e.g., 'en', 'zh', 'dark_theme').

  Returns:
      A dictionary mapping Fully Qualified Names (FQNs) to values.
"SemanticPointerProtocol": |-
  Defines the contract for a Semantic Pointer (L).

  A Semantic Pointer is a recursive, immutable reference to a semantic location.
  It serves as the primary key for addressing resources in the Nexus.
"SemanticPointerProtocol.__add__": |-
  Operator '+': Joins the pointer with a string or another pointer.
  Example: L.auth + "login" -> L.auth.login
"SemanticPointerProtocol.__eq__": |-
  Pointers must be comparable with strings and other pointers.
"SemanticPointerProtocol.__getattr__": |-
  Creates a new pointer extended by the attribute name.
  Example: L.auth -> "auth"
"SemanticPointerProtocol.__hash__": |-
  Pointers must be hashable to be used as dictionary keys.
"SemanticPointerProtocol.__mul__": |-
  Operator '*': Distributes the pointer over a set of suffixes, creating a PointerSet.
  Example: L.auth * {"read", "write"} -> {L.auth.read, L.auth.write}
"SemanticPointerProtocol.__str__": |-
  Returns the fully qualified string representation of the pointer.
  Example: "auth.login.success"
"SemanticPointerProtocol.__truediv__": |-
  Operator '/': Joins the pointer with a string or another pointer (path-like syntax).
  Example: L.auth / "login" -> L.auth.login
"T_Pointer": |-
  A TypeVar used for covariant type hinting in the SemanticPointerProtocol.
"WritableResourceLoaderProtocol": |-
  Extends ResourceLoader with writing and location capabilities.
"WritableResourceLoaderProtocol.locate": |-
  Returns the physical path where a resource would be stored.
"WritableResourceLoaderProtocol.put": |-
  Persists a value for a specific pointer and domain.
~~~~~

#### Acts 2: 导出 OperatorProtocol

~~~~~act
patch_file
packages/pyneedle-spec/src/needle/spec/__init__.py
~~~~~
~~~~~python.old
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
~~~~~python.new
    NexusProtocol,
    OperatorProtocol,
)

__all__ = [
    "SemanticPointerProtocol",
    "PointerSetProtocol",
    "ResourceLoaderProtocol",
    "WritableResourceLoaderProtocol",
    "NexusProtocol",
    "OperatorProtocol",
]
~~~~~

#### Acts 3: 创建 Operators 模块与 DictOperator

DictOperator 是最简单的算子，用于从内存字典中查找值。

~~~~~act
run_command
~~~~~
~~~~~
mkdir -p packages/pyneedle-runtime/src/needle/operators
~~~~~

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/operators/__init__.py
~~~~~
~~~~~python
from .dict_operator import DictOperator
from .fs_operator import FileSystemOperator

__all__ = ["DictOperator", "FileSystemOperator"]
~~~~~

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/operators/dict_operator.py
~~~~~
~~~~~python
from typing import Any, Dict, Union
from needle.spec import OperatorProtocol, SemanticPointerProtocol


class DictOperator(OperatorProtocol):
    """
    A Config Operator that provides values from an in-memory dictionary.
    """

    def __init__(self, data: Dict[str, Any]):
        self._data = data

    def __call__(self, key: Union[str, SemanticPointerProtocol]) -> Any:
        return self._data.get(str(key))
~~~~~

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/operators/dict_operator.stitcher.yaml
~~~~~
~~~~~yaml
"DictOperator": |-
  A simple operator that wraps a dictionary.
  Primarily used as a Config Operator to provide static configuration values
  to the pipeline, or for mocking data in tests.
"DictOperator.__call__": |-
  Retrieves a value from the dictionary using the string representation of the key.
"DictOperator.__init__": |-
  Initializes the operator with a source dictionary.
~~~~~

#### Acts 4: 实现 FileSystemOperator

FileSystemOperator 是核心执行器，它基于懒加载策略。与一次性扫描整个目录树的 `FileSystemLoader` 不同，它利用 `SemanticPointer` 的结构来精确定位文件。
规则：`L.part1.part2` -> 从 `root/part1.json` 中查找键 `part2`。

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/operators/fs_operator.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional, Union, Dict, Any
from needle.spec import OperatorProtocol, SemanticPointerProtocol
from needle.loaders.json_handler import JsonHandler


class FileSystemOperator(OperatorProtocol):
    """
    An Executor Operator that loads resources from a specific directory on demand.
    """

    def __init__(self, root: Union[str, Path]):
        self.root = Path(root)
        self._handler = JsonHandler()
        # Cache for loaded file contents: filename -> flat_dict
        self._file_cache: Dict[str, Dict[str, Any]] = {}

    def __call__(self, pointer: Union[str, SemanticPointerProtocol]) -> Optional[str]:
        key = str(pointer)
        if not key:
            return None

        parts = key.split(".")
        filename = parts[0]
        # The key to look up inside the file (rest of the pointer)
        # If key is "app", inner_key is None (or we can decide behavior)
        # Assuming standard behavior: L.app.title -> file: app.json, key: title
        inner_key = ".".join(parts[1:]) if len(parts) > 1 else None

        # 1. Ensure file is loaded
        if filename not in self._file_cache:
            file_path = self.root / f"{filename}.json"
            if file_path.is_file():
                # Load and flatten using existing handler logic
                self._file_cache[filename] = self._handler.load(file_path)
            else:
                self._file_cache[filename] = {}

        # 2. Retrieve value
        data = self._file_cache[filename]
        
        # If no inner key, checking for existence of file/module itself?
        # For now, we only support leaf retrieval inside files.
        if inner_key:
            val = data.get(inner_key)
            return str(val) if val is not None else None
        
        # Accessing the file root directly (L.app) is not typically a string value,
        # but could be supported if we want to return a sub-dict? 
        # But OperatorProtocol usually implies retrieving a specific resource unit (str).
        # Let's return None for now if it's not a leaf node string.
        return None
~~~~~

~~~~~act
write_file
packages/pyneedle-runtime/src/needle/operators/fs_operator.stitcher.yaml
~~~~~
~~~~~yaml
"FileSystemOperator": |-
  A high-performance, lazy-loading Executor Operator for the file system.

  It maps `SemanticPointer` paths to file system paths using a standard convention:
  The first segment of the pointer determines the filename (`{segment}.json`),
  and the remaining segments determine the key within that file.
"FileSystemOperator.__call__": |-
  Resolves a pointer to a string value.

  Example:
  `op(L.app.title)` -> Loads `root/app.json` -> Returns value of key "title".

  Returns `None` if the file does not exist or the key is not found.
"FileSystemOperator.__init__": |-
  Initializes the operator with a specific root directory.
  This directory is usually a specific language folder (e.g., `.../assets/en`).
~~~~~

#### Acts 5: 添加测试

最后，我们需要验证这两个新算子的行为。

~~~~~act
write_file
packages/pyneedle-runtime/tests/test_operators.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from needle.pointer import L
from needle.operators import DictOperator, FileSystemOperator


def test_dict_operator_retrieves_values():
    data = {"app.title": "My App", "simple_key": "Value"}
    op = DictOperator(data)

    assert op("app.title") == "My App"
    assert op(L.app.title) == "My App"
    assert op("simple_key") == "Value"
    assert op("missing") is None


def test_fs_operator_lazy_loading(tmp_path: Path):
    # Arrange
    root = tmp_path / "assets"
    root.mkdir()
    
    # Create app.json
    (root / "app.json").write_text('{"title": "My App", "ver": {"major": 1}}', encoding="utf-8")
    
    op = FileSystemOperator(root)

    # Act & Assert
    
    # 1. Simple fetch
    # This should trigger load of app.json
    assert op(L.app.title) == "My App"

    # 2. Nested key fetch (JsonHandler flattens nested dicts)
    # "ver": {"major": 1} -> "ver.major": "1"
    assert op(L.app.ver.major) == "1"

    # 3. Missing file
    assert op(L.auth.login) is None
    
    # 4. Missing key in existing file
    assert op(L.app.description) is None


def test_fs_operator_caching(tmp_path: Path):
    root = tmp_path / "assets"
    root.mkdir()
    f = root / "data.json"
    f.write_text('{"key": "v1"}', encoding="utf-8")

    op = FileSystemOperator(root)
    
    # First access loads v1
    assert op(L.data.key) == "v1"

    # Externally change file
    f.write_text('{"key": "v2"}', encoding="utf-8")

    # Second access should still return cached v1
    assert op(L.data.key) == "v1"
~~~~~

~~~~~act
write_file
packages/pyneedle-runtime/tests/test_operators.stitcher.yaml
~~~~~
~~~~~yaml
"test_dict_operator_retrieves_values": |-
  Tests that DictOperator correctly retrieves values using both strings and SemanticPointers.
"test_fs_operator_caching": |-
  Tests that FileSystemOperator caches loaded files in memory to reduce I/O.
"test_fs_operator_lazy_loading": |-
  Tests that FileSystemOperator correctly loads values from JSON files on demand,
  handling flat and nested keys.
~~~~~

### 下一步建议
实施阶段一的 Part 2：**重构 OverlayNexus**。这将涉及修改 `packages/pyneedle-nexus`，引入新的 `OverlayOperator` 并从 `OverlayNexus` 中提取逻辑。
