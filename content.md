简要回答
好的，进入下一阶段：补全 `GriffePythonParser` 的 Import 提取能力。这将解决生成的 `.pyi` 文件因缺少导入语句而无法使用的问题。

## [WIP] feat(adapter): 为 Griffe 解析器实现基于 AST 的 Import 语句提取

### 用户需求
1.  扩展 `GriffePythonParser`，使其能够提取源码中的 `import` 和 `from ... import` 语句。
2.  确保生成的 `ModuleDef.imports` 列表被正确填充。

### 评论
虽然 Griffe 提供了高级的语义模型，但为了高效且格式规范地提取 Import 语句（用于 `.pyi` 生成），直接利用 Python 内置的 `ast` 模块进行遍历是最稳健且低成本的方案。我们已经在代码中为了语法检查而生成了 AST 树，现在只是充分利用它。

### 目标
1.  修改 `packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py`，增加针对 Import 提取的测试用例。
2.  修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py`，实现 `ImportVisitor` 并集成到 `parse` 流程中。

### 基本原理
我们利用 `ast.NodeVisitor` 遍历语法树的顶层节点，识别 `Import` 和 `ImportFrom` 节点，并使用 `ast.unparse` (Python 3.9+) 将其还原为标准化的字符串代码。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/parser #scope/core #ai/instruct
#task/domain/engine #task/object/griffe-parser #task/action/expand #task/state/continue

---

### Script

#### Acts 1: 添加 Import 提取测试

在单元测试中增加一个专门测试 Import 提取的方法。

~~~~~act
patch_file
packages/stitcher-python-adapter/tests/unit/test_griffe_parser.py
~~~~~
~~~~~python.old
        method = cls.methods[0]
        assert method.name == "method"
        assert len(method.args) == 1
        assert method.args[0].name == "self"
~~~~~
~~~~~python.new
        method = cls.methods[0]
        assert method.name == "method"
        assert len(method.args) == 1
        assert method.args[0].name == "self"

    def test_parse_imports(self, parser):
        code = """
import os
from typing import List, Optional
import sys as system
"""
        module = parser.parse(code)
        
        # ast.unparse normalizes output
        expected_imports = [
            "import os",
            "from typing import List, Optional",
            "import sys as system"
        ]
        
        # Check that we caught all of them. Order should be preserved.
        assert len(module.imports) == 3
        for expected in expected_imports:
            assert expected in module.imports
~~~~~

#### Acts 2: 实现 ImportVisitor 并集成

我们定义一个内部类 `_ImportVisitor`，并在 `parse` 方法中使用它。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python.old
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
~~~~~
~~~~~python.new
class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.append(ast.unparse(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(ast.unparse(node))


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
        
        # 1.5 Extract Imports via AST
        import_visitor = _ImportVisitor()
        import_visitor.visit(tree)
        imports = import_visitor.imports

        # 2. Visit with Griffe
        module_name = file_path.replace("/", ".").replace(".py", "") or "module"
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/griffe_parser.py
~~~~~
~~~~~python.old
        # 3. Map to Stitcher IR
        return self._map_module(griffe_module, file_path)

    def _map_module(self, gm: griffe.Module, file_path: str) -> ModuleDef:
        functions = []
        classes = []
        attributes = []

        for member in gm.members.values():
            # Skip aliases (imported names) to prevent resolution errors
            # We only want to map symbols DEFINED in this module.
            if member.is_alias:
                continue

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
~~~~~
~~~~~python.new
        # 3. Map to Stitcher IR
        return self._map_module(griffe_module, file_path, imports)

    def _map_module(self, gm: griffe.Module, file_path: str, imports: List[str]) -> ModuleDef:
        functions = []
        classes = []
        attributes = []

        for member in gm.members.values():
            # Skip aliases (imported names) to prevent resolution errors
            # We only want to map symbols DEFINED in this module.
            if member.is_alias:
                continue

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
            imports=imports
        )
~~~~~

### 下一步建议

运行单元测试。如果通过，我们可以进行一次手动验证：
1.  创建一个通过测试项目。
2.  运行 `stitcher generate`。
3.  检查生成的 `.pyi` 文件是否包含了正确的 import 语句。

（**注**：`_enrich_typing_imports` 的逻辑——即自动补充缺失的 `List`, `Optional` 等导入——仍然是缺失的。对于严格的类型检查通过，这是必需的。我们可以在确认基础 Import 提取工作正常后，决定是否立即移植该逻辑。）
