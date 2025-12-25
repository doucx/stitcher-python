简要回答：
测试如预期失败（返回空字符串）。现在进入 **GREEN** 阶段，我们将实现 `StubGenerator` 的核心逻辑。

我们需要注意以下几点实现细节：
1.  **缩进管理**: Python 对缩进敏感，即使是 `.pyi` 文件。我们需要一个 `_indent(level)` 辅助函数。
2.  **Arguments 格式化**: 需要根据 `ArgumentKind` 处理参数分隔符（如 `/` 和 `*`），这在 Python 3.8+ 中很重要。
3.  **Docstring 处理**: 如果有 docstring，需要用 `"""` 包裹，并注意换行。如果没有 docstring，通常可以用 `...` 作为函数体。
4.  **Attributes**: 类属性通常不带默认值（或只有类型），但在 `.pyi` 中，如果有值，也可以写成 `VAR: int = ...` 或直接 `VAR: int`。我们的测试预期是 `VERSION: str`（只有类型），这在 Stub 文件中是标准做法。

## [WIP] feat(io): 实现 StubGenerator 核心逻辑 (Green Phase)

### 用户需求
在 `stitcher-io` 包中实现 `StubGenerator` 类，使其能够将 `ModuleDef` IR 对象转换为符合 Python 语法规范的 `.pyi` 存根代码，从而通过单元测试。

### 评论
**实现策略**：
我们将采用自底向上的方法：
1.  先实现 `_generate_args`：处理参数列表。
2.  再实现 `_generate_function`：处理函数头、装饰器、返回值和 docstring。
3.  接着实现 `_generate_class`：处理类头、基类和内部方法/属性。
4.  最后在 `generate` 中组合它们。

这种拆分使得代码结构清晰，且容易单独测试（如果在未来需要的话）。

### 目标
1.  完善 `packages/stitcher-io/src/stitcher/io/stub_generator.py`。
2.  实现完整的 IR -> 文本转换逻辑。
3.  确保通过 `test_generate_simple_pyi` 测试。

### 基本原理
`.pyi` 文件的本质是去除实现的 Python 代码。我们通过字符串模板和列表拼接来生成它。

### 标签
#intent/build #flow/ready #priority/high
#comp/io #concept/generator #scope/core #ai/instruct
#task/domain/implementation #task/object/stub-generator #task/action/implement
#task/state/continue #task/status/active

---

### Script

#### Acts 1: 实现 StubGenerator
~~~~~act
write_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~python
from typing import List, Optional
from stitcher.spec import (
    Argument,
    ArgumentKind,
    Attribute,
    ClassDef,
    FunctionDef,
    ModuleDef,
)


class StubGenerator:
    def __init__(self, indent_spaces: int = 4):
        self._indent_str = " " * indent_spaces

    def generate(self, module: ModuleDef) -> str:
        """
        Generates the content of a .pyi file from a ModuleDef IR.
        """
        lines = []

        # 1. Module Docstring
        if module.docstring:
            lines.append(self._format_docstring(module.docstring, 0))
            lines.append("")  # Empty line after docstring

        # 2. Imports (TODO: Pass these through from scanner later)
        if module.imports:
            for imp in module.imports:
                lines.append(imp)
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

    def _format_docstring(self, doc: str, level: int) -> str:
        indent = self._indent(level)
        # Simplified handling: always use triple quotes
        # In a robust implementation, we might handle escaping quotes inside docstring
        if "\n" in doc:
             # multiline
             return f'{indent}"""\n{indent}{doc}\n{indent}"""'
        return f'{indent}"""{doc}"""'

    def _generate_attribute(self, attr: Attribute, level: int) -> str:
        indent = self._indent(level)
        # In .pyi files, we prefer Type Hints:  name: type
        # If value is present (constant), we might output: name: type = value
        # But PEP 484 recommends name: type = ... for constants or just name: type
        # Let's stick to name: type for now as per test expectation.
        
        annotation = attr.annotation if attr.annotation else "Any"
        line = f"{indent}{attr.name}: {annotation}"
        
        # If we wanted to include value:
        # if attr.value:
        #     line += f" = {attr.value}"
            
        return line

    def _generate_args(self, args: List[Argument]) -> str:
        # This is tricky because of POSITIONAL_ONLY (/) and KEYWORD_ONLY (*) markers.
        # We need to detect transitions between kinds.
        
        # Simplified approach for MVP:
        # Just join them. Correctly handling / and * requires looking ahead/behind or state machine.
        # Let's do a slightly better job:
        
        parts = []
        state = ArgumentKind.POSITIONAL_OR_KEYWORD # Default start state logic (simplified)
        
        # Check if we have pos-only args
        has_pos_only = any(a.kind == ArgumentKind.POSITIONAL_ONLY for a in args)
        pos_only_emitted = False
        
        has_kw_only = any(a.kind == ArgumentKind.KEYWORD_ONLY for a in args)
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
                prev_was_var_pos = (i > 0 and args[i-1].kind == ArgumentKind.VAR_POSITIONAL)
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
        lines.append(def_line)

        # Body
        body_indent = self._indent(level + 1)
        if func.docstring:
            lines.append(self._format_docstring(func.docstring, level + 1))
            lines.append(f"{body_indent}...")
        else:
            lines.append(f"{body_indent}...")
            
        return "\n".join(lines)

    def _generate_class(self, cls: ClassDef, level: int) -> str:
        indent = self._indent(level)
        lines = []

        # Class Def
        bases_str = ""
        if cls.bases:
            bases_str = f"({', '.join(cls.bases)})"
        
        lines.append(f"{indent}class {cls.name}{bases_str}:")
        
        # Body
        has_content = False
        
        # Docstring
        if cls.docstring:
            lines.append(self._format_docstring(cls.docstring, level + 1))
            has_content = True

        # Attributes
        for attr in cls.attributes:
            lines.append(self._generate_attribute(attr, level + 1))
            has_content = True
        
        if has_content and cls.methods:
             lines.append("") # Spacer between attrs and methods

        # Methods
        for i, method in enumerate(cls.methods):
            lines.append(self._generate_function(method, level + 1))
            if i < len(cls.methods) - 1:
                lines.append("") # Spacer between methods
            has_content = True

        if not has_content:
            lines.append(f"{self._indent(level + 1)}...")

        return "\n".join(lines)
~~~~~

### 下一步建议
运行 `pytest`。如果通过，我们将完成 `Spec` -> `Scanner` -> `IO` 的核心链路构建。

接下来的关键步骤是将这些组件**缝合**在一起，即 **Application Layer** 的实现。我们将编写一个集成测试，模拟从“读取真实文件”到“生成 .pyi 字符串”的完整过程。
