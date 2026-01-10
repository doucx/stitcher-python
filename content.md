好的，我将开始实施您请求的前两个原子任务。这将分为三个步骤：
1.  修改 `stitcher-spec` 中的 `Attribute` 模型。
2.  修改 `GriffePythonParser` 以解析并映射别名。
3.  创建一个新的单元测试来验证此行为。

这是一个工作进行中的计划，旨在为索引系统引入别名解析的核心能力。

## [WIP] feat(index): Introduce alias resolution in parser

### 用户需求

1.  **Atomic Task 1**: 修改 `stitcher-spec` 中的 `Attribute` 数据模型，为其增加一个 `alias_target` 字段，用于存储别名所指向的原始符号的 FQN。
2.  **Atomic Task 2**: 修改 `stitcher-python-analysis` 包中的 `GriffePythonParser`，使其能够识别 `import` 和 `from ... import` 语句，并将它们作为带有 `alias_target` 信息的 `Attribute` 实例映射到 `ModuleDef` 中。
3.  为 `GriffePythonParser` 的新功能编写单元测试，确保别名被正确解析。

### 评论

这是解决“数据保真度债务”中 **1.3 (缺失的别名解析)** 的关键第一步。通过让“别名”在我们的中间表示（IR）中成为一等公民，我们为后续实现精确的引用分析（债务 1.2）和高保真的代码重构奠定了基础。此变更是解锁索引真正语义能力的核心。

### 目标

1.  在 `stitcher.spec.models.Attribute` dataclass 中成功添加 `alias_target: Optional[str] = None` 字段。
2.  更新 `GriffePythonParser` 的 `_map_module` 方法，移除对 `member.is_alias` 的过滤，并增加处理 `griffe.Alias` 对象的逻辑。
3.  实现一个新的 `_map_alias` 私有方法，将 `griffe.Alias` 对象转换为 `stitcher.spec.Attribute` 对象，正确填充其 `name` 和 `alias_target` 字段。
4.  创建一个新的测试文件，并添加一组单元测试，覆盖对 `import ...`、`import ... as ...`、`from ... import ...` 和 `from ... import ... as ...` 语句的解析，验证生成的 `Attribute` 符合预期。

### 基本原理

1.  **Spec-First**: 我们首先修改 `stitcher-spec`，因为它是系统中所有组件共享的契约。通过先定义数据模型，我们确保了后续的实现（解析器）有一个明确的目标。
2.  **Leverage Griffe**: Griffe 已经完成了对 Python 导入语句的复杂解析，并将其表示为 `griffe.Alias` 对象。我们的任务不是重新发明轮子，而是利用 Griffe 的解析结果，将其正确地映射到我们自己的 IR 中。`Alias` 对象上的 `target_path` 属性已经为我们提供了所需的目标 FQN。
3.  **Test-Driven Development**: 对于这种核心功能的增强，添加一个专门的单元测试是至关重要的。这不仅能验证我们当前实现的正确性，还能在未来保护此逻辑免受回归问题的影响。

### 标签

#intent/build #flow/ready #priority/high #comp/spec #comp/python-analysis #comp/tests #concept/alias-resolution #concept/parser #task/domain/indexing #task/object/alias-resolution #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: (Task 1) 扩展 Attribute 模型

首先，我们将在 `stitcher-spec` 包中为 `Attribute` 模型添加 `alias_target` 字段。

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
    location: Optional[SourceLocation] = None
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
    alias_target: Optional[str] = None  # The FQN of the symbol this alias points to
~~~~~

#### Acts 2: (Task 2) 更新 Griffe 解析器以处理别名

接下来，我们将修改位于 `stitcher-python-analysis` 包中的 `GriffePythonParser`，使其能够处理并映射 Griffe 解析出的别名。

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/griffe/parser.py
~~~~~
~~~~~python.old
    def _map_module(
        self, gm: griffe.Module, file_path: str, imports: List[str]
    ) -> ModuleDef:
        functions = []
        classes = []
        attributes = []

        for member in gm.members.values():
            if member.is_alias:
                continue
            if member.is_function:
                functions.append(self._map_function(cast(griffe.Function, member)))
            elif member.is_class:
                classes.append(self._map_class(cast(griffe.Class, member)))
            elif member.is_attribute:
                attributes.append(self._map_attribute(cast(griffe.Attribute, member)))

        docstring = gm.docstring.value if gm.docstring else None
~~~~~
~~~~~python.new
    def _map_module(
        self, gm: griffe.Module, file_path: str, imports: List[str]
    ) -> ModuleDef:
        functions = []
        classes = []
        attributes = []

        for member in gm.members.values():
            if member.is_function:
                functions.append(self._map_function(cast(griffe.Function, member)))
            elif member.is_class:
                classes.append(self._map_class(cast(griffe.Class, member)))
            elif member.is_attribute:
                attributes.append(self._map_attribute(cast(griffe.Attribute, member)))
            elif member.is_alias:
                attributes.append(self._map_alias(cast(griffe.Alias, member)))

        docstring = gm.docstring.value if gm.docstring else None
~~~~~

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/griffe/parser.py
~~~~~
~~~~~python.old
    def _map_attribute(self, ga: griffe.Attribute) -> Attribute:
        annotation = str(ga.annotation) if ga.annotation else None
        value = str(ga.value) if ga.value else None
        docstring = ga.docstring.value if ga.docstring else None
        return Attribute(
            name=ga.name,
            annotation=annotation,
            value=value,
            docstring=docstring,
            location=self._extract_location(ga),
        )
~~~~~
~~~~~python.new
    def _map_attribute(self, ga: griffe.Attribute) -> Attribute:
        annotation = str(ga.annotation) if ga.annotation else None
        value = str(ga.value) if ga.value else None
        docstring = ga.docstring.value if ga.docstring else None
        return Attribute(
            name=ga.name,
            annotation=annotation,
            value=value,
            docstring=docstring,
            location=self._extract_location(ga),
        )

    def _map_alias(self, ga: griffe.Alias) -> Attribute:
        return Attribute(
            name=ga.name,
            alias_target=ga.target_path,
            location=self._extract_location(ga),
        )
~~~~~

#### Acts 3: (Task 2) 为别名解析添加单元测试

最后，我们创建一个新的测试文件来验证 `GriffePythonParser` 现在能够正确处理各种导入语句。

~~~~~act
write_file
packages/stitcher-python-analysis/tests/unit/griffe/test_parser.py
~~~~~
~~~~~python
import pytest
from stitcher.python.analysis.griffe.parser import GriffePythonParser


@pytest.fixture
def parser():
    return GriffePythonParser()


class TestGriffeParserAliases:
    def test_parse_import_from(self, parser: GriffePythonParser):
        code = "from os.path import join, splitext"
        module = parser.parse(code)

        assert len(module.attributes) == 2

        join_attr = next(a for a in module.attributes if a.name == "join")
        assert join_attr.alias_target == "os.path.join"
        assert join_attr.value is None

        splitext_attr = next(a for a in module.attributes if a.name == "splitext")
        assert splitext_attr.alias_target == "os.path.splitext"

    def test_parse_import_from_with_alias(self, parser: GriffePythonParser):
        code = "from pathlib import Path as P"
        module = parser.parse(code)

        assert len(module.attributes) == 1

        path_attr = module.attributes[0]
        assert path_attr.name == "P"
        assert path_attr.alias_target == "pathlib.Path"

    def test_parse_import_module(self, parser: GriffePythonParser):
        code = "import json"
        module = parser.parse(code)

        assert len(module.attributes) == 1

        json_attr = module.attributes[0]
        assert json_attr.name == "json"
        assert json_attr.alias_target == "json"

    def test_parse_import_module_with_alias(self, parser: GriffePythonParser):
        code = "import sys as system"
        module = parser.parse(code)

        assert len(module.attributes) == 1

        sys_attr = module.attributes[0]
        assert sys_attr.name == "system"
        assert sys_attr.alias_target == "sys"

    def test_attributes_and_aliases_coexist(self, parser: GriffePythonParser):
        code = """
import os
from pathlib import Path

MY_CONSTANT = "hello"
"""
        module = parser.parse(code)

        assert len(module.attributes) == 3

        os_attr = next(a for a in module.attributes if a.name == "os")
        assert os_attr.alias_target == "os"

        path_attr = next(a for a in module.attributes if a.name == "Path")
        assert path_attr.alias_target == "pathlib.Path"

        const_attr = next(a for a in module.attributes if a.name == "MY_CONSTANT")
        assert const_attr.value == "'hello'"
        assert const_attr.alias_target is None
~~~~~

### 下一步建议

我们已经成功地让解析器识别并记录了别名。下一步是利用这些新信息：

-   **实现 Atomic Task 3**: 修改 `PythonAdapter` (`stitcher-python-adapter` 包) 以消费 `Attribute.alias_target` 字段，并将其转换为数据库中的 `SymbolRecord.alias_target_id`。
-   **实现 Atomic Task 4**: 增强 `PythonAdapter._extract_references`，将解析出的别名添加到本地符号表中，以实现对导入符号的精确引用跟踪。

如果您同意，我将为您生成执行下一步的计划。
