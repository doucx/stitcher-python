简要回答：
这是一个 P0 级的修复。为了让 IDE 正确识别 `.pyi` 中的导出符号，我们必须保留源码中的 `__all__` 定义。

我们将采取**“原样保留”**的策略：
1.  **Scanner**: 在解析 AST 时，专门侦测对 `__all__` 的赋值（包括普通赋值 `__all__ = ...` 和带类型注解的赋值 `__all__: list = ...`）。我们将赋值符号右侧的表达式作为**原始字符串**捕获。
2.  **Spec**: 在 IR (`ModuleDef`) 中新增 `dunder_all` 字段来存储这个字符串。
3.  **Generator**: 在生成 `.pyi` 时，如果存在 `dunder_all`，则在 Imports 之后显式写入 `__all__ = <value>`。

这种方法最稳健，因为它不仅支持列表字面量 `["A"]`，也支持元组 `("A",)` 甚至加法运算 `["A"] + ["B"]`（只要这些写法在静态分析下是合法的）。

## [WIP] fix: 支持 __all__ 的解析与生成以修复符号导出

### 用户需求
用户生成的 `.pyi` 文件导致 IDE 报错 `unknown import symbol`，因为默认导入在 `.pyi` 中是私有的。用户要求 `stitcher` 支持 `__all__` 或 `import as` 语法，以使导出公开。

### 评论
这是 Python 存根文件的核心机制。没有 `__all__`，生成的存根对库的使用者来说几乎是废品。

### 目标
1.  修改 `ModuleDef`，增加 `dunder_all` 字段。
2.  修改 `parser.py`，拦截 `__all__` 的赋值并提取其右值代码。
3.  修改 `stub_generator.py`，输出 `__all__` 语句。
4.  添加单元测试验证解析和生成逻辑。

### 基本原理
-   **AST 解析**: 使用 LibCST 访问 `Assign` 和 `AnnAssign` 节点。如果目标变量名是 `__all__`，则提取其 `value` 节点的代码表示，并不将其视为普通属性（Attribute）。
-   **代码生成**: 在 `.pyi` 头部（Imports 后，Attributes 前）插入 `__all__ = ...`。

### 标签
#intent/fix #flow/ready #priority/high #comp/scanner #comp/io #scope/core
#task/domain/parser #task/object/dunder-all #task/action/implement
#task/state/continue

---

### Script

#### Acts 1: 更新 Spec 模型

在 `ModuleDef` 中添加 `dunder_all` 字段。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/models.py
~~~~~
~~~~~old
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
~~~~~new
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
    # The raw string representation of the __all__ assignment value (e.g. '["a", "b"]')
    dunder_all: Optional[str] = None
~~~~~

#### Acts 2: 更新 Scanner 解析逻辑

修改 `IRBuildingVisitor` 以拦截 `__all__`。

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~old
    def __init__(self):
        # Module level containers
        self.functions: List[FunctionDef] = []
        self.classes: List[ClassDef] = []
        self.attributes: List[Attribute] = []
        self.imports: List[str] = []

        # Scope management: A stack of currently active ClassDefs being built.
        # If stack is empty, we are at module level.
        self._class_stack: List[ClassDef] = []
        self._dummy_module = cst.Module([])  # Helper for code generation
~~~~~
~~~~~new
    def __init__(self):
        # Module level containers
        self.functions: List[FunctionDef] = []
        self.classes: List[ClassDef] = []
        self.attributes: List[Attribute] = []
        self.imports: List[str] = []
        self.dunder_all: Optional[str] = None

        # Scope management: A stack of currently active ClassDefs being built.
        # If stack is empty, we are at module level.
        self._class_stack: List[ClassDef] = []
        self._dummy_module = cst.Module([])  # Helper for code generation
~~~~~

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~old
    def visit_AnnAssign(self, node: cst.AnnAssign) -> Optional[bool]:
        # Handle: x: int = 1
        if not isinstance(node.target, cst.Name):
            return False

        name = node.target.value
        annotation = self._dummy_module.code_for_node(
            node.annotation.annotation
        ).strip()

        value = None
        if node.value:
            value = self._dummy_module.code_for_node(node.value).strip()

        self._add_attribute(Attribute(name=name, annotation=annotation, value=value))
        return False

    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        # Handle: x = 1
        # Only handle simple assignment to a single name for now
        if len(node.targets) != 1:
            return False

        target = node.targets[0].target
        if not isinstance(target, cst.Name):
            return False

        name = target.value
        value = self._dummy_module.code_for_node(node.value).strip()

        self._add_attribute(Attribute(name=name, annotation=None, value=value))
        return False
~~~~~
~~~~~new
    def visit_AnnAssign(self, node: cst.AnnAssign) -> Optional[bool]:
        # Handle: x: int = 1
        if not isinstance(node.target, cst.Name):
            return False

        name = node.target.value
        value = None
        if node.value:
            value = self._dummy_module.code_for_node(node.value).strip()

        # Special handling for __all__
        if name == "__all__" and not self._class_stack:
            if value:
                self.dunder_all = value
            return False

        annotation = self._dummy_module.code_for_node(
            node.annotation.annotation
        ).strip()

        self._add_attribute(Attribute(name=name, annotation=annotation, value=value))
        return False

    def visit_Assign(self, node: cst.Assign) -> Optional[bool]:
        # Handle: x = 1
        # Only handle simple assignment to a single name for now
        if len(node.targets) != 1:
            return False

        target = node.targets[0].target
        if not isinstance(target, cst.Name):
            return False

        name = target.value
        value = self._dummy_module.code_for_node(node.value).strip()

        # Special handling for __all__
        if name == "__all__" and not self._class_stack:
            self.dunder_all = value
            return False

        self._add_attribute(Attribute(name=name, annotation=None, value=value))
        return False
~~~~~

~~~~~act
patch_file
packages/stitcher-scanner/src/stitcher/scanner/parser.py
~~~~~
~~~~~old
    module_def = ModuleDef(
        file_path=file_path,
        docstring=cst_module.get_docstring()
        if isinstance(cst_module.get_docstring(), str)
        else None,
        functions=visitor.functions,
        classes=visitor.classes,
        attributes=visitor.attributes,
        imports=visitor.imports,
    )
~~~~~
~~~~~new
    module_def = ModuleDef(
        file_path=file_path,
        docstring=cst_module.get_docstring()
        if isinstance(cst_module.get_docstring(), str)
        else None,
        functions=visitor.functions,
        classes=visitor.classes,
        attributes=visitor.attributes,
        imports=visitor.imports,
        dunder_all=visitor.dunder_all,
    )
~~~~~

#### Acts 3: 更新 Generator 生成逻辑

在生成的 `.pyi` 中包含 `__all__`。

~~~~~act
patch_file
packages/stitcher-io/src/stitcher/io/stub_generator.py
~~~~~
~~~~~old
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
~~~~~
~~~~~new
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
~~~~~

#### Acts 4: 添加测试用例

我们添加两个测试：一个测 Scanner 能抓到，一个测 Generator 能输出。

~~~~~act
write_file
packages/stitcher-scanner/tests/test_parser_dunder_all.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.scanner import parse_source_code


def test_parse_dunder_all_simple():
    source = dedent("""
    __all__ = ["func1", "func2"]
    
    def func1(): pass
    """)
    module = parse_source_code(source)
    
    assert module.dunder_all == '["func1", "func2"]'
    # Should NOT be in attributes
    assert not any(attr.name == "__all__" for attr in module.attributes)


def test_parse_dunder_all_annotated():
    source = dedent("""
    from typing import List
    __all__: List[str] = ["A"]
    """)
    module = parse_source_code(source)
    
    assert module.dunder_all == '["A"]'
    assert not any(attr.name == "__all__" for attr in module.attributes)


def test_parse_dunder_all_complex():
    source = dedent("""
    __all__ = ["A"] + ["B"]
    """)
    module = parse_source_code(source)
    
    # We capture the raw expression code
    assert module.dunder_all == '["A"] + ["B"]'
~~~~~

~~~~~act
write_file
packages/stitcher-io/tests/test_generator_dunder_all.py
~~~~~
~~~~~python
from textwrap import dedent
from stitcher.spec import ModuleDef
from stitcher.io import StubGenerator


def test_generate_with_dunder_all():
    module = ModuleDef(
        file_path="foo.py",
        imports=["import os"],
        dunder_all='["func"]',
    )
    
    gen = StubGenerator()
    output = gen.generate(module)
    
    expected = dedent("""
    import os
    
    __all__ = ["func"]
    """)
    
    assert expected.strip() in output.strip()
~~~~~

### 下一步建议
1.  **运行测试**: 确保新添加的测试通过 `pytest packages/stitcher-scanner/tests/ packages/stitcher-io/tests/`。
2.  **Dogfooding 重试**: 再次运行 `stitcher generate`。
3.  **验证**: 检查生成的 `packages/stitcher-common/src/stitcher/common/__init__.pyi`，它现在应该包含 `__all__ = ["bus"]`。
4.  **IDE 验证**: 查看 `core.py` 里的红线是否消失。此时，`stitcher` 应该真正可以用了。
