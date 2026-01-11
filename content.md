好的，我们正式开始实施“确定性链接”路线图中的 **Phase 1: 数据模型解耦**。

此计划将对 `stitcher-index` 的核心数据库模式进行一次外科手术式的重构。我们将修改 `symbols` 和 `references` 表，以物理性地分离“逻辑 FQN”（一个符号的声明性名称）和“物理 SURI”（一个符号在项目中的确定性位置）。这是构建 Linker 的前提条件。

## [WIP] refactor(index): Decouple logical and physical links in DB schema

### 错误分析

无。这是对“确定性链接”宏观路线图的主动实施。

### 用户需求

根据路线图 Phase 1，修改 `stitcher-index` 的数据库模式和相关的数据访问代码，以解耦符号和引用的逻辑路径 (FQN) 与物理链接 (SURI)。具体包括：
1.  在 `symbols` 表中添加 `alias_target_fqn` 字段，并将 `alias_target_id` 设为可空。
2.  在 `references` 表中添加 `target_fqn` 字段，并将 `target_id` 设为可空。

### 评论

这是一个典型的架构“正本清源”操作，完全符合 HFEA 公理。当前的数据库模式错误地将一个尚不确定的“链接意图”强制具体化为一个物理地址，导致上游 `PythonAdapter` 不得不进行“启发式猜测”。通过将 `_id` 字段（物理链接）设为可空，并引入 `_fqn` 字段（逻辑意图），我们使数据模型能够诚实地反映系统在扫描阶段的知识状态：“我知道你想引用 `pkg.mod.ClassA`，但我还不知道它在哪里”。这种本体论上的正确性是构建健壮系统的基石。

### 目标

1.  重写 `schema.sql`，修改 `symbols` 和 `references` 表的定义。
2.  更新 `types.py` 中的 `SymbolRecord` 和 `ReferenceRecord` 数据类以匹配新的数据库模式。
3.  修改 `store.py` 中的 `update_analysis` 方法，使其能够写入新的 `_fqn` 字段。
4.  修改 `index_adapter.py` 中的 `_extract_symbols` 和 `_extract_references` 方法，使其不再调用 `_guess_suri`，而是将原始 FQN 存入新字段，并将 `_id` 字段留空。

### 基本原理

我们正在将 `stitcher-index` 的工作流转变为一个两阶段过程：**扫描 (Scan)** 和 **链接 (Link)**。

-   **当前计划（扫描阶段）**：我们修改数据模型，使其能够仅记录“扫描”阶段的信息。`PythonAdapter` 在分析文件时，只负责提取它能确定的信息——即符号的定义（FQN）和引用的意图（target_FQN）。它不再承担“链接”的职责。
-   **未来计划（链接阶段）**：在所有文件都被扫描并存入数据库后，一个全新的“链接器”组件将在全知视角下运行。它会读取所有 `_fqn` 字段，并在数据库中查找匹配的定义，然后回填正确的 `_id` (SURI) 字段。

此计划通过修改数据模型，为未来的链接器铺平了道路。

### 标签

#intent/architect #flow/ready #priority/critical #comp/index #comp/python-adapter #concept/state #scope/core #ai/delegate #task/domain/architecture #task/object/component-unification #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 升级数据库 Schema

我们将重写 `schema.sql` 文件，引入新的 `_fqn` 字段，并将 `_id` 字段（外键）设置为 `NULLABLE`。

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
    -- NOTE: This column is planned for the "Linker" phase.
    canonical_fqn TEXT UNIQUE,
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

#### Acts 2: 更新数据类型 (`types.py`)

现在更新 Python 数据类以匹配新的数据库结构。

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
    id: str  # SURI
    name: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

    # Populated during Scan phase
    alias_target_fqn: Optional[str] = None
    
    # Populated during Link phase
    alias_target_id: Optional[str] = None
    canonical_fqn: Optional[str] = None
    
    file_id: Optional[int] = None
    logical_path: Optional[str] = None
    signature_hash: Optional[str] = None


@dataclass
class ReferenceRecord:
    target_fqn: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int

    # Populated during Link phase
    target_id: Optional[str] = None
    
    # Context
    source_file_id: Optional[int] = None
    id: Optional[int] = None  # Database Row ID
~~~~~

#### Acts 3: 更新数据存储层 (`store.py`)

修改 `INSERT` 语句以包含新字段。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
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
            if symbols:
                conn.executemany(
                    """
                    INSERT INTO symbols (
                        id, file_id, name, logical_path, kind,
                        alias_target_fqn, alias_target_id,
                        lineno, col_offset, end_lineno, end_col_offset, signature_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            s.id,
                            file_id,
                            s.name,
                            s.logical_path,
                            s.kind,
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

#### Acts 4: 更新 `PythonAdapter` 以填充新字段

这是关键一步：我们让 Adapter 停止猜测，只记录它确切知道的事情。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
            # Alias Handling
            alias_target_id: Optional[str] = None
            final_kind = kind
            alias_target_fqn = getattr(entity_for_hash, "alias_target", None)
            if alias_target_fqn:
                final_kind = "alias"
                alias_target_id = self._guess_suri(
                    alias_target_fqn, logical_module_fqn, rel_path
                )

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=final_kind,
                    lineno=loc.lineno if loc else 0,
                    col_offset=loc.col_offset if loc else 0,
                    end_lineno=loc.end_lineno if loc else 0,
                    end_col_offset=loc.end_col_offset if loc else 0,
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                    alias_target_id=alias_target_id,
                )
            )
~~~~~
~~~~~python.new
            # Alias Handling
            alias_target_fqn_val: Optional[str] = None
            final_kind = kind
            alias_target_fqn_from_ir = getattr(entity_for_hash, "alias_target", None)
            if alias_target_fqn_from_ir:
                final_kind = "alias"
                alias_target_fqn_val = alias_target_fqn_from_ir

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=final_kind,
                    lineno=loc.lineno if loc else 0,
                    col_offset=loc.col_offset if loc else 0,
                    end_lineno=loc.end_lineno if loc else 0,
                    end_col_offset=loc.end_col_offset if loc else 0,
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                    alias_target_fqn=alias_target_fqn_val,
                    alias_target_id=None,  # Will be populated by Linker
                )
            )
~~~~~
~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
            for target_fqn, locations in registry._index.items():
                for loc in locations:
                    # Convert logical FQN target to SURI
                    # NOTE: This is a heuristic. We don't have a SourceMap yet.
                    # We assume standard python layout: a.b.c -> py://a/b.py#c (simplified)
                    # For local symbols, we can be precise. For external, we guess.

                    target_suri = self._guess_suri(
                        target_fqn, logical_module_fqn, rel_path
                    )

                    refs.append(
                        ReferenceRecord(
                            target_id=target_suri,
                            kind=loc.ref_type.value,
                            lineno=loc.lineno,
                            col_offset=loc.col_offset,
                            end_lineno=loc.end_lineno,
                            end_col_offset=loc.end_col_offset,
                        )
                    )
~~~~~
~~~~~python.new
            for target_fqn, locations in registry._index.items():
                for loc in locations:
                    refs.append(
                        ReferenceRecord(
                            target_fqn=target_fqn,
                            target_id=None,  # Will be populated by Linker
                            kind=loc.ref_type.value,
                            lineno=loc.lineno,
                            col_offset=loc.col_offset,
                            end_lineno=loc.end_lineno,
                            end_col_offset=loc.end_col_offset,
                        )
                    )
~~~~~
~~~~~act
delete_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/uri.py
~~~~~

### 下一步建议

我们已经成功地完成了数据模型的解耦，这是整个“确定性链接”路线图中最关键的基础设施变更。`stitcher-index` 现在能够诚实地存储扫描阶段的原始信息，而不再依赖脆弱的猜测。

**下一步：执行 Phase 2: 构建全局符号映射 (Global Symbol Map)**。

我将为你生成一个计划，该计划将：
1.  在 `symbols` 表中添加 `canonical_fqn` 字段（已在本次 schema 中预留）。
2.  修改 `PythonAdapter`，使其在扫描文件时，为每个定义的符号计算并存储其全局唯一的 `canonical_fqn`。
3.  这将为我们的 Linker 提供一个快速查找“逻辑名 -> 物理位置”的索引。
