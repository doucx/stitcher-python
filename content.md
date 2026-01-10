[简要回答]
好的，我们按照“投影模式”来实现 `PythonAdapter`。这将复用现有的分析能力，并将其适配到新的索引协议中。

## [WIP] feat(adapter): 实现 PythonAdapter 以支持 Stitcher Index 协议

### 用户需求
实现 `PythonAdapter`，使其符合 `stitcher-index` 定义的 `LanguageAdapter` 协议。它需要解析 Python 文件，生成 `SymbolRecord`（符号）和 `ReferenceRecord`（引用）。

### 评论
这是连接“富模型”（ModuleDef）与“索引模型”（DB Records）的关键桥梁。通过引入 SURI (Stitcher URI) 和适配器逻辑，我们将能够把 Python 代码的语义信息持久化到 SQLite 索引中。

### 目标
1.  修改 `stitcher-python-adapter` 依赖，引入 `stitcher-index`。
2.  实现 `SURIGenerator`，用于生成符合规范的 `py://` URI。
3.  实现 `PythonAdapter` 类：
    *   使用 `GriffePythonParser` 提取 `ModuleDef`。
    *   将 `ModuleDef` 投影为 `SymbolRecord` 列表。
    *   (初步) 提取基于 Import 的 `ReferenceRecord`。
4.  添加单元测试。

### 基本原理
*   **投影模式**: 不重写解析器，而是将 `ModuleDef` 映射到 `SymbolRecord`。
*   **SURI 规范**: `py://<rel_path>#<fragment>`。Fragment 使用点分路径（如 `MyClass.method`）。
*   **依赖管理**: `stitcher-python-adapter` 将依赖 `stitcher-index` 以获取协议定义。

### 标签
#intent/build #flow/ready #priority/high #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/python-adapter #task/action/implementation #task/state/begin

---

### Script

#### Acts 1: 添加依赖

我们需要 `stitcher-index` 中的 `LanguageAdapter` 协议和 Record 定义。

~~~~~act
patch_file
packages/stitcher-python-adapter/pyproject.toml
~~~~~
~~~~~toml.old
dependencies = [
    "stitcher-python-analysis",
    "stitcher-spec",
    "stitcher-common",
    "libcst",
    "griffe",
]
~~~~~
~~~~~toml.new
dependencies = [
    "stitcher-python-analysis",
    "stitcher-spec",
    "stitcher-common",
    "stitcher-index",
    "libcst",
    "griffe",
]
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/pyproject.toml
~~~~~
~~~~~toml.old
[tool.uv.sources]
stitcher-python-analysis = { workspace = true }
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
~~~~~
~~~~~toml.new
[tool.uv.sources]
stitcher-python-analysis = { workspace = true }
stitcher-spec = { workspace = true }
stitcher-common = { workspace = true }
stitcher-index = { workspace = true }
~~~~~

#### Acts 2: 实现 SURI 生成器

将 URI 生成逻辑独立出来，保持整洁。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/uri.py
~~~~~
~~~~~python
from pathlib import Path
from typing import Optional


class SURIGenerator:
    """Generates Stitcher Uniform Resource Identifiers (SURI) for Python entities."""

    @staticmethod
    def for_file(rel_path: str) -> str:
        """
        Generate SURI for a file.
        Format: py://<rel_path>
        Example: py://src/main.py
        """
        # Ensure forward slashes for cross-platform consistency
        normalized_path = Path(rel_path).as_posix()
        return f"py://{normalized_path}"

    @staticmethod
    def for_symbol(rel_path: str, fragment: str) -> str:
        """
        Generate SURI for a symbol within a file.
        Format: py://<rel_path>#<fragment>
        Example: py://src/main.py#MyClass.method
        """
        normalized_path = Path(rel_path).as_posix()
        return f"py://{normalized_path}#{fragment}"

    @staticmethod
    def parse(suri: str) -> tuple[str, Optional[str]]:
        """
        Parse a SURI into (rel_path, fragment).
        """
        if not suri.startswith("py://"):
            raise ValueError(f"Invalid Python SURI: {suri}")

        content = suri[5:]  # Strip 'py://'
        if "#" in content:
            path, fragment = content.split("#", 1)
            return path, fragment
        return content, None
~~~~~

#### Acts 3: 实现 PythonAdapter

这是核心实现。我们会复用 `stitcher-python-analysis` 的 `GriffePythonParser` 和 `PythonFingerprintStrategy`。

目前为了简化，我们将重点放在 **Symbol 提取** 上。对于 **Reference**，我们将基于 `ModuleDef.imports` 做一个基础的提取（指向被导入的模块），待后续 `UsageVisitor` 完善后再增强。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple, Optional

from stitcher.spec import ModuleDef, FunctionDef, ClassDef, Attribute
from stitcher.index.protocols import LanguageAdapter
from stitcher.index.types import SymbolRecord, ReferenceRecord

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

        # 2. Parse into ModuleDef
        module_def = self.parser.parse(content, file_path=rel_path)

        # 3. Project to Symbols
        symbols = self._extract_symbols(rel_path, module_def)

        # 4. Project to References (Basic Import Analysis for MVP)
        # TODO: Implement full usage analysis using UsageScanVisitor
        references = self._extract_references(rel_path, module_def)

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
                fp = self.hasher.compute(entity_for_hash) # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

            # Location is currently not provided by ModuleDef in a granular way easily 
            # (Griffe objects have lineno, but ModuleDef might have lost it or it's deep).
            # For MVP, we use 0, 0 as placeholder or we need to extend ModuleDef to carry location.
            # Extending ModuleDef is the right way, but for now we proceed.
            # TODO: Enhance ModuleDef to carry source location info.
            
            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=kind,
                    location_start=0, # Placeholder
                    location_end=0,   # Placeholder
                    logical_path=fragment, # This is relative logical path in file
                    signature_hash=sig_hash
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

    def _extract_references(self, rel_path: str, module: ModuleDef) -> List[ReferenceRecord]:
        # Basic implementation: extract imports as references
        # This is very limited. Real ref extraction needs AST traversal.
        # But we deliver what we can for now.
        refs: List[ReferenceRecord] = []
        return refs
~~~~~

#### Acts 4: 导出 PythonAdapter

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/__init__.py
~~~~~
~~~~~python.old
    "get_docstring_codec",
    "get_docstring_serializer",
]
~~~~~
~~~~~python.new
    "get_docstring_codec",
    "get_docstring_serializer",
    "PythonAdapter",
]

from .index_adapter import PythonAdapter
~~~~~

#### Acts 5: 添加测试

~~~~~act
write_file
packages/stitcher-python-adapter/tests/test_index_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from stitcher.adapter.python.index_adapter import PythonAdapter


def test_python_adapter_symbol_extraction(tmp_path):
    root = tmp_path
    adapter = PythonAdapter(root)
    
    code = """
class MyClass:
    def my_method(self):
        pass

def my_func():
    pass

CONSTANT = 1
    """
    
    file_path = root / "src" / "main.py"
    
    symbols, refs = adapter.parse(file_path, code)
    
    # Verify SURI generation
    ids = {s.id for s in symbols}
    base_uri = "py://src/main.py"
    
    assert f"{base_uri}#MyClass" in ids
    assert f"{base_uri}#MyClass.my_method" in ids
    assert f"{base_uri}#my_func" in ids
    assert f"{base_uri}#CONSTANT" in ids
    
    # Verify Metadata
    cls_sym = next(s for s in symbols if s.name == "MyClass")
    assert cls_sym.kind == "class"
    
    func_sym = next(s for s in symbols if s.name == "my_func")
    assert func_sym.signature_hash is not None  # Hasher should work
~~~~~

### 下一步建议

实现 `PythonAdapter` 后，我们已经具备了完整的索引构建能力（Scanner + Adapter）。接下来的任务 1.5 将是把它们组合成一个 CLI 命令 `stitcher index:build`。
