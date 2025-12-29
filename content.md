简要回答
好的，我们继续扩展 `GriffePythonParser` 的能力，使其支持 Python 类（Class）和属性（Attribute）的解析。

## [WIP] feat(adapter): 扩展 Griffe 解析器以支持类和属性

### 用户需求
1.  扩展 `GriffePythonParser`，使其能够解析 `class` 定义，包括基类、方法和类属性。
2.  扩展 `GriffePythonParser`，使其能够解析模块级别的变量（Attributes）。
3.  补充相应的单元测试。

### 评论
这是完成解析器核心功能的关键一步。Griffe 将类和模块都统一抽象为容器，拥有 `members` 字典，这使得递归处理（如类中的方法）变得相对直观。我们需要特别注意属性（Attribute）的处理，因为它们不仅包含值，还可能包含注解和文档字符串。

### 目标
1.  更新 `packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py`，增加类和属性的测试用例。
2.  修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py`，实现 `_map_class` 和 `_map_attribute` 方法，并完善 `_map_module`。

### 基本原理
我们将利用 Griffe 的 `Class` 和 `Attribute` 对象模型。
- **类 (Class)**: 映射为 `stitcher.spec.ClassDef`。需要遍历其 `members` 来分离方法和属性。
- **属性 (Attribute)**: 映射为 `stitcher.spec.Attribute`。需要提取其注解（`annotation`）和赋值（`value`）。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/parser #scope/core #ai/instruct
#task/domain/engine #task/object/griffe-parser #task/action/expand #task/state/continue

---

### Script

#### Acts 1: 扩展单元测试

我们在测试文件中添加一个新的测试类 `TestGriffeParserStructure`，专门涵盖类、继承、模块属性和嵌套成员的解析。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py
~~~~~
~~~~~python.old
        assert args[1].name == "b"
        assert args[1].kind == ArgumentKind.POSITIONAL_OR_KEYWORD
~~~~~
~~~~~python.new
        assert args[1].name == "b"
        assert args[1].kind == ArgumentKind.POSITIONAL_OR_KEYWORD

class TestGriffeParserStructure:
    @pytest.fixture
    def parser(self):
        return GriffePythonParser()

    def test_parse_module_attributes(self, parser):
        code = """
CONST_VAL: int = 42
\"\"\"Constant docstring.\"\"\"
simple_var = "hello"
"""
        module = parser.parse(code)
        
        assert len(module.attributes) == 2
        
        attr1 = next(a for a in module.attributes if a.name == "CONST_VAL")
        assert attr1.annotation == "int"
        assert attr1.value == "42"
        assert attr1.docstring == "Constant docstring."

        attr2 = next(a for a in module.attributes if a.name == "simple_var")
        assert attr2.value == "'hello'"  # Normalized quotes

    def test_parse_class_def(self, parser):
        code = """
class MyClass(Base1, Base2):
    \"\"\"Class doc.\"\"\"
    field: str = "init"
    
    def method(self):
        pass
"""
        module = parser.parse(code)
        assert len(module.classes) == 1
        cls = module.classes[0]
        
        assert cls.name == "MyClass"
        assert cls.docstring == "Class doc."
        assert cls.bases == ["Base1", "Base2"]
        
        # Check Attribute
        assert len(cls.attributes) == 1
        attr = cls.attributes[0]
        assert attr.name == "field"
        assert attr.annotation == "str"
        assert attr.value == "'init'"
        
        # Check Method
        assert len(cls.methods) == 1
        method = cls.methods[0]
        assert method.name == "method"
        assert len(method.args) == 1
        assert method.args[0].name == "self"
~~~~~

#### Acts 2: 实现类与属性解析逻辑

我们在 `GriffePythonParser` 中增加 `_map_class` 和 `_map_attribute` 方法，并在 `_map_module` 中集成它们。此变更较大，我们重写整个文件以保持清晰。

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
            raise ValueError(f"Syntax error in {file_path}: {e}") from e

        # 2. Visit with Griffe
        module_name = file_path.replace("/", ".").replace(".py", "") or "module"
        griffe_module = griffe.visit(module_name, filepath=None, code=source_code)

        # 3. Map to Stitcher IR
        return self._map_module(griffe_module, file_path)

    def _map_module(self, gm: griffe.Module, file_path: str) -> ModuleDef:
        functions = []
        classes = []
        attributes = []

        for member in gm.members.values():
            if member.is_function:
                functions.append(self._map_function(member))
            elif member.is_class:
                classes.append(self._map_class(member))
            elif member.is_attribute:
                attributes.append(self._map_attribute(member))

        docstring = gm.docstring.value if gm.docstring else None

        return ModuleDef(
            file_path=file_path,
            docstring=docstring,
            functions=functions,
            classes=classes,
            attributes=attributes,
            imports=[] # Imports handling to be added later
        )

    def _map_class(self, gc: griffe.Class) -> ClassDef:
        methods = []
        attributes = []

        for member in gc.members.values():
            if member.is_function:
                methods.append(self._map_function(member))
            elif member.is_attribute:
                attributes.append(self._map_attribute(member))

        docstring = gc.docstring.value if gc.docstring else None
        
        # Bases are expressions, we stringify them
        bases = [str(b) for b in gc.bases]

        return ClassDef(
            name=gc.name,
            bases=bases,
            decorators=[str(d.value) for d in gc.decorators],
            docstring=docstring,
            attributes=attributes,
            methods=methods
        )

    def _map_attribute(self, ga: griffe.Attribute) -> Attribute:
        annotation = str(ga.annotation) if ga.annotation else None
        value = str(ga.value) if ga.value else None
        docstring = ga.docstring.value if ga.docstring else None

        return Attribute(
            name=ga.name,
            annotation=annotation,
            value=value,
            docstring=docstring
        )

    def _map_function(self, gf: griffe.Function) -> FunctionDef:
        args = [self._map_argument(p) for p in gf.parameters]
        
        return_annotation = None
        if gf.returns:
             return_annotation = str(gf.returns)

        docstring = gf.docstring.value if gf.docstring else None

        return FunctionDef(
            name=gf.name,
            args=args,
            return_annotation=return_annotation,
            docstring=docstring,
            is_async="async" in gf.labels,
            decorators=[str(d.value) for d in gf.decorators],
            is_static="staticmethod" in gf.labels,
            is_class="classmethod" in gf.labels,
        )

    def _map_argument(self, param: griffe.Parameter) -> Argument:
        kind_map = {
            "positional-only": ArgumentKind.POSITIONAL_ONLY,
            "positional-or-keyword": ArgumentKind.POSITIONAL_OR_KEYWORD,
            "keyword-only": ArgumentKind.KEYWORD_ONLY,
            "variadic positional": ArgumentKind.VAR_POSITIONAL,
            "variadic keyword": ArgumentKind.VAR_KEYWORD,
        }
        
        st_kind = ArgumentKind.POSITIONAL_OR_KEYWORD
        if param.kind:
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

现在我们已经基本完成了 `GriffePythonParser` 的核心数据结构映射（Function, Class, Attribute, Module）。下一步，我们可以考虑运行测试，并在通过后**集成 `stitcher-cli`**，将这个新的解析器作为可通过配置切换的选项，完成技术提案中的第三步。
