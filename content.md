我将解决 `1.2. 债务：残缺的引用分析` 这项技术债务。

根据债务分析，当前的 `PythonAdapter` 没有实现引用（即符号使用）的提取逻辑，这使得索引只是一个“符号定义表”，而不是一个“语义关系图”，无法支持“查找所有引用”等核心功能。

我的计划是实现完整的引用分析，具体步骤如下：

1.  **增强解析器**: 我将修改 `GriffePythonParser`，使其在解析时缓存底层的 `griffe.Module` 对象。这个富对象包含了 Griffe 解析和名称解析后的所有详细信息，是构建引用关系的关键。
2.  **实现引用提取**: 我将重写 `PythonAdapter._extract_references` 方法。它将利用 Griffe 解析出的模块信息来构建一个本地符号到其全局唯一标识符（SURI）的映射。
3.  **集成 CST 分析**: 使用上一步构建的符号映射，我将调用 `stitcher-python-analysis` 中已有的、基于 LibCST 的 `UsageScanVisitor` 来遍历源代码的语法树，精确地找出所有符号的用法。
4.  **数据转换与过滤**: `UsageScanVisitor` 返回的用法位置将被转换为索引所需的 `ReferenceRecord` 格式。在此过程中，我会过滤掉符号的“定义”位置，确保索引中只包含纯粹的“引用”。
5.  **编写集成测试**: 我将创建一个新的集成测试，模拟一个包含本地导入、包内别名和跨文件引用的典型项目结构。该测试将验证 `PythonAdapter` 是否能正确地提取引用，并确保引用指向的是正确的符号（特别是 `__init__.py` 中的别名），从而验证封装边界的正确性。

通过这些步骤，`stitcher-index` 将获得完整的语义关系信息，为未来的高级功能（如全局重构、架构检查）奠定坚实的基础。

## [WIP] feat: 实现 PythonAdapter 的引用分析

### 用户需求

解决 `1.2. 债务：残缺的引用分析 (Incomplete Reference Analysis)` 中描述的技术债务，为 `stitcher-index` 提供完整的符号引用（代码使用）信息。

### 评论

这是为 `stitcher-index` 填充“血肉”的关键一步。没有引用关系，索引的价值将大打折扣。完成此任务将解锁“查找所有引用”、“移动/重命名”重构以及架构校验等核心功能，是实现 Stitcher 2.0 愿景的基础。

### 目标

1.  修改 `GriffePythonParser` 以暴露 Griffe 的完整解析结果。
2.  在 `PythonAdapter` 中实现 `_extract_references` 方法，集成 Griffe 的名称解析和 LibCST 的 `UsageScanVisitor`。
3.  确保 `PythonAdapter.parse` 方法能够同时返回精确的符号定义和符号引用列表。
4.  添加集成测试来验证引用提取的正确性，特别是对别名的处理。

### 基本原理

我们将采用一种混合解析策略来平衡性能和准确性：

1.  **Griffe 用于名称解析**: 首先，使用 Griffe 对代码进行一次完整的解析。Griffe 非常擅长处理 Python 复杂的导入和别名规则，能够为我们提供一个从“本地名称”到“权威符号 SURI”的准确映射 (`local_symbols`)。
2.  **LibCST 用于语法遍历**: 接着，利用 `local_symbols` 映射，我们驱动一个 LibCST 的 `UsageScanVisitor` 来遍历源代码。CST 提供了对代码结构的精确控制和元数据（如位置信息），使其成为识别所有“用法”的理想工具。
3.  **过滤与转换**: `UsageScanVisitor` 会找到所有对符号的引用，我们将其结果进行后处理，过滤掉定义本身，并将有效的“用法”转换为索引数据库所需的 `ReferenceRecord` 格式。

这种方法复用了现有、经过测试的 `UsageScanVisitor`，同时利用了 Griffe 在语义理解上的优势，是实现目标的最高效路径。

### 标签

#intent/build #flow/ready #priority/high #comp/index #comp/python-adapter #concept/state #scope/core #ai/brainstorm #task/domain/indexing #task/object/reference-analysis #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 增强 Griffe 解析器以缓存结果

我将修改 `GriffePythonParser`，使其在 `parse` 方法执行后，将底层的 `griffe.Module` 对象存储在一个实例变量中，以便 `PythonAdapter` 后续访问。

~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/griffe/parser.py
~~~~~
~~~~~python.old
import ast
from pathlib import Path
from typing import List, cast, Any

import griffe
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FunctionDef,
    ClassDef,
    Attribute,
    Argument,
    ArgumentKind,
)
from stitcher.python.analysis.cst.visitors import _enrich_typing_imports


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.append(ast.unparse(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(ast.unparse(node))


class GriffePythonParser(LanguageParserProtocol):
    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
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
        # Explicit cast to Any to bypass Pyright check if filepath is strict Path
        path_obj = Path(file_path) if file_path else None
        griffe_module = griffe.visit(
            module_name, filepath=cast(Any, path_obj), code=source_code
        )

        # 3. Map to Stitcher IR
        module_def = self._map_module(griffe_module, file_path, imports)

        # 4. Enrich imports
        _enrich_typing_imports(module_def)

        return module_def
~~~~~
~~~~~python.new
import ast
from pathlib import Path
from typing import List, cast, Any, Optional

import griffe
from stitcher.spec import (
    ModuleDef,
    LanguageParserProtocol,
    FunctionDef,
    ClassDef,
    Attribute,
    Argument,
    ArgumentKind,
)
from stitcher.python.analysis.cst.visitors import _enrich_typing_imports


class _ImportVisitor(ast.NodeVisitor):
    def __init__(self):
        self.imports: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        self.imports.append(ast.unparse(node))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        self.imports.append(ast.unparse(node))


class GriffePythonParser(LanguageParserProtocol):
    def __init__(self):
        self.last_griffe_module: Optional[griffe.Module] = None

    def parse(self, source_code: str, file_path: str = "") -> ModuleDef:
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
        # Explicit cast to Any to bypass Pyright check if filepath is strict Path
        path_obj = Path(file_path) if file_path else None
        griffe_module = griffe.visit(
            module_name, filepath=cast(Any, path_obj), code=source_code
        )
        self.last_griffe_module = griffe_module

        # 3. Map to Stitcher IR
        module_def = self._map_module(griffe_module, file_path, imports)

        # 4. Enrich imports
        _enrich_typing_imports(module_def)

        return module_def
~~~~~

#### Acts 2: 实现引用提取逻辑

现在，我将重写 `PythonAdapter` 以集成新的解析和引用提取流程。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Set

import cst
import griffe
from stitcher.spec import ModuleDef
from stitcher.index.protocols import LanguageAdapter
from stitcher.index.types import SymbolRecord, ReferenceRecord
from stitcher.python.analysis.cst.usage_visitor import (
    UsageRegistry,
    UsageScanVisitor,
)

from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
from .uri import SURIGenerator


class PythonAdapter(LanguageAdapter):
    def __init__(self, root_path: Path):
        self.root_path = root_path
        self.parser = GriffePythonParser()
        self.hasher = PythonFingerprintStrategy()

    def parse(
        self, file_path: Path, content: str
    ) -> Tuple[List[SymbolRecord], List[ReferenceRecord]]:
        # 1. Calculate relative path for SURI
        try:
            rel_path = file_path.relative_to(self.root_path).as_posix()
        except ValueError:
            # Fallback if file is not in root (should not happen in normal scan)
            rel_path = file_path.name

        # 2. Parse into ModuleDef (which also populates parser.last_griffe_module)
        module_def = self.parser.parse(content, file_path=rel_path)
        griffe_module = self.parser.last_griffe_module

        # 3. Project to Symbols
        symbols = self._extract_symbols(rel_path, module_def)

        # 4. Project to References
        references: List[ReferenceRecord] = []
        if griffe_module:
            references = self._extract_references(
                rel_path, content, griffe_module, file_path
            )

        return symbols, references

    def _extract_symbols(self, rel_path: str, module: ModuleDef) -> List[SymbolRecord]:
        symbols: List[SymbolRecord] = []

        # Helper to add symbol
        def add(
            name: str,
            kind: str,
            entity_for_hash: Optional[object] = None,
            parent_fragment: str = "",
        ):
            fragment = f"{parent_fragment}.{name}" if parent_fragment else name
            suri = SURIGenerator.for_symbol(rel_path, fragment)

            # Compute Hash
            sig_hash = None
            if entity_for_hash:
                # We reuse the strategy, but we need to adapt it because strategy returns a Fingerprint object
                # with multiple keys. We probably want 'current_code_structure_hash'.
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

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

        # 1. Functions
        for func in module.functions:
            add(func.name, "function", func)

        # 2. Classes
        for cls in module.classes:
            cls_frag = add(cls.name, "class", cls)

            # Methods
            for method in cls.methods:
                add(method.name, "method", method, parent_fragment=cls_frag)

            # Attributes
            for attr in cls.attributes:
                add(attr.name, "variable", None, parent_fragment=cls_frag)

        # 3. Module-level Attributes
        for attr in module.attributes:
            add(attr.name, "variable", None)

        return symbols

    def _build_local_symbols_map(
        self, griffe_module: griffe.Module
    ) -> Dict[str, str]:
        """Builds a map from local name to target SURI."""
        symbols: Dict[str, str] = {}

        def get_suri(obj: griffe.Object) -> Optional[str]:
            if not obj.filepath:
                return None
            try:
                rel_path = obj.filepath.relative_to(self.root_path).as_posix()
            except ValueError:
                return None

            module_path = obj.module.canonical_path
            canonical_path = obj.canonical_path
            fragment = None
            if canonical_path.startswith(module_path):
                fragment = canonical_path[len(module_path) :].lstrip(".")

            if fragment:
                return SURIGenerator.for_symbol(rel_path, fragment)
            return SURIGenerator.for_file(rel_path)

        for member in griffe_module.members.values():
            target = member.target if member.is_alias else member
            if not target:
                continue

            suri = get_suri(target)
            if suri:
                symbols[member.name] = suri
        return symbols

    def _get_definition_sites(
        self, griffe_module: griffe.Module
    ) -> Set[Tuple[int, int]]:
        """Collects all (lineno, column) tuples for symbol definitions."""
        sites: Set[Tuple[int, int]] = set()

        def collect(obj: griffe.Object):
            sites.add((obj.lineno, obj.column))
            for member in obj.members.values():
                if not member.is_alias:
                    collect(member)

        collect(griffe_module)
        return sites

    def _extract_references(
        self,
        rel_path: str,
        content: str,
        griffe_module: griffe.Module,
        abs_file_path: Path,
    ) -> List[ReferenceRecord]:
        # Step 1: Get all definition locations to filter them out later
        definition_sites = self._get_definition_sites(griffe_module)

        # Step 2: Build a map of local names to their resolved SURIs
        local_symbols = self._build_local_symbols_map(griffe_module)

        # Step 3: Parse with LibCST and run the usage visitor
        try:
            cst_module = cst.parse_module(content)
            wrapper = cst.MetadataWrapper(cst_module)
        except cst.ParserSyntaxError:
            return []  # Can't analyze syntax errors

        registry = UsageRegistry()
        module_fqn = rel_path.removesuffix(".py").replace("/", ".")
        is_init = abs_file_path.name == "__init__.py"

        visitor = UsageScanVisitor(
            file_path=abs_file_path,
            local_symbols=local_symbols,
            registry=registry,
            current_module_fqn=module_fqn,
            is_init_file=is_init,
        )
        wrapper.visit(visitor)

        # Step 4: Convert visitor results to ReferenceRecords, filtering out definitions
        references: List[ReferenceRecord] = []
        for target_suri, locations in registry._index.items():
            for loc in locations:
                if (loc.lineno, loc.col_offset) in definition_sites:
                    continue  # Skip self-referential definitions

                references.append(
                    ReferenceRecord(
                        target_id=target_suri,
                        kind=loc.ref_type.value,
                        location_start=loc.lineno,
                        location_end=loc.end_lineno,
                    )
                )
        return references
~~~~~

#### Acts 3: 添加集成测试

我将创建一个新的测试文件来验证引用提取逻辑。该测试将建立一个多文件 Python 包，并断言 `PythonAdapter` 能正确识别跨文件的符号用法，并将其链接到正确的别名 SURI。

~~~~~act
write_file
packages/stitcher-python-adapter/tests/integration/test_index_adapter_references.py
~~~~~
~~~~~python
from pathlib import Path

from stitcher.adapter.python import PythonAdapter
from stitcher.test_utils import WorkspaceFactory


def test_reference_extraction_with_aliases(tmp_path: Path):
    """
    Verify that reference extraction correctly identifies usages and
    links them to the SURI of the alias in __init__.py, not the
    original definition.
    """
    # Arrange: Create a project with a nested module and an alias
    wf = WorkspaceFactory(tmp_path)
    wf.with_source(
        "pkg/core.py",
        """
    class App:
        '''The main application class.'''
        pass
    """,
    )
    wf.with_source(
        "pkg/__init__.py",
        """
    from .core import App
    """,
    )
    wf.with_source(
        "main.py",
        """
    from pkg import App

    # This is a usage of the App alias
    instance = App()
    """,
    )
    wf.build()

    adapter = PythonAdapter(root_path=tmp_path)

    # Act: Parse the file that uses the alias
    main_py_path = tmp_path / "main.py"
    main_content = main_py_path.read_text()
    _, references = adapter.parse(main_py_path, main_content)

    # Assert
    assert (
        len(references) >= 2
    ), "Should find at least references for the import and the instantiation"

    # The key assertion: the target SURI must point to the alias in __init__.py
    expected_target_suri = "py://pkg/__init__.py#App"

    # Find the reference for the `App()` instantiation on line 5
    app_usage_ref = None
    for ref in references:
        if ref.target_id == expected_target_suri and ref.location_start == 5:
            app_usage_ref = ref
            break

    assert (
        app_usage_ref is not None
    ), f"Did not find reference to '{expected_target_suri}' on line 5"
    assert app_usage_ref.kind == "symbol"

    # Find the reference for the `from pkg import App` statement on line 2
    import_usage_ref = None
    for ref in references:
        if ref.target_id == expected_target_suri and ref.location_start == 2:
            import_usage_ref = ref
            break

    assert (
        import_usage_ref is not None
    ), f"Did not find import reference to '{expected_target_suri}' on line 2"
    assert import_usage_ref.kind == "symbol"
~~~~~

### 下一步建议

我们已经成功地为索引填充了引用数据。下一步的关键是解决 **`1.1. 债务：不精确的符号位置`**。

当前，所有 `SymbolRecord` 的位置信息都被硬编码为 0。为了支持 IDE 的“跳转到定义”和精确的代码重构，我们需要：
1.  增强 `ModuleDef` 中间表示，使其能够携带从 Griffe 解析器获得的精确行号和列号信息。
2.  修改 `PythonAdapter._extract_symbols` 方法，将这些精确的位置信息传递给 `SymbolRecord`。

完成这项工作后，`stitcher-index` 将同时拥有符号的“定义”和“使用”的精确位置，构成一个功能完备的语义图谱。
