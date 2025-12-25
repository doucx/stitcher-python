简要回答：
IR 数据模型（中间表示）是连接 Scanner 和 Generator 的核心契约。定义完这个模型后，我们将正式进入“逻辑密集区”（Scanner 的 AST 解析），那正是引入 TDD 的**最佳**时机。

## [WIP] feat: 定义 Stitcher 核心 IR 数据模型 (Spec)

### 用户需求
用户需要实现 `stitcher-spec` 包中的核心数据模型。这些模型将充当 Stitcher 的“通用语言”，承载从源代码解析出的结构信息（如类、函数、参数、文档），并作为生成 `.pyi` 和 YAML 文件的基础。

### 评论
Spec 层是纯数据定义，逻辑密度低，因此我们直接通过设计良好的 `dataclasses` 来实现，暂不需要 TDD。
**关于 TDD 的切入点**：
一旦 Spec 定义完成，我们进入 **`stitcher-scanner` (AST 解析)** 阶段时，**必须**立即切换到 TDD 模式。
*   **原因**：AST 解析涉及极其复杂的边界情况（`async` 关键字、复杂的 Type Hints、`*args/**kwargs`、装饰器堆叠等）。
*   **方法**：我们将不再直接写解析器代码，而是先写“包含各种奇葩 Python 代码片段”的测试用例，断言解析器能将其转换为正确的 IR 对象。

### 目标
1.  在 `packages/stitcher-spec/src/stitcher/spec/models.py` 中定义完整的 IR 模型层级。
2.  模型应涵盖：`Module`, `Class`, `Function`, `Attribute` (变量), `Argument` (参数)。
3.  确保模型能够存储“源代码签名”和“文档字符串”的分离状态（虽然在 IR 中它们在一起，但在逻辑上我们要意识到它们来源可能不同）。

### 基本原理
我们使用 Python 标准库的 `@dataclass` 来定义模型，因为它提供了开箱即用的类型安全和易读性，且易于序列化。模型的结构将镜像 Python 的语义结构，但去除了具体的实现体（Body），只保留接口（Interface）和元数据（Metadata）。

### 标签
#intent/architect #flow/ready #priority/high
#comp/spec #concept/ir #scope/core #ai/instruct
#task/domain/spec #task/object/ir-models #task/action/define
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 定义核心 IR 模型
我们将创建一个包含完整层级结构的文件。核心设计决策包括：
*   **Argument**: 需要区分位置参数、关键字参数等类型。
*   **Function**: 需要支持 `is_async` 标志，以及装饰器列表。
*   **Class**: 需要基类（Bases）列表。
*   **Docstring**: 所有主要实体都必须有一个可选的 `docstring` 字段。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Union


class ArgumentKind(str, Enum):
    """Corresponds to inspect._ParameterKind."""
    POSITIONAL_ONLY = "POSITIONAL_ONLY"
    POSITIONAL_OR_KEYWORD = "POSITIONAL_OR_KEYWORD"
    VAR_POSITIONAL = "VAR_POSITIONAL"  # *args
    KEYWORD_ONLY = "KEYWORD_ONLY"
    VAR_KEYWORD = "VAR_KEYWORD"      # **kwargs


@dataclass
class Argument:
    """Represents a function or method argument."""
    name: str
    kind: ArgumentKind
    annotation: Optional[str] = None
    default: Optional[str] = None  # The string representation of the default value
    

@dataclass
class Attribute:
    """Represents a module-level or class-level variable."""
    name: str
    annotation: Optional[str] = None
    value: Optional[str] = None    # The string representation of the value (for constants)
    docstring: Optional[str] = None


@dataclass
class FunctionDef:
    """Represents a function or method definition."""
    name: str
    args: List[Argument] = field(default_factory=list)
    return_annotation: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    is_async: bool = False
    is_static: bool = False  # @staticmethod
    is_class: bool = False   # @classmethod


@dataclass
class ClassDef:
    """Represents a class definition."""
    name: str
    bases: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    attributes: List[Attribute] = field(default_factory=list)
    methods: List[FunctionDef] = field(default_factory=list)
    # Nested classes can be supported later if needed, but usually .pyi flattens or keeps them nested.
    # For MVP, let's keep it simple.


@dataclass
class ModuleDef:
    """Represents a parsed Python module (a single .py file)."""
    file_path: str  # Relative path from project root
    docstring: Optional[str] = None
    attributes: List[Attribute] = field(default_factory=list)
    functions: List[FunctionDef] = field(default_factory=list)
    classes: List[ClassDef] = field(default_factory=list)
    # Imports are tricky. For .pyi generation, we often need to preserve them 
    # or recreate them based on used types. 
    # For MVP, we might treat imports as raw lines or simple structures.
    imports: List[str] = field(default_factory=list) 

~~~~~

#### Acts 2: 暴露模型
更新 `__init__.py` 以便其他包可以方便地导入。

~~~~~act
write_file
packages/stitcher-spec/src/stitcher/spec/__init__.py
~~~~~
~~~~~python
# This must be the very first line to allow this package to coexist with other
# namespace packages in editable installs.
__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from .models import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)

__all__ = [
    "Argument",
    "ArgumentKind",
    "Attribute",
    "ClassDef",
    "FunctionDef",
    "ModuleDef",
]
~~~~~

### 下一步建议

**战略转折点：启动 TDD**

现在 Spec 已经定义好了，我们即将开始开发 `stitcher-scanner`。这是项目的第一个复杂逻辑挑战。

建议在这个点放慢速度，按照以下 **TDD 流程** 进行：

1.  **创建测试骨架**: 在 `tests/unit/scanner/` 下创建一个测试文件。
2.  **编写失败的测试 (Red)**:
    *   构造一段简单的 Python 源代码字符串（例如 `def hello(name: str) -> None: ...`）。
    *   调用尚未实现的 `Scanner.parse(code)`。
    *   断言它返回了一个 `ModuleDef`，其中包含一个正确的 `FunctionDef` 对象。
3.  **实现 Scanner (Green)**: 在 `stitcher-scanner` 中编写 AST 访问逻辑，使测试通过。
4.  **逐步增加复杂度 (Refactor/Iterate)**:
    *   添加带默认值的参数测试。
    *   添加带装饰器的测试。
    *   添加类的解析测试。
    *   添加 `async` 函数的测试。

如果你同意，接下来的计划将直接创建测试用例，而不是实现代码。
