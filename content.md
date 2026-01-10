好的，我们继续执行计划的第二步：将所有与存根生成相关的逻辑迁移到新创建的 `stitcher-stubgen` 包中。

这将是一个纯粹的代码移动和清理操作。迁移后，项目暂时会处于一个无法编译的状态，因为我们还未重新连接 `stitcher-application` 和 `stitcher-stubgen` 之间的依赖关系，这将在第三步中完成。

## [WIP] refactor(arch): Migrate stub generation logic to stitcher-stubgen

### 用户需求

将 `GenerateRunner`、`StubPackageManager` 和 `PythonStubGenerator` 的实现从 `stitcher-application` 和 `stitcher-python-adapter` 包中物理迁移到 `stitcher-stubgen` 包内，并清理原始位置遗留的文件和导出语句。

### 评论

这是整个重构中最核心的“物理迁移”步骤。通过将代码移动到新的领域边界内，我们使架构上的分离变得明确且不可逆。这一步会暂时引入“可控的混乱”（即 broken imports），但这是增量重构过程中的正常现象。它为下一步通过定义清晰的服务接口来修复这些连接创造了必要条件。

### 目标

1.  **迁移 `GenerateRunner`**: 将 `generate.py` 从 `application/runners` 移动到 `stubgen/runners.py`。
2.  **迁移 `StubPackageManager`**: 将 `stub_package_manager.py` 从 `application/services` 移动到 `stubgen`，并将其重命名为 `services.py` 以反映其作为包内服务的角色。
3.  **迁移并整合 `PythonStubGenerator`**: 将 `python-adapter` 中分散的生成器逻辑整合并移动到 `stubgen/generator.py`。
4.  **清理源包**: 从 `stitcher-application` 和 `stitcher-python-adapter` 中移除被迁移的文件及其在 `__init__.py` 中的导出，保持代码库的整洁。

### 基本原理

我们将使用一系列精确的 `move_file`、`write_file`、`delete_file` 和 `patch_file` 操作来完成迁移。`move_file` 用于直接移动文件及其历史。对于生成器，因为它原本分散在两个文件中，我们将读取核心实现，将其写入到新位置的一个统一文件中，然后删除原始文件。最后，通过 `patch_file` 精确地修改 `__init__.py` 文件，移除旧的导出，从而完成“解耦”的第一步。

### 标签

#intent/refine #flow/ready #priority/high #comp/application #comp/python-adapter #comp/stubgen #task/domain/architecture #task/object/stubgen-package #task/action/migration #task/state/continue

---

### Script

#### Acts 1: 迁移 `GenerateRunner`

我们将 `GenerateRunner` 从 `stitcher-application` 移动到 `stitcher-stubgen`，并更新 `application` 的导出。

~~~~~act
move_file
packages/stitcher-application/src/stitcher/app/runners/generate.py
packages/stitcher-stubgen/src/stitcher/stubgen/runners.py
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/__init__.py
~~~~~
~~~~~python.old
from .check import CheckRunner
from .generate import GenerateRunner
from .init import InitRunner
from .pump import PumpRunner
from .transform import TransformRunner
from .coverage import CoverageRunner
from .refactor import RefactorRunner

__all__ = [
    "CheckRunner",
    "GenerateRunner",
    "InitRunner",
    "PumpRunner",
    "TransformRunner",
    "CoverageRunner",
    "RefactorRunner",
]
~~~~~
~~~~~python.new
from .check import CheckRunner
from .init import InitRunner
from .pump import PumpRunner
from .transform import TransformRunner
from .coverage import CoverageRunner
from .refactor import RefactorRunner

__all__ = [
    "CheckRunner",
    "InitRunner",
    "PumpRunner",
    "TransformRunner",
    "CoverageRunner",
    "RefactorRunner",
]
~~~~~

#### Acts 2: 迁移 `StubPackageManager`

同样，我们将 `StubPackageManager` 及其文档从 `stitcher-application` 移动到 `stitcher-stubgen`。

~~~~~act
move_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.py
packages/stitcher-stubgen/src/stitcher/stubgen/services.py
~~~~~

~~~~~act
move_file
packages/stitcher-application/src/stitcher/app/services/stub_package_manager.stitcher.yaml
packages/stitcher-stubgen/src/stitcher/stubgen/services.stitcher.yaml
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/services/__init__.py
~~~~~
~~~~~python.old
from .doc_manager import DocumentManager
from .signature_manager import SignatureManager
from .stub_package_manager import StubPackageManager
from .scanner import ScannerService
from .differ import Differ
from .merger import DocstringMerger

__all__ = [
    "DocumentManager",
    "SignatureManager",
    "StubPackageManager",
    "ScannerService",
    "Differ",
    "DocstringMerger",
]
~~~~~
~~~~~python.new
from .doc_manager import DocumentManager
from .signature_manager import SignatureManager
from .scanner import ScannerService
from .differ import Differ
from .merger import DocstringMerger

__all__ = [
    "DocumentManager",
    "SignatureManager",
    "ScannerService",
    "Differ",
    "DocstringMerger",
]
~~~~~

#### Acts 3: 迁移并整合 `PythonStubGenerator`

我们将 `python-adapter` 中的生成器实现和接口合并，并迁移到 `stitcher-stubgen`。

~~~~~act
write_file
packages/stitcher-stubgen/src/stitcher/stubgen/generator.py
~~~~~
~~~~~python
from typing import List
from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)


class PythonStubGenerator:
    def __init__(self, indent_spaces: int = 4):
        self._indent_str = " " * indent_spaces

    def generate(self, module: ModuleDef) -> str:
        lines = []

        # 1. Module Docstring (Ignored in skeleton generation)

        # 2. Imports (TODO: Pass these through from scanner later)
        if module.imports:
            for imp in module.imports:
                lines.append(imp)
            lines.append("")

        # 2.5. __all__
        if module.dunder_all:
            lines.append(f"__all__ = {module.dunder_all}")
            lines.append("")

        # 3. Module Attributes
        for attr in module.attributes:
            lines.append(self._generate_attribute(attr, 0))
        if module.attributes:
            lines.append("")

        # 4. Functions
        for func in module.functions:
            lines.append(self._generate_function(func, 0))
            lines.append("")

        # 5. Classes
        for cls in module.classes:
            lines.append(self._generate_class(cls, 0))
            lines.append("")

        return "\n".join(lines).strip()

    def _indent(self, level: int) -> str:
        return self._indent_str * level

    def _generate_attribute(
        self, attr: Attribute, level: int, include_value: bool = True
    ) -> str:
        indent = self._indent(level)
        # In .pyi files, we prefer Type Hints:  name: type
        # If value is present (constant), we might output: name: type = value
        # But PEP 484 recommends name: type = ... for constants or just name: type
        # For class attributes, we purposefully exclude values to avoid scoping issues.

        annotation = attr.annotation if attr.annotation else "Any"
        line = f"{indent}{attr.name}: {annotation}"

        if include_value and attr.value:
            line += f" = {attr.value}"

        return line

    def _generate_args(self, args: List[Argument]) -> str:
        # This is tricky because of POSITIONAL_ONLY (/) and KEYWORD_ONLY (*) markers.
        # We need to detect transitions between kinds.

        # Simplified approach for MVP:
        # Just join them. Correctly handling / and * requires looking ahead/behind or state machine.
        # Let's do a slightly better job:

        parts = []

        # Check if we have pos-only args
        has_pos_only = any(a.kind == ArgumentKind.POSITIONAL_ONLY for a in args)
        pos_only_emitted = False

        kw_only_marker_emitted = False

        for i, arg in enumerate(args):
            # Handle POSITIONAL_ONLY end marker
            if has_pos_only and not pos_only_emitted:
                if arg.kind != ArgumentKind.POSITIONAL_ONLY:
                    parts.append("/")
                    pos_only_emitted = True

            # Handle KEYWORD_ONLY start marker
            if arg.kind == ArgumentKind.KEYWORD_ONLY and not kw_only_marker_emitted:
                # If the previous arg was VAR_POSITIONAL (*args), we don't need a bare *
                # Otherwise, we do.
                prev_was_var_pos = (
                    i > 0 and args[i - 1].kind == ArgumentKind.VAR_POSITIONAL
                )
                if not prev_was_var_pos:
                    parts.append("*")
                kw_only_marker_emitted = True

            # Format the argument itself
            arg_str = arg.name
            if arg.kind == ArgumentKind.VAR_POSITIONAL:
                arg_str = f"*{arg.name}"
            elif arg.kind == ArgumentKind.VAR_KEYWORD:
                arg_str = f"**{arg.name}"

            if arg.annotation:
                arg_str += f": {arg.annotation}"

            if arg.default:
                arg_str += f" = {arg.default}"

            parts.append(arg_str)

        # Edge case: If all args were pos-only, we need to append / at the end
        if has_pos_only and not pos_only_emitted:
            parts.append("/")

        return ", ".join(parts)

    def _generate_function(self, func: FunctionDef, level: int) -> str:
        indent = self._indent(level)
        lines = []

        # Decorators
        for dec in func.decorators:
            # dec is raw code like "staticmethod", we need to prepend @
            # But wait, LibCST might or might not include @?
            # In our scanner we did: code_for_node(dec.decorator). So it is just the name/call.
            lines.append(f"{indent}@{dec}")

        # Async
        prefix = "async " if func.is_async else ""

        # Def
        args_str = self._generate_args(func.args)
        ret_str = f" -> {func.return_annotation}" if func.return_annotation else ""

        def_line = f"{indent}{prefix}def {func.name}({args_str}){ret_str}:"

        # Body - Always use ellipsis for skeleton
        lines.append(f"{def_line} ...")

        return "\n".join(lines)

    def _generate_class(self, cls: ClassDef, level: int) -> str:
        indent = self._indent(level)
        lines = []

        # Decorators
        for dec in cls.decorators:
            lines.append(f"{indent}@{dec}")

        # Class Def
        bases_str = ""
        if cls.bases:
            bases_str = f"({', '.join(cls.bases)})"

        lines.append(f"{indent}class {cls.name}{bases_str}:")

        # Body
        has_content = False

        # Docstring (Ignored in skeleton)

        # Attributes
        for attr in cls.attributes:
            # We explicitly DISABLE value generation for class attributes.
            # This prevents bugs where instance attributes initialized from __init__ arguments
            # (e.g. self.x = x) are generated as class attrs with invalid values (x: Any = x).
            lines.append(self._generate_attribute(attr, level + 1, include_value=False))
            has_content = True

        if has_content and cls.methods:
            lines.append("")  # Spacer between attrs and methods

        # Methods
        for i, method in enumerate(cls.methods):
            lines.append(self._generate_function(method, level + 1))
            if i < len(cls.methods) - 1:
                lines.append("")  # Spacer between methods
            has_content = True

        if not has_content:
            lines.append(f"{self._indent(level + 1)}...")

        return "\n".join(lines)
~~~~~

~~~~~act
delete_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/internal/stub_generator.py
~~~~~

~~~~~act
delete_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/generator.py
~~~~~

~~~~~act
run_command
~~~~~
~~~~~
rm -r packages/stitcher-python-adapter/src/stitcher/adapter/python/internal
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python.old
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
~~~~~python.new
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

我们已经成功地将所有存根生成逻辑集中到了 `stitcher-stubgen` 包中。

下一步是**第 3 步：定义新的服务接口**。我将提出一个计划，在 `stitcher-stubgen` 包中创建一个高级别的服务接口（`StubgenService`），它将作为 `stitcher-application` 与存根生成功能交互的唯一、稳定的入口点。这将是我们重新连接系统并修复因本次迁移而产生的 broken imports 的关键。
