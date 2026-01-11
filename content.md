[简要回答]
我们将执行 Phase 1，重构数据模型以实现逻辑意图（FQN）与物理链接（SURI）的解耦。

## [WIP] refactor(index): 解耦数据模型，引入 FQN 字段

### 错误分析
无。这是“确定性链接”路线图的 Phase 1 实施。

### 用户需求
1.  修改数据库 Schema，引入 `canonical_fqn`, `alias_target_fqn` (Symbols) 和 `target_fqn` (References) 字段。
2.  更新 `stitcher-index` 的 `types.py` 和 `store.py` 以适配新 Schema。
3.  更新 `PythonAdapter`，停止猜测 SURI，改为提取确切的 FQN 并存入新字段。

### 评论
这是架构从“单次扫描”向“扫描-链接”二相机制转变的关键转折点。通过在数据库层和代码层明确区分“通过解析代码看到的逻辑名(FQN)”和“通过链接过程确定的物理ID(SURI)”，我们消除了扫描阶段对不完整信息的依赖（即“猜测”）。这也为后续引入 Linker 组件做好了数据准备。

### 目标
1.  更新 `schema.sql` 定义新的表结构。
2.  更新 `SymbolRecord` 和 `ReferenceRecord` 数据类。
3.  重写 `IndexStore` 的 SQL 语句以读写新字段。
4.  重构 `PythonAdapter`，利用 Phase A/B 建立的基础（`path_to_logical_fqn`, `ScopeAnalyzer`）来填充 FQN 字段，同时将 `*_id` 字段留空（待 Linker 填充）。

### 基本原理
目前的扫描器试图在只看到一个文件的情况下解决跨文件引用，这必然导致猜测。解耦后，扫描器只需诚实地记录“我看到了对 `pkg.utils.Helper` 的引用”，而不必编造一个可能错误的 `py://pkg/utils.py#Helper` SURI。这保证了扫描阶段产生的数据是绝对真实的（High Fidelity），为后续确定性的链接过程提供了可靠输入。

### 标签
#intent/refine #flow/ready #priority/high #comp/index #comp/python-adapter #scope/core #ai/delegate #task/domain/architecture #task/object/schema-decoupling #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 更新数据库 Schema

我们首先明确定义新的数据库结构。这将作为后续代码变更的契约。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/schema.sql
~~~~~
~~~~~sql
-- File System Tracking
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    content_hash TEXT NOT NULL,
    last_mtime REAL NOT NULL,
    last_size INTEGER NOT NULL,
    -- 0: Dirty (needs re-indexing), 1: Indexed
    indexing_status INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);

-- Symbol Definitions
CREATE TABLE IF NOT EXISTS symbols (
    -- Stitcher Uniform Resource Identifier (SURI) -> py://<rel_path>#<fragment>
    id TEXT PRIMARY KEY,
    file_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    
    -- The fully qualified name, unique within the project.
    -- e.g., my_pkg.utils.helper
    canonical_fqn TEXT,
    
    -- Relative logical path within the file, e.g., MyClass.my_method
    logical_path TEXT,
    kind TEXT NOT NULL,

    -- ALIAS-SPECIFIC FIELDS --
    -- The logical FQN this alias points to, extracted directly by the parser.
    -- e.g., "my_pkg.utils.helper" for "from my_pkg.utils import helper"
    alias_target_fqn TEXT,
    
    -- The resolved SURI of the target symbol (FK to symbols.id).
    -- This is populated by the Linker phase. Can be NULL if unresolved.
    alias_target_id TEXT,

    -- Location in source file
    lineno INTEGER NOT NULL,
    col_offset INTEGER NOT NULL,
    end_lineno INTEGER NOT NULL,
    end_col_offset INTEGER NOT NULL,
    
    -- Structural hash of the symbol's signature
    signature_hash TEXT,

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (alias_target_id) REFERENCES symbols(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_symbols_file_id ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_canonical_fqn ON symbols(canonical_fqn);


-- Symbol References
CREATE TABLE IF NOT EXISTS 'references' (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_file_id INTEGER NOT NULL,

    -- The logical FQN of the target, extracted by the parser.
    -- e.g., "os.path.join"
    target_fqn TEXT NOT NULL,
    
    -- The resolved SURI of the target symbol (FK to symbols.id).
    -- This is populated by the Linker phase. Can be NULL if unresolved.
    target_id TEXT,

    kind TEXT NOT NULL, -- e.g., 'import', 'call', 'annotation'
    
    -- Location of the reference in the source file
    lineno INTEGER NOT NULL,
    col_offset INTEGER NOT NULL,
    end_lineno INTEGER NOT NULL,
    end_col_offset INTEGER NOT NULL,

    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES symbols(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_references_source_file_id ON 'references'(source_file_id);
CREATE INDEX IF NOT EXISTS idx_references_target_id ON 'references'(target_id);
~~~~~

#### Acts 2: 更新 Python 数据类型

接下来，更新 `stitcher-index` 中的数据类以匹配新的 Schema。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/types.py
~~~~~
~~~~~python
from dataclasses import dataclass
from typing import Optional


@dataclass
class FileRecord:
    id: int
    path: str
    content_hash: str
    last_mtime: float
    last_size: int
    indexing_status: int


@dataclass
class SymbolRecord:
    id: str
    name: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    file_id: Optional[int] = None
    logical_path: Optional[str] = None
    canonical_fqn: Optional[str] = None
    alias_target_fqn: Optional[str] = None
    alias_target_id: Optional[str] = None
    signature_hash: Optional[str] = None


@dataclass
class ReferenceRecord:
    target_fqn: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    target_id: Optional[str] = None
    source_file_id: Optional[int] = None
    id: Optional[int] = None
~~~~~

#### Acts 3: 更新 IndexStore

修改 `IndexStore` 以处理新的字段。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
            # 2. Insert new symbols
            if symbols:
                conn.executemany(
                    """
                    INSERT INTO symbols (
                        id, file_id, name, logical_path, kind, 
                        alias_target_id, lineno, col_offset, end_lineno, end_col_offset, signature_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            s.id,
                            file_id,
                            s.name,
                            s.logical_path,
                            s.kind,
                            s.alias_target_id,
                            s.lineno,
                            s.col_offset,
                            s.end_lineno,
                            s.end_col_offset,
                            s.signature_hash,
                        )
                        for s in symbols
                    ],
                )

            # 3. Insert new references
            if references:
                conn.executemany(
                    """
                    INSERT INTO 'references' (
                        source_file_id, target_id, kind, 
                        lineno, col_offset, end_lineno, end_col_offset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            file_id,
                            r.target_id,
                            r.kind,
                            r.lineno,
                            r.col_offset,
                            r.end_lineno,
                            r.end_col_offset,
                        )
                        for r in references
                    ],
                )
~~~~~
~~~~~python.new
            # 2. Insert new symbols
            if symbols:
                conn.executemany(
                    """
                    INSERT INTO symbols (
                        id, file_id, name, logical_path, kind, 
                        canonical_fqn, alias_target_fqn, alias_target_id,
                        lineno, col_offset, end_lineno, end_col_offset, signature_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            s.id,
                            file_id,
                            s.name,
                            s.logical_path,
                            s.kind,
                            s.canonical_fqn,
                            s.alias_target_fqn,
                            s.alias_target_id,
                            s.lineno,
                            s.col_offset,
                            s.end_lineno,
                            s.end_col_offset,
                            s.signature_hash,
                        )
                        for s in symbols
                    ],
                )

            # 3. Insert new references
            if references:
                conn.executemany(
                    """
                    INSERT INTO 'references' (
                        source_file_id, target_fqn, target_id, kind, 
                        lineno, col_offset, end_lineno, end_col_offset
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            file_id,
                            r.target_fqn,
                            r.target_id,
                            r.kind,
                            r.lineno,
                            r.col_offset,
                            r.end_lineno,
                            r.end_col_offset,
                        )
                        for r in references
                    ],
                )
~~~~~

#### Acts 4: 重构 PythonAdapter

最后，彻底改造 `PythonAdapter`，移除 `_guess_suri`，并使用 Phase A/B 的成果来填充新字段。

~~~~~act
write_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python
from pathlib import Path
from typing import List, Tuple, Optional

from stitcher.spec import ModuleDef
from stitcher.index.protocols import LanguageAdapter
from stitcher.index.types import SymbolRecord, ReferenceRecord

import libcst as cst
from stitcher.adapter.python.griffe_parser import GriffePythonParser
from stitcher.adapter.python.fingerprint import PythonFingerprintStrategy
from stitcher.python.analysis.cst.usage_visitor import UsageScanVisitor, UsageRegistry
from stitcher.python.analysis.scope import ScopeAnalyzer
from stitcher.python.analysis.utils import path_to_logical_fqn
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

        # Pre-calculate logical FQN for the module
        logical_module_fqn = path_to_logical_fqn(rel_path)

        # 3. Project to Symbols
        symbols = self._extract_symbols(rel_path, module_def, logical_module_fqn)

        # 4. Project to References
        references = self._extract_references(
            rel_path, module_def, content, file_path, logical_module_fqn
        )

        return symbols, references

    def _extract_symbols(
        self, rel_path: str, module: ModuleDef, logical_module_fqn: str
    ) -> List[SymbolRecord]:
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
            canonical_fqn = f"{logical_module_fqn}.{fragment}"

            # Compute Hash
            sig_hash = None
            if entity_for_hash:
                fp = self.hasher.compute(entity_for_hash)  # type: ignore
                sig_hash = fp.get("current_code_structure_hash")

            # Location Handling
            loc = getattr(entity_for_hash, "location", None)

            # Alias Handling
            alias_target_fqn: Optional[str] = None
            final_kind = kind
            
            # Check for alias target in the entity
            target_attr = getattr(entity_for_hash, "alias_target", None)
            if target_attr:
                final_kind = "alias"
                alias_target_fqn = target_attr

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=final_kind,
                    lineno=loc.lineno if loc else 0,
                    col_offset=loc.col_offset if loc else 0,
                    end_lineno=loc.end_lineno if loc else 0,
                    end_col_offset=loc.end_col_offset if loc else 0,
                    logical_path=fragment,
                    canonical_fqn=canonical_fqn,
                    alias_target_fqn=alias_target_fqn,
                    alias_target_id=None,  # Decoupled: Linker will fill this
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
                add(attr.name, "variable", attr, parent_fragment=cls_frag)

        # 3. Module-level Attributes
        for attr in module.attributes:
            add(attr.name, "variable", attr)

        return symbols

    def _extract_references(
        self,
        rel_path: str,
        module: ModuleDef,
        content: str,
        file_path: Path,
        logical_module_fqn: str,
    ) -> List[ReferenceRecord]:
        refs: List[ReferenceRecord] = []

        # 1. Build local_symbols map using the centralized analyzer
        analyzer = ScopeAnalyzer()
        # Note: ScopeAnalyzer returns a map of {local_name: target_fqn}
        # We don't need to manually use it here because UsageScanVisitor uses it internally?
        # Wait, UsageScanVisitor takes local_symbols as input.
        local_symbols = analyzer.build_from_ir(module, logical_module_fqn)

        # 2. Parse CST and Run Visitor
        try:
            wrapper = cst.MetadataWrapper(cst.parse_module(content))
            registry = UsageRegistry()

            visitor = UsageScanVisitor(
                file_path=file_path,
                local_symbols=local_symbols,
                registry=registry,
                current_module_fqn=logical_module_fqn,
                is_init_file=rel_path.endswith("__init__.py"),
            )
            wrapper.visit(visitor)

            # 3. Convert Registry to ReferenceRecords
            # UsageRegistry structure: { target_fqn: [UsageLocation, ...] }
            for target_fqn, locations in registry.get_all_usages().items():
                for loc in locations:
                    refs.append(
                        ReferenceRecord(
                            target_fqn=target_fqn,  # Store the logical intent directly
                            target_id=None,         # Decoupled: Linker will fill this
                            kind=loc.ref_type.value,
                            lineno=loc.lineno,
                            col_offset=loc.col_offset,
                            end_lineno=loc.end_lineno,
                            end_col_offset=loc.end_col_offset,
                        )
                    )

        except Exception:
            # If CST parsing fails (syntax error), we just return empty refs
            pass

        return refs
~~~~~
~~~~~act
patch_file
packages/stitcher-python-analysis/src/stitcher/python/analysis/cst/usage_visitor.py
~~~~~
~~~~~python
    def get_usages(self, target_fqn: str) -> List[UsageLocation]:
        return self._index.get(target_fqn, [])
~~~~~
~~~~~python
    def get_usages(self, target_fqn: str) -> List[UsageLocation]:
        return self._index.get(target_fqn, [])
    
    def get_all_usages(self) -> Dict[str, List[UsageLocation]]:
        return self._index
~~~~~

### 下一步建议

我们已经完成了 Phase 1 的核心重构：
1.  数据库 Schema 已支持 FQN 存储。
2.  代码逻辑已完全解耦，“猜测 SURI” 的代码已被移除。
3.  `UsageRegistry` 增加了 `get_all_usages` 方法以便 Adapter 使用。

**注意**: 由于数据库 Schema 发生了变更，您需要手动删除现有的 `.stitcher/index/index.db` 文件，以便系统重新初始化数据库。

接下来的步骤是实现 **Phase 3: Linker**。我们需要创建一个新的 `Linker` 组件，它将查询 `symbols` 表，匹配 `canonical_fqn`，并将正确的 SURI 填入 `references` 表的 `target_id` 字段。这将最终闭合“引用-定义”的环路。
