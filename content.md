当然，我们立即开始。第一步是搭建 `GriffePythonParser` 的基础结构。

我将创建 `griffe_parser.py` 文件，在其中定义一个遵循 `LanguageParserProtocol` 协议的 `GriffePythonParser` 类，并为其 `parse` 方法提供一个骨架实现。最后，我会将这个新类从 `stitcher-python-adapter` 包中导出，使其可以被系统其他部分发现和使用。

## [WIP] feat: 创建 GriffePythonParser 的骨架实现

### 用户需求
开始实施 Griffe 集成技术提案的第一步：创建新的解析器类 `GriffePythonParser`，并为其搭建基础框架。

### 评论
这是一个关键的起始步骤，完全符合我们在技术提案中制定的、基于适配器模式的非侵入式集成策略。通过首先建立类的骨架并导出它，我们为后续逐步填充复杂的 Griffe-to-IR 映射逻辑奠定了坚实的基础。

### 目标
1.  在 `stitcher-python-adapter` 包中创建 `griffe_parser.py` 文件。
2.  定义 `GriffePythonParser` 类，确保它实现了 `LanguageParserProtocol` 协议。
3.  在 `parse` 方法中，实现调用 Griffe 解析器的基本逻辑，并为后续的映射工作留下清晰的 `TODO` 注释。
4.  更新 `stitcher-python-adapter` 包的 `__init__.py` 文件，以导出新的 `GriffePythonParser` 类。

### 基本原理
我们采用“结构先行”的方法。首先创建文件和类定义，可以确保我们的新组件在架构上处于正确的位置。`parse` 方法的骨架实现将作为核心映射逻辑的容器，我们将在接下来的步骤中逐步填充它。这种增量式的方法使得每一步的变更都小而可控。

### 标签
#intent/build #flow/ready #priority/high #comp/python-adapter #concept/parser #scope/core #ai/instruct #task/domain/parsing #task/object/griffe-adapter #task/action/implementation #task/state/begin

---
### Script

#### Acts 1: 创建 Griffe 解析器的骨架文件

首先，我们创建 `griffe_parser.py` 文件。它将包含 `GriffePythonParser` 类的定义，该类实现了 `LanguageParserProtocol`，并有一个基本的 `parse` 方法来调用 Griffe 加载器。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python
import griffe.dataclasses as dc
import griffe.loader
from stitcher.spec import (
    ModuleDef,
    FunctionDef,
    ClassDef,
    Argument,
    ArgumentKind,
    Attribute,
    LanguageParserProtocol,
)


class GriffePythonParser(LanguageParserProtocol):
    """A Python parser implementation powered by Griffe."""

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """
        Parses Python source code using Griffe and maps the result to
        the Stitcher IR (ModuleDef).
        """
        # Griffe can work with in-memory code, but needs a module name.
        # We derive a plausible module name from the file path.
        module_name = (
            file_path.replace("/", ".").removesuffix(".py") if file_path else "dynamic_module"
        )

        griffe_module = griffe.loader.load_module(
            module_name,
            filepath=file_path or None,  # Pass None if not provided
            code=source_code,
        )

        # TODO: Implement the full mapping logic from griffe.dataclasses.Module
        # to stitcher.spec.ModuleDef.

        # Placeholder implementation for the skeleton:
        return ModuleDef(
            file_path=file_path,
            docstring=griffe_module.docstring.value if griffe_module.docstring else None,
            # functions=[self._map_function(f) for f in griffe_module.functions.values()],
            # classes=[self._map_class(c) for c in griffe_module.classes.values()],
            # attributes=[self._map_attribute(a) for a in griffe_module.attributes.values()],
        )

    def _map_function(self, griffe_func: dc.Function) -> FunctionDef:
        # TODO: Map Griffe function to FunctionDef
        pass

    def _map_class(self, griffe_class: dc.Class) -> ClassDef:
        # TODO: Map Griffe class to ClassDef
        pass

    def _map_attribute(self, griffe_attr: dc.Attribute) -> Attribute:
        # TODO: Map Griffe attribute to AttributeDef
        pass
~~~~~

#### Acts 2: 从适配器包中导出新解析器

现在，我们将新的 `GriffePythonParser` 添加到包的 `__init__.py` 中，使其可以被 CLI 的工厂函数导入和使用。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python.old
from .inspector import parse_plugin_entry, InspectionError

__all__ = [
    "PythonParser",
    "PythonTransformer",
    "PythonStubGenerator",
    "PythonFingerprintStrategy",
    "parse_plugin_entry",
    "InspectionError",
]
~~~~~
~~~~~python.new
from .inspector import parse_plugin_entry, InspectionError
from .griffe_parser import GriffePythonParser

__all__ = [
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
我们已经成功创建了 `GriffePythonParser` 的基础结构。下一步是开始实现核心的映射逻辑。我建议我们从最简单的部分开始：

1.  **实现 `_map_attribute`**: 将 Griffe 的 `Attribute` 对象映射到我们的 `stitcher.spec.Attribute` IR。
2.  **在 `parse` 方法中启用 attributes 的映射**: `attributes=[self._map_attribute(a) for a in griffe_module.attributes.values()]`。

这将允许我们逐步构建和验证转换逻辑。如果您同意，我将生成执行此操作的计划。
