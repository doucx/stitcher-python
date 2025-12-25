好的，测试失败，我们已进入 **GREEN** 阶段。

现在，我们将实现 `StubGenerator` 的核心逻辑。这涉及到遍历 `ModuleDef` IR 对象的各个部分，并根据 `.pyi` 文件的语法规则，将它们格式化为字符串。我们将创建一系列辅助方法来处理不同的 IR 节点（如函数、类、属性），以保持代码的清晰和模块化。

## [WIP] feat(io): 实现 StubGenerator 逻辑 (Green Phase)

### 用户需求
为了通过 `test_generate_simple_pyi` 测试，需要在 `stitcher-io` 中实现 `StubGenerator.generate` 方法的完整逻辑。该方法必须能够将一个 `ModuleDef` 对象正确地转换为符合 `.pyi` 语法规范的字符串。

### 评论
**实现策略**：
我们将采用“分而治之”的策略，为每一种 IR 节点（`FunctionDef`, `ClassDef`, `Attribute`, `Argument`）编写一个专门的生成器辅助方法。
*   **Indentation**: 所有辅助方法都会接收一个 `indent_level` 参数，以正确处理类内部的缩进。
*   **Function Body**: 我们将遵循 `.pyi` 的惯例：
    *   如果函数/方法有文档字符串，则函数体为 `:\n    """docstring"""\n    ...`
    *   如果函数/方法没有文档字符串，则函数体为 `: ...`，以保持简洁。
*   **Attributes**: 在 `.pyi` 文件中，我们只声明变量的类型（`NAME: type`），而不包括其值。

### 目标
1.  完整实现 `packages/stitcher-io/src/stitcher/io/stub_generator.py`。
2.  创建 `_generate_function`, `_generate_class`, `_generate_attribute` 等辅助方法。
3.  确保代码能够处理 `async`、装饰器、参数默认值、基类等所有测试用例中涉及的元素。
4.  运行测试，确保变绿。

### 基本原理
这个过程本质上是一个简单的“代码生成器”或“编译器后端”。它将结构化的中间表示（IR）转换为特定目标语言（`.pyi` 语法）的文本表示。

### 标签
#intent/build #flow/ready #priority/high
#comp/io #concept/generator #scope/core #ai/instruct
#task/domain/implementation #task/object/stub-generator #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 实现 StubGenerator
我们将完整地重写 `stub_generator.py` 文件。

~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python
from typing import List
from stitcher.spec import (
    ModuleDef,
    FunctionDef,
    ClassDef,
    Attribute,
    Argument,
    ArgumentKind,
)


class StubGenerator:
    def generate(self, module: ModuleDef) -> str:
        """
        Generates the content of a .pyi file from a ModuleDef IR.
        """
        parts = []

        if module.docstring:
            parts.append(f'"""{module.docstring}"""')

        if module.attributes:
            if parts:
                parts.append("")  # Add a blank line
            for attr in module.attributes:
                parts.append(self._generate_attribute(attr))
        
        if module.functions:
            for func in module.functions:
                if parts:
                    parts.append("\n")
                parts.append(self._generate_function(func))

        if module.classes:
            for cls in module.classes:
                if parts:
                    parts.append("\n")
                parts.append(self._generate_class(cls))

        return "\n".join(parts)

    def _generate_attribute(self, attr: Attribute, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        if attr.annotation:
            return f"{indent}{attr.name}: {attr.annotation}"
        return f"{indent}{attr.name}: ..."

    def _generate_arguments(self, args: List[Argument]) -> str:
        parts = []
        for arg in args:
            part = arg.name
            if arg.annotation:
                part += f": {arg.annotation}"
            if arg.default:
                part += f" = {arg.default}"
            parts.append(part)
        return ", ".join(parts)

    def _generate_function(self, func: FunctionDef, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        lines = []

        # Decorators
        for dec in func.decorators:
            lines.append(f"{indent}{dec}")
        
        # Signature
        signature = f"{indent}"
        if func.is_async:
            signature += "async "
        signature += f"def {func.name}({self._generate_arguments(func.args)})"
        if func.return_annotation:
            signature += f" -> {func.return_annotation}"
        
        # Body
        if func.docstring:
            signature += ":"
            lines.append(signature)
            docstring_indent = "    " * (indent_level + 1)
            lines.append(f'{docstring_indent}"""{func.docstring}"""')
            lines.append(f"{docstring_indent}...")
        else:
            signature += ": ..."
            lines.append(signature)

        return "\n".join(lines)

    def _generate_class(self, cls: ClassDef, indent_level: int = 0) -> str:
        indent = "    " * indent_level
        lines = []

        # Class header
        bases = f"({', '.join(cls.bases)})" if cls.bases else ""
        lines.append(f"{indent}class {cls.name}{bases}:")

        child_indent_level = indent_level + 1
        child_indent = "    " * child_indent_level
        
        # Docstring
        if cls.docstring:
            lines.append(f'{child_indent}"""{cls.docstring}"""')

        # Attributes and methods
        body_parts = []
        if cls.attributes:
            for attr in cls.attributes:
                body_parts.append(self._generate_attribute(attr, child_indent_level))

        if cls.methods:
            for method in cls.methods:
                if body_parts:
                     # Add a blank line between attributes and first method, or between methods
                     body_parts.append("")
                body_parts.append(self._generate_function(method, child_indent_level))
        
        if not body_parts:
            lines.append(f"{child_indent}...")
        else:
            lines.extend(body_parts)

        return "\n".join(lines)
~~~~~

### 下一步建议
运行 `pytest`。如果通过，我们的 `stitcher-io` 模块的核心功能就已经完成。

接下来，我们将进入**任务 1.3: `stitcher generate` 命令 (MVP 版本)** 的实现。这意味着我们需要在 `stitcher-application` 层创建一个编排器，它会：
1.  调用 `stitcher-scanner` 来解析文件。
2.  将得到的 `ModuleDef` 传递给 `stitcher-io` 的 `StubGenerator`。
3.  （下一步）将生成的字符串写入文件系统。

我们将继续使用 TDD，为 `stitcher-application` 编写一个集成测试。
