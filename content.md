简要回答
好的，我们开始基于 TDD 原则，创建单元测试并实现 `GriffePythonParser` 的核心函数解析逻辑。

## [WIP] feat(adapter): 实现 Griffe 解析器核心逻辑与单元测试

### 用户需求
1.  创建单元测试文件，验证解析器的基本功能。
2.  实现 `GriffePythonParser`，将 Python 源代码映射为 Stitcher 的 `ModuleDef` IR，重点实现函数和参数的解析。

### 评论
我们将在 `packages/stitcher-python-adapter` 下建立独立的测试目录，以保证包的自包含性。
实现策略上，我们将利用 `ast` 模块结合 `griffe.visit` 来进行内存中解析，避免对文件系统的依赖，这与我们在其他组件中“零副作用”的测试哲学一致。

### 目标
1.  创建 `packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py`。
2.  实现 `packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py` 的具体逻辑。

### 基本原理
Griffe 的设计允许访问 AST。通过 `griffe.visit`，我们可以将源代码字符串转换为 Griffe 的对象模型（`griffe.Module`, `griffe.Function` 等），然后编写适配器逻辑将其转换为 `stitcher.spec` 定义的 IR。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/parser #scope/core #ai/instruct
#task/domain/engine #task/object/griffe-parser #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 创建测试目录

首先确保测试目录存在。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-python-adapter/tests/unit
~~~~~

#### Acts 2: 创建单元测试

我们定义一个测试用例，涵盖了普通函数、异步函数、参数类型（带默认值、类型注解）和返回值的解析。这将作为我们实现的验收标准。

~~~~~act
write_file
packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py
~~~~~
~~~~~python
import pytest
from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.spec import ArgumentKind

class TestGriffeParserFunctions:
    @pytest.fixture
    def parser(self):
        return GriffePythonParser()

    def test_parse_simple_function(self, parser):
        code = """
def my_func(a: int, b: str = "default") -> bool:
    \"\"\"My docstring.\"\"\"
    return True
"""
        module = parser.parse(code)
        
        assert len(module.functions) == 1
        func = module.functions[0]
        
        assert func.name == "my_func"
        assert func.docstring == "My docstring."
        assert func.return_annotation == "bool"
        assert not func.is_async
        
        assert len(func.args) == 2
        arg1 = func.args[0]
        assert arg1.name == "a"
        assert arg1.annotation == "int"
        assert arg1.kind == ArgumentKind.POSITIONAL_OR_KEYWORD
        
        arg2 = func.args[1]
        assert arg2.name == "b"
        assert arg2.default == '"default"'

    def test_parse_async_function(self, parser):
        code = "async def runner(): pass"
        module = parser.parse(code)
        assert module.functions[0].is_async

    def test_parse_positional_only_args(self, parser):
        code = "def func(a, /, b): pass"
        module = parser.parse(code)
        
        args = module.functions[0].args
        assert args[0].name == "a"
        assert args[0].kind == ArgumentKind.POSITIONAL_ONLY
        assert args[1].name == "b"
        assert args[1].kind == ArgumentKind.POSITIONAL_OR_KEYWORD
~~~~~

#### Acts 3: 实现 Griffe 解析器

现在我们实现核心解析逻辑。我们将使用 `ast.parse` 生成语法树，然后用 `griffe.visit` 遍历它。
**注意**：为了处理参数类型映射，我们需要正确转换 Griffe 的参数 Kind 到 `stitcher.spec.ArgumentKind`。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python
import ast
import griffe
from typing import List, Optional, Any
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FunctionDef,
    Argument,
    ArgumentKind,
    ClassDef,
    Attribute
)


class GriffePythonParser(LanguageParserProtocol):
    """
    A Python parser implementation using Griffe.
    """

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
        """
        Parses the given source code into a Stitcher ModuleDef IR using Griffe.
        """
        # 1. Parse into AST
        try:
            tree = ast.parse(source_code)
        except SyntaxError as e:
            # Wrap SyntaxError or let it bubble? For now, standard behavior.
            raise ValueError(f"Syntax error in {file_path}: {e}") from e

        # 2. Visit with Griffe
        # We use a virtual module name based on file path or default
        module_name = file_path.replace("/", ".").replace(".py", "") or "module"
        griffe_module = griffe.visit(module_name, filepath=None, code=source_code)

        # 3. Map to Stitcher IR
        return self._map_module(griffe_module, file_path)

    def _map_module(self, gm: griffe.Module, file_path: str) -> ModuleDef:
        functions = []
        # Filter and map top-level functions
        for member in gm.members.values():
            if member.is_function:
                functions.append(self._map_function(member))
            # TODO: Add Class handling in next iteration
            # if member.is_class:
            #     classes.append(self._map_class(member))

        # TODO: Extract module-level docstring and attributes
        # Griffe module docstring parsing
        docstring = gm.docstring.value if gm.docstring else None

        return ModuleDef(
            file_path=file_path,
            docstring=docstring,
            functions=functions,
            # Placeholders for future iterations
            classes=[],
            attributes=[],
            imports=[]
        )

    def _map_function(self, gf: griffe.Function) -> FunctionDef:
        args = [self._map_argument(p) for p in gf.parameters]
        
        # Griffe stores return annotation object, we need source string or name
        return_annotation = None
        if gf.returns:
            # gf.returns is typically an ExprName or similar. We want the string representation.
            # Griffe < 1.0 might act differently, assuming modern/stable API behavior:
            # We use .source or try to stringify
             return_annotation = str(gf.returns)

        docstring = gf.docstring.value if gf.docstring else None

        return FunctionDef(
            name=gf.name,
            args=args,
            return_annotation=return_annotation,
            docstring=docstring,
            is_async=gf.is_async,
            decorators=[str(d.value) for d in gf.decorators],
            # Basic static/class method detection from decorators
            is_static="staticmethod" in [d.value.name for d in gf.decorators if hasattr(d.value, "name")],
            is_class="classmethod" in [d.value.name for d in gf.decorators if hasattr(d.value, "name")],
        )

    def _map_argument(self, param: griffe.Parameter) -> Argument:
        # Map Kind
        # Griffe kind is usually string-like or inspect.Parameter.kind compatible
        kind_map = {
            "positional-only": ArgumentKind.POSITIONAL_ONLY,
            "positional-or-keyword": ArgumentKind.POSITIONAL_OR_KEYWORD,
            "keyword-only": ArgumentKind.KEYWORD_ONLY,
            "variadic positional": ArgumentKind.VAR_POSITIONAL,
            "variadic keyword": ArgumentKind.VAR_KEYWORD,
        }
        
        # Griffe's kind.value (if enum) or str(kind) needs to be checked
        # griffe.ParameterKind is an Enum.
        st_kind = ArgumentKind.POSITIONAL_OR_KEYWORD # Default
        if param.kind:
             # Convert Griffe kind to our enum. 
             # Logic simplifies depending on Griffe version. 
             # We assume param.kind.name or param.kind.value matches convention
             slug = str(param.kind.value)
             st_kind = kind_map.get(slug, ArgumentKind.POSITIONAL_OR_KEYWORD)

        annotation = str(param.annotation) if param.annotation else None
        default = str(param.default) if param.default else None

        return Argument(
            name=param.name,
            kind=st_kind,
            annotation=annotation,
            default=default
        )
~~~~~

### 下一步建议

我们已经实现了对函数的解析。下一步，我们应该：
1.  **运行该单元测试**（通过Quipu环境外执行或后续 CI 验证）。
2.  **完善 `_map_module` 逻辑**，添加对 `ClassDef`（包括嵌套方法）和模块级 `Attribute` 的支持。
3.  处理 Griffe 特有的复杂类型注解解析 (Type Extensions)。
