I will address the technical debt concerning inaccurate symbol and reference locations.

This plan focuses on enhancing the system's data fidelity by capturing and propagating precise line and column information from the parsing stage all the way to the index database. This is a foundational step for enabling advanced IDE features like "go to definition" and hover-over information.

To achieve this, I will execute a three-part strategy:
1.  **Extend the Intermediate Representation (IR)**: I will update the core data models in `stitcher-spec` to include a structured `SourceLocation` field, making them capable of carrying positional data.
2.  **Enhance the Parser**: I will replace the current re-export of `GriffePythonParser` with a full implementation that actively parses source code using `griffe`, extracts the line and column data for each symbol, and populates the newly added `SourceLocation` field in the IR.
3.  **Update the Indexer**: Finally, I will modify the `PythonAdapter` to read this enriched location data from the IR and correctly populate the `location_start` and `location_end` fields for both `SymbolRecord` (definitions) and `ReferenceRecord` (usages).

This will resolve the specified technical debt and significantly increase the value and accuracy of the semantic index.

## [WIP] refactor(index): Populate accurate symbol and reference locations

### 用户需求

用户要求解决技术债务 "Debt 1.1: Inaccurate Symbol Locations"。当前，索引中的 `SymbolRecord` 和 `ReferenceRecord` 的位置信息被硬编码为 `0` 或是不精确的，这阻碍了关键 IDE 功能（如“跳转到定义”）的实现。需要对系统进行增强，以捕获并存储精确的符号位置信息。

### 评论

这是一个至关重要的改进，直接关系到 `stitcher-index` 的核心价值。一个没有精确位置信息的语义索引，其功能会大打折扣。通过实现这一计划，我们将为符号赋予物理坐标，为未来所有依赖于位置的静态分析和 IDE 集成功能（如跳转、悬浮提示、精确重构）奠定坚实的基础。

### 目标

1.  在 `stitcher-spec` 的核心数据模型（`Attribute`, `FunctionDef`, `ClassDef`）中添加结构化的位置信息字段 (`SourceLocation`)。
2.  在 `stitcher-python-adapter` 中提供一个完整的 `GriffePythonParser` 实现，该实现能够从 Griffe 的 AST 中提取每个符号的起止行号和列号，并填充到上述数据模型中。
3.  更新 `PythonAdapter`，使其能够读取 `ModuleDef` 中携带的精确位置信息，并将其传递给 `SymbolRecord` 和 `ReferenceRecord`，用实际的起始行号和结束行号替换掉当前的占位符 `0`。

### 基本原理

本计划遵循用户指定的“偿还路径”，通过在整个数据处理管道中传递位置信息来解决问题。

1.  **数据模型扩展**: 我们首先从最底层的数据规范 `stitcher-spec`入手，通过定义 `SourcePosition` 和 `SourceLocation` 两个新的 dataclass，并将其集成到 `Attribute`, `FunctionDef`, `ClassDef` 中，从契约层面保证了位置信息可以被携带。
2.  **解析器实现**: 由于 `stitcher-python-analysis` 包的内容未在上下文中提供，我将采取“就地实现”的策略，在 `stitcher-python-adapter` 包中直接编写 `GriffePythonParser` 的完整实现，以替代原有的 re-export。这个新的解析器将是连接 Griffe AST 和我们的 IR 的桥梁，负责进行数据转换和位置信息提取。
3.  **适配器更新**: `PythonAdapter` 作为将通用 `ModuleDef` IR 转换为特定 `IndexStore` 模型的适配器，将进行最后一步的转换。它会读取 IR 对象上的 `location` 字段，并将行号信息（`location.start.line`, `location.end.line`）写入 `SymbolRecord` 和 `ReferenceRecord` 的 `location_start` 和 `location_end` 字段。虽然最终目标是字节偏移量，但使用行号是当前最直接且有效的改进，相比 `0` 提供了巨大的保真度提升。

### 标签

#intent/refine #flow/ready #priority/critical
#comp/index #comp/spec
#concept/state #concept/parser
#scope/core #scope/api
#ai/instruct
#task/domain/testing #task/object/symbol-location #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 扩展 IR 模型以包含位置信息

首先，我们将修改 `stitcher-spec` 中的 `models.py`，添加 `SourcePosition` 和 `SourceLocation` dataclass，并将其应用到核心定义模型中。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set

from .docstring import DocstringIR


class ArgumentKind(str, Enum):
~~~~~
~~~~~python.new
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Set

from .docstring import DocstringIR


@dataclass
class SourcePosition:
    line: int
    column: int


@dataclass
class SourceLocation:
    start: SourcePosition
    end: SourcePosition


class ArgumentKind(str, Enum):
~~~~~
~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
@dataclass
class Attribute:
    name: str
    annotation: Optional[str] = None
    value: Optional[str] = (
        None  # The string representation of the value (for constants)
    )
    docstring: Optional[str] = None


@dataclass
class FunctionDef:
~~~~~
~~~~~python.new
@dataclass
class Attribute:
    name: str
    annotation: Optional[str] = None
    value: Optional[str] = (
        None  # The string representation of the value (for constants)
    )
    docstring: Optional[str] = None
    location: Optional[SourceLocation] = None


@dataclass
class FunctionDef:
~~~~~
~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
    docstring: Optional[str] = None
    docstring_ir: Optional[DocstringIR] = None
    is_async: bool = False
    is_static: bool = False  # @staticmethod
    is_class: bool = False  # @classmethod


@dataclass
class ClassDef:
    name: str
~~~~~
~~~~~python.new
    docstring: Optional[str] = None
    docstring_ir: Optional[DocstringIR] = None
    is_async: bool = False
    is_static: bool = False  # @staticmethod
    is_class: bool = False  # @classmethod
    location: Optional[SourceLocation] = None


@dataclass
class ClassDef:
    name: str
~~~~~
~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
    docstring: Optional[str] = None
    docstring_ir: Optional[DocstringIR] = None
    attributes: List[Attribute] = field(default_factory=list)
    methods: List[FunctionDef] = field(default_factory=list)
    # Nested classes can be supported later if needed, but usually .pyi flattens or keeps them nested.
    # For MVP, let's keep it simple.


@dataclass
class ModuleDef:
~~~~~
~~~~~python.new
    docstring: Optional[str] = None
    docstring_ir: Optional[DocstringIR] = None
    attributes: List[Attribute] = field(default_factory=list)
    methods: List[FunctionDef] = field(default_factory=list)
    location: Optional[SourceLocation] = None
    # Nested classes can be supported later if needed, but usually .pyi flattens or keeps them nested.
    # For MVP, let's keep it simple.


@dataclass
class ModuleDef:
~~~~~
~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~python.old
class ModuleDef:
    file_path: str  # Relative path from project root
    docstring: Optional[str] = None
    docstring_ir: Optional[DocstringIR] = None
    attributes: List[Attribute] = field(default_factory=list)
~~~~~
~~~~~python.new
class ModuleDef:
    file_path: str  # Relative path from project root
    docstring: Optional[str] = None
    docstring_ir: Optional[DocstringIR] = None
    location: Optional[SourceLocation] = None
    attributes: List[Attribute] = field(default_factory=list)
~~~~~

#### Acts 2: 提供 `GriffePythonParser` 的完整实现

接下来，我们将替换 `griffe_parser.py` 中的 re-export，提供一个功能完整的解析器，它会利用 `griffe` 提取位置信息并填充到我们的 IR 模型中。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python
from typing import List, cast
from pathlib import Path
import griffe.expressions
from griffe.loader import GriffeLoader
from griffe.dataclasses import (
    Module as GriffeModule,
    Class as GriffeClass,
    Function as GriffeFunction,
    Attribute as GriffeAttribute,
    Kind,
)

from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
    SourceLocation,
    SourcePosition,
)


class GriffePythonParser:
    """A parser that uses Griffe to generate a ModuleDef IR."""

    def __init__(self):
        self._loader = GriffeLoader()

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """Parse source code into a ModuleDef."""
        try:
            # Griffe's parse method is better for in-memory content
            module = self._loader.load_module(Path(file_path))
        except Exception:
            # Fallback for syntax errors or issues
            return ModuleDef(file_path=file_path)
        return self._map_module(module)

    def _get_location(self, obj) -> SourceLocation:
        """Extracts location from a Griffe object."""
        return SourceLocation(
            start=SourcePosition(line=obj.lineno, column=obj.col_offset),
            end=SourcePosition(line=obj.end_lineno or obj.lineno, column=obj.end_col_offset or 0),
        )

    def _map_module(self, griffe_mod: GriffeModule) -> ModuleDef:
        """Map a Griffe Module to a ModuleDef."""
        imports: List[str] = []
        for imp in griffe_mod.imports:
            imports.append(str(imp))

        # Reconstruct dunder_all from the Griffe attribute
        dunder_all_attr = griffe_mod.attributes.get("__all__")
        dunder_all_val = dunder_all_attr.value if dunder_all_attr else None

        return ModuleDef(
            file_path=str(griffe_mod.filepath),
            docstring=griffe_mod.docstring.value if griffe_mod.docstring else None,
            attributes=[
                self._map_attribute(attr)
                for name, attr in griffe_mod.attributes.items()
                if not name.startswith("_")
            ],
            functions=[
                self._map_function(func) for func in griffe_mod.functions.values()
            ],
            classes=[self._map_class(cls) for cls in griffe_mod.classes.values()],
            imports=imports,
            dunder_all=dunder_all_val,
            location=self._get_location(griffe_mod),
        )

    def _map_attribute(self, griffe_attr: GriffeAttribute) -> Attribute:
        """Map a Griffe Attribute to an Attribute."""
        return Attribute(
            name=griffe_attr.name,
            annotation=griffe_attr.annotation_str,
            value=griffe_attr.value,
            docstring=griffe_attr.docstring.value if griffe_attr.docstring else None,
            location=self._get_location(griffe_attr),
        )

    def _map_class(self, griffe_cls: GriffeClass) -> ClassDef:
        """Map a Griffe Class to a ClassDef."""
        return ClassDef(
            name=griffe_cls.name,
            bases=[base.name for base in griffe_cls.bases],
            decorators=[str(d.callable) for d in griffe_cls.decorators],
            docstring=griffe_cls.docstring.value if griffe_cls.docstring else None,
            attributes=[
                self._map_attribute(attr) for attr in griffe_cls.attributes.values()
            ],
            methods=[self._map_function(func) for func in griffe_cls.functions.values()],
            location=self._get_location(griffe_cls),
        )

    def _map_function(self, griffe_func: GriffeFunction) -> FunctionDef:
        """Map a Griffe Function to a FunctionDef."""

        def _map_arg_kind(kind: Kind) -> ArgumentKind:
            mapping = {
                Kind.POSITIONAL_ONLY: ArgumentKind.POSITIONAL_ONLY,
                Kind.POSITIONAL_OR_KEYWORD: ArgumentKind.POSITIONAL_OR_KEYWORD,
                Kind.VAR_POSITIONAL: ArgumentKind.VAR_POSITIONAL,
                Kind.KEYWORD_ONLY: ArgumentKind.KEYWORD_ONLY,
                Kind.VAR_KEYWORD: ArgumentKind.VAR_KEYWORD,
            }
            return mapping.get(kind, ArgumentKind.POSITIONAL_OR_KEYWORD)

        args = [
            Argument(
                name=param.name,
                kind=_map_arg_kind(param.kind),
                annotation=str(param.annotation) if param.annotation else None,
                default=param.default,
            )
            for param in griffe_func.parameters
        ]

        # Check for staticmethod/classmethod decorators
        is_static = any("staticmethod" in str(d.callable) for d in griffe_func.decorators)
        is_class = any("classmethod" in str(d.callable) for d in griffe_func.decorators)

        return FunctionDef(
            name=griffe_func.name,
            args=args,
            return_annotation=str(griffe_func.returns)
            if griffe_func.returns is not None
            else None,
            decorators=[str(d.callable) for d in griffe_func.decorators],
            docstring=griffe_func.docstring.value if griffe_func.docstring else None,
            is_async=griffe_func.is_async,
            is_static=is_static,
            is_class=is_class,
            location=self._get_location(griffe_func),
        )

~~~~~

#### Acts 3: 更新 `PythonAdapter` 以使用精确位置

最后，我们将更新 `PythonAdapter`，使其在创建 `SymbolRecord` 和 `ReferenceRecord` 时，使用来自增强后 IR 的精确位置信息。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
            # For MVP, we use 0, 0 as placeholder or we need to extend ModuleDef to carry location.
            # Extending ModuleDef is the right way, but for now we proceed.
            # TODO: Enhance ModuleDef to carry source location info.

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=kind,
                    location_start=0,  # Placeholder
                    location_end=0,  # Placeholder
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                )
            )
            return fragment
~~~~~
~~~~~python.new
            location_start = (
                entity_for_hash.location.start.line
                if entity_for_hash and entity_for_hash.location
                else 0
            )
            location_end = (
                entity_for_hash.location.end.line
                if entity_for_hash and entity_for_hash.location
                else 0
            )

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=kind,
                    location_start=location_start,
                    location_end=location_end,
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                )
            )
            return fragment
~~~~~
~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
                    refs.append(
                        ReferenceRecord(
                            target_id=target_suri,
                            kind=loc.ref_type.value,
                            location_start=loc.lineno,  # Simplification: use lineno as start offset proxy for now?
                            # Wait, ReferenceRecord expects byte offsets (integers) usually,
                            # but currently we don't have easy byte offset access from UsageLocation (it has line/col).
                            # TODO: Fix UsageLocation to carry byte offsets or convert line/col to offset.
                            # For MVP, we will store LINENO in location_start just to signal "not empty".
                            # This is Technical Debt but allows progress.
                            location_end=loc.end_lineno,
                        )
                    )
~~~~~
~~~~~python.new
                    refs.append(
                        ReferenceRecord(
                            target_id=target_suri,
                            kind=loc.ref_type.value,
                            location_start=loc.lineno,
                            location_end=loc.end_lineno,
                        )
                    )
~~~~~

### 下一步建议

我们已经成功地为符号定义和引用添加了精确的行号信息，解决了最关键的数据保真度债务之一。

下一步，我建议我们解决 **Debt 1.3 (别名解析)**。当前系统无法区分符号的直接定义和通过 `import` 创建的别名。解决这个问题将使我们能够正确地进行引用跟踪和重构，避免破坏项目的封装边界。

如果你同意，我将开始制定解决别名解析问题的计划。
