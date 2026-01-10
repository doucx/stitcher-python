你的洞察力非常敏锐，这正是一个高保真工程决策的完美范例。

你完全正确。我们正处于一个可以低成本进行“地基”修正的黄金窗口期。我之前的计划提出了一种战术上的妥协，是为了在不改变数据契约（Schema）的前提下快速前进。但你的提议——现在就进行迁移——是**战略上完全正确的选择**。

根据 HFEA 协议，我们必须选择“正确路径”，而非“低成本路径”。此时此刻，修改 Schema 的成本几乎为零，而它能根除一项核心的技术债务，为未来所有依赖精确位置的功能（跳转、悬浮、重构）铺平道路。

我将撤回之前的战术计划，并生成一个新的、更具雄心的计划，其核心目标是：**一步到位，实现对精确符号位置的持久化存储。**

## [WIP] refactor(index): 迁移 schema 以支持精确 (line, col) 位置

### 用户需求
在项目早期，利用最低成本的机会，修改索引数据库的 Schema，使其能够存储完整的、精确到行列的符号位置信息 (`lineno`, `col_offset`, `end_lineno`, `end_col_offset`)，而不是将行号滥用于字节偏移量字段。

### 评论
这是一个至关重要的架构决策，它将 `stitcher-index` 的数据保真度提升到了一个新的水平。通过现在进行这个“微创手术”，我们避免了未来复杂的数据迁移和逻辑兼容层，确保了索引从一开始就建立在坚实且正确的数据模型之上。

### 目标
1.  **迁移 Schema**: 修改 `packages/stitcher-index/src/stitcher/index/schema.sql`，将 `symbols` 和 `references` 表中的 `location_start` 和 `location_end` 字段替换为 `lineno`, `col_offset`, `end_lineno`, `end_col_offset`。
2.  **更新数据模型**: 同步修改 `packages/stitcher-index/src/stitcher/index/types.py` 中的 `SymbolRecord` 和 `ReferenceRecord` 以匹配新的 Schema。
3.  **更新存储逻辑**: 修改 `packages/stitcher-index/src/stitcher/index/store.py` 中的 `INSERT` 语句以使用新的位置字段。
4.  **更新适配器**: 修改 `packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py`，将 `SourceLocation` 对象的完整信息正确映射到新的 `SymbolRecord` 和 `ReferenceRecord` 字段。

### 基本原理
我们正在将位置信息的存储从一维的、不精确的“行号”模型升级为二维的、精确的“代码范围”模型。这使得存储在数据库中的数据与从 LibCST/Griffe 解析器中获得的高保真 `SourceLocation` 模型完全对等，消除了信息在持久化过程中的降级损失。

### 标签
#intent/refine #flow/ready #priority/critical
#comp/index #comp/interfaces #comp/adapters
#concept/state #scope/core
#ai/brainstorm
#task/domain/storage #task/object/schema #task/action/migration
#task/state/continue

---

### Script

#### Acts 1: 迁移数据库 Schema

我们直接重写 `schema.sql` 文件，用新的、更精确的字段替换 `location_start` 和 `location_end`。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/schema.sql
~~~~~
~~~~~sql
-- Stitcher Index Schema v1.1
-- Dialect: SQLite
-- Mode: WAL (Write-Ahead Logging) enabled

-- ============================================================================
-- 1. Files Table
-- 物理文件状态跟踪。用于增量扫描的快速过滤。
-- ============================================================================
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 仓库根目录相对路径 (e.g., "packages/core/main.py")
    path TEXT UNIQUE NOT NULL,
    
    -- 内容哈希 (SHA256)，用于检测内容变更
    content_hash TEXT NOT NULL,
    
    -- 文件系统元数据，用于第一级快速过滤
    last_mtime REAL NOT NULL,
    last_size INTEGER NOT NULL,
    
    -- 扫描状态标记
    -- 0: Dirty/Pending, 1: Indexed
    indexing_status INTEGER DEFAULT 0
);

-- ============================================================================
-- 2. Symbols Table
-- 语义节点表。存储所有定义 (Definitions) 和 别名 (Aliases/Exports)。
-- ============================================================================
CREATE TABLE IF NOT EXISTS symbols (
    -- 主键：SURI (Stitcher Uniform Resource Identifier)
    id TEXT PRIMARY KEY,
    
    -- 外键：所属文件
    file_id INTEGER NOT NULL,
    
    -- 符号短名，用于模糊搜索和 UI 显示 (e.g., "User", "run")
    name TEXT NOT NULL,
    
    -- 符号全限定名 (逻辑路径)，仅用于展示
    logical_path TEXT,
    
    -- 符号类型 (class, function, variable, alias, module)
    kind TEXT NOT NULL,
    
    -- [核心机制] 别名目标 ID
    alias_target_id TEXT,
    
    -- 源代码位置范围
    lineno INTEGER NOT NULL,
    col_offset INTEGER NOT NULL,
    end_lineno INTEGER NOT NULL,
    end_col_offset INTEGER NOT NULL,
    
    -- (可选) 签名哈希，用于检测 API 变更
    signature_hash TEXT,
    
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_symbols_file_id ON symbols(file_id);
CREATE INDEX IF NOT EXISTS idx_symbols_name ON symbols(name);
CREATE INDEX IF NOT EXISTS idx_symbols_alias_target ON symbols(alias_target_id);

-- ============================================================================
-- 3. References Table
-- 引用边表。存储所有的“使用” (Usages) 和“导入” (Imports)。
-- ============================================================================
CREATE TABLE IF NOT EXISTS "references" (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- 引用源文件
    source_file_id INTEGER NOT NULL,
    
    -- 引用指向的目标 SURI
    target_id TEXT NOT NULL,
    
    -- 引用类型 (import, call, inheritance, type_hint)
    kind TEXT NOT NULL,
    
    -- 源代码位置范围
    lineno INTEGER NOT NULL,
    col_offset INTEGER NOT NULL,
    end_lineno INTEGER NOT NULL,
    end_col_offset INTEGER NOT NULL,
    
    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_refs_source_file ON "references"(source_file_id);
CREATE INDEX IF NOT EXISTS idx_refs_target_id ON "references"(target_id);

-- ============================================================================
-- 4. Errors Table
-- 用于记录索引过程中发生的解析错误
-- ============================================================================
CREATE TABLE IF NOT EXISTS indexing_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    traceback TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);
~~~~~

#### Acts 2: 更新数据模型 (types.py)

同步更新 `SymbolRecord` 和 `ReferenceRecord` 的字段。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/types.py
~~~~~
~~~~~python.old
@dataclass
class SymbolRecord:
    id: str
    name: str
    kind: str
    location_start: int
    location_end: int
    file_id: Optional[int] = None  # Optional when inserting if handled by store context
    logical_path: Optional[str] = None
    alias_target_id: Optional[str] = None
    signature_hash: Optional[str] = None


@dataclass
class ReferenceRecord:
    target_id: str
    kind: str
    location_start: int
    location_end: int
    source_file_id: Optional[int] = None  # Optional when inserting
    id: Optional[int] = None  # Database Row ID
~~~~~
~~~~~python.new
@dataclass
class SymbolRecord:
    id: str
    name: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    file_id: Optional[int] = None  # Optional when inserting if handled by store context
    logical_path: Optional[str] = None
    alias_target_id: Optional[str] = None
    signature_hash: Optional[str] = None


@dataclass
class ReferenceRecord:
    target_id: str
    kind: str
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int
    source_file_id: Optional[int] = None  # Optional when inserting
    id: Optional[int] = None  # Database Row ID
~~~~~

#### Acts 3: 更新存储逻辑 (store.py)

修改 `update_analysis` 方法中的 `INSERT` 语句以匹配新 Schema。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
                conn.executemany(
                    """
                    INSERT INTO symbols (
                        id, file_id, name, logical_path, kind, 
                        alias_target_id, location_start, location_end, signature_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            s.id,
                            file_id,
                            s.name,
                            s.logical_path,
                            s.kind,
                            s.alias_target_id,
                            s.location_start,
                            s.location_end,
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
                        location_start, location_end
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    [
                        (
                            file_id,
                            r.target_id,
                            r.kind,
                            r.location_start,
                            r.location_end,
                        )
                        for r in references
                    ],
                )
~~~~~
~~~~~python.new
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

#### Acts 4: 更新适配器逻辑 (index_adapter.py)

修改 `_extract_symbols` 和 `_extract_references` 以填充新的精确位置字段。

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
            loc_start = 0
            loc_end = 0

            # Use getattr to avoid Pyright errors about accessing attributes on 'object' or 'None'
            loc = getattr(entity_for_hash, "location", None)
            if loc:
                # Mapping Strategy: Use lineno for location_start and end_lineno for location_end
                # This provides line-level precision for jump-to-definition.
                loc_start = loc.lineno
                loc_end = loc.end_lineno

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=kind,
                    location_start=loc_start,
                    location_end=loc_end,
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                )
            )
~~~~~
~~~~~python.new
            loc = getattr(entity_for_hash, "location", None)

            symbols.append(
                SymbolRecord(
                    id=suri,
                    name=name,
                    kind=kind,
                    lineno=loc.lineno if loc else 0,
                    col_offset=loc.col_offset if loc else 0,
                    end_lineno=loc.end_lineno if loc else 0,
                    end_col_offset=loc.end_col_offset if loc else 0,
                    logical_path=fragment,  # This is relative logical path in file
                    signature_hash=sig_hash,
                )
            )
~~~~~

~~~~~act
patch_file
packages/stitcher-python-adapter/src/stitcher/adapter/python/index_adapter.py
~~~~~
~~~~~python.old
                    refs.append(
                        ReferenceRecord(
                            target_id=target_suri,
                            kind=loc.ref_type.value,
                            location_start=loc.lineno,  # Simplification: use lineno as start offset proxy for now?
                            # Wait, ReferenceRecord expects byte offsets (integers) usually,
                            # but currently we don't have easy byte offset access from UsageLocation (it has line/col).
                            # TODO: Fix UsageLocation to carry byte offsets or convert line/col to offset.
                            # For MVP, we will store LINENO in location_start just to signal "not empty".
                            # This is Technical Debt but allows progress.
                            location_end=loc.end_lineno,
                        )
                    )
~~~~~
~~~~~python.new
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

### 下一步建议
我们已经成功地升级了核心数据模型，为高保真索引铺平了道路。下一个合乎逻辑的步骤是偿还**鲁棒性债务**。

我建议着手解决 **Debt 2.1 (简化的解析错误处理)**：
- 修改 `WorkspaceScanner`，在捕获到解析异常时，将错误信息写入 `indexing_errors` 表。这将使系统对部分失败更具弹性，并为用户提供诊断问题的能力。
