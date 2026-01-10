## [WIP] feat: Implement database layer for stitcher-index

### 用户需求

实现 `stitcher-index` 的数据库层，包括：
1.  将之前确定的 Schema 定义为 SQL 文件。
2.  创建 Python 类型定义 (`types.py`) 以对应数据库实体。
3.  实现数据库连接管理 (`db.py`)，确保 SQLite 配置正确（WAL 模式）。
4.  实现 CRUD 操作封装 (`store.py`)，支持文件同步和符号/引用的原子更新。
5.  编写单元测试验证上述功能。

### 评论

这是构建语义索引的基础。一个健壮的数据库层能为上层的扫描器和查询器提供坚实的支撑。我们在设计时特别注意了 SQLite 的并发性能配置（WAL）以及更新操作的原子性（事务管理），以确保在增量索引过程中数据的完整性。

### 目标

1.  在 `packages/stitcher-index/src/stitcher/index/` 下创建 `schema.sql`, `types.py`, `db.py`, `store.py`。
2.  在 `packages/stitcher-index/tests/` 下创建测试脚手架和单元测试。

### 基本原理

*   **Schema**: 采用 "Stitcher Index Schema v1.0"，支持 URI 主键和 Alias 机制。
*   **连接管理**: 使用 `contextmanager` 管理连接，强制开启 `WAL` 模式和 `foreign_keys` 约束。
*   **CRUD**: `IndexStore` 提供面向业务的高级接口（如 `update_analysis`），而不是暴露原始 SQL，从而屏蔽底层事务的复杂性。
*   **测试**: 遵循 Monorepo 测试架构，测试文件与包共存，并使用 `tmp_path` 确保测试环境隔离。

### 标签

#intent/build #flow/ready #priority/high #comp/engine #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/stitcher-index #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 定义 Schema 和数据类型

首先，我们将 Schema 保存为 SQL 文件，并定义相应的 Python Dataclass，以便在代码中以类型安全的方式操作数据。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/schema.sql
~~~~~
~~~~~sql
-- Stitcher Index Schema v1.0
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
    
    -- 源代码位置范围 (字节偏移量)
    location_start INTEGER NOT NULL,
    location_end INTEGER NOT NULL,
    
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
    location_start INTEGER NOT NULL,
    location_end INTEGER NOT NULL,
    
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
~~~~~

#### Acts 2: 实现数据库连接管理

这里我们实现 `DatabaseManager`，负责 SQLite 连接的生命周期和配置。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/db.py
~~~~~
~~~~~python
import sqlite3
import logging
from pathlib import Path
from typing import Optional, Generator
from contextlib import contextmanager
try:
    from importlib.resources import files
except ImportError:
    # For Python < 3.9 compatibility if needed, though project requires >=3.10
    from importlib_resources import files  # type: ignore

log = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_raw_connection(self) -> sqlite3.Connection:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        
        # Performance & Integrity optimizations
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA foreign_keys = ON;")
        
        # Return rows as sqlite3.Row for dict-like access
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self) -> None:
        """Loads schema.sql and initializes the database tables."""
        schema_path = files("stitcher.index").joinpath("schema.sql")
        schema_sql = schema_path.read_text(encoding="utf-8")
        
        with self.get_connection() as conn:
            conn.executescript(schema_sql)
            log.debug(f"Initialized database at {self.db_path}")

    @contextmanager
    def get_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Yields a managed connection. 
        Commits on success, rolls back on exception.
        Closes connection at the end.
        """
        conn = self._get_raw_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
~~~~~

#### Acts 3: 实现 CRUD 操作 (`IndexStore`)

这是核心逻辑层，封装了具体的 SQL 操作。

~~~~~act
write_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python
from typing import Optional, List, Tuple
from .db import DatabaseManager
from .types import FileRecord, SymbolRecord, ReferenceRecord


class IndexStore:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def sync_file(
        self, path: str, content_hash: str, mtime: float, size: int
    ) -> Tuple[int, bool]:
        """
        Registers a file in the index.
        Returns: (file_id, is_changed)
        is_changed is True if the file is new or content_hash changed.
        """
        with self.db.get_connection() as conn:
            cursor = conn.execute(
                "SELECT id, content_hash FROM files WHERE path = ?", (path,)
            )
            row = cursor.fetchone()

            if row:
                file_id = row["id"]
                old_hash = row["content_hash"]
                if old_hash != content_hash:
                    # Content changed: update metadata and mark as dirty
                    conn.execute(
                        """
                        UPDATE files 
                        SET content_hash = ?, last_mtime = ?, last_size = ?, indexing_status = 0
                        WHERE id = ?
                        """,
                        (content_hash, mtime, size, file_id),
                    )
                    return file_id, True
                else:
                    # Content same: just update stat metadata to prevent rescans
                    conn.execute(
                        """
                        UPDATE files 
                        SET last_mtime = ?, last_size = ? 
                        WHERE id = ?
                        """,
                        (mtime, size, file_id),
                    )
                    return file_id, False
            else:
                # New file
                cursor = conn.execute(
                    """
                    INSERT INTO files (path, content_hash, last_mtime, last_size, indexing_status)
                    VALUES (?, ?, ?, ?, 0)
                    """,
                    (path, content_hash, mtime, size),
                )
                return cursor.lastrowid, True

    def get_file_by_path(self, path: str) -> Optional[FileRecord]:
        with self.db.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE path = ?", (path,)
            ).fetchone()
            if row:
                return FileRecord(**dict(row))
        return None

    def update_analysis(
        self,
        file_id: int,
        symbols: List[SymbolRecord],
        references: List[ReferenceRecord],
    ) -> None:
        """
        Atomically replaces all symbols and references for a file, 
        and marks the file as indexed.
        """
        with self.db.get_connection() as conn:
            # 1. Clear old data for this file
            conn.execute("DELETE FROM symbols WHERE file_id = ?", (file_id,))
            conn.execute("DELETE FROM 'references' WHERE source_file_id = ?", (file_id,))

            # 2. Insert new symbols
            if symbols:
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

            # 4. Mark as indexed
            conn.execute(
                "UPDATE files SET indexing_status = 1 WHERE id = ?", (file_id,)
            )

    def get_symbols_by_file(self, file_id: int) -> List[SymbolRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM symbols WHERE file_id = ?", (file_id,)
            ).fetchall()
            return [SymbolRecord(**dict(row)) for row in rows]

    def get_references_by_file(self, file_id: int) -> List[ReferenceRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM 'references' WHERE source_file_id = ?", (file_id,)
            ).fetchall()
            return [ReferenceRecord(**dict(row)) for row in rows]
~~~~~

#### Acts 4: 创建测试脚手架和测试用例

我们使用 `pytest` 进行验证。

~~~~~act
run_command
~~~~~
~~~~~bash
mkdir -p packages/stitcher-index/tests/unit
~~~~~
~~~~~act
write_file
packages/stitcher-index/tests/conftest.py
~~~~~
~~~~~python
import pytest
from pathlib import Path
from stitcher.index.db import DatabaseManager
from stitcher.index.store import IndexStore

@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "index.db"

@pytest.fixture
def db_manager(db_path):
    manager = DatabaseManager(db_path)
    manager.initialize()
    return manager

@pytest.fixture
def store(db_manager):
    return IndexStore(db_manager)
~~~~~

~~~~~act
write_file
packages/stitcher-index/tests/unit/test_store.py
~~~~~
~~~~~python
import pytest
from stitcher.index.types import SymbolRecord, ReferenceRecord

def test_file_lifecycle(store):
    # 1. Sync new file
    fid, changed = store.sync_file("src/main.py", "hash1", 100.0, 50)
    assert changed is True
    assert fid is not None
    
    rec = store.get_file_by_path("src/main.py")
    assert rec.indexing_status == 0  # Starts as dirty
    assert rec.content_hash == "hash1"

    # 2. Sync unchanged file
    fid2, changed = store.sync_file("src/main.py", "hash1", 101.0, 50)
    assert changed is False
    assert fid2 == fid
    
    # 3. Sync changed file
    fid3, changed = store.sync_file("src/main.py", "hash2", 102.0, 60)
    assert changed is True
    
    rec = store.get_file_by_path("src/main.py")
    assert rec.content_hash == "hash2"
    assert rec.indexing_status == 0

def test_analysis_update(store):
    fid, _ = store.sync_file("src/lib.py", "h1", 100, 10)
    
    symbols = [
        SymbolRecord(
            id="py://src/lib.py#User",
            name="User",
            kind="class",
            location_start=0,
            location_end=10,
            logical_path="lib.User"
        )
    ]
    
    references = [
        ReferenceRecord(
            target_id="py://src/other.py#func",
            kind="import",
            location_start=5,
            location_end=15
        )
    ]
    
    # Update
    store.update_analysis(fid, symbols, references)
    
    # Verify file is marked indexed
    rec = store.get_file_by_path("src/lib.py")
    assert rec.indexing_status == 1
    
    # Verify symbols
    saved_syms = store.get_symbols_by_file(fid)
    assert len(saved_syms) == 1
    assert saved_syms[0].name == "User"
    
    # Verify references
    saved_refs = store.get_references_by_file(fid)
    assert len(saved_refs) == 1
    assert saved_refs[0].target_id == "py://src/other.py#func"

def test_analysis_replacement(store):
    """Ensure old analysis data is wiped on update"""
    fid, _ = store.sync_file("src/lib.py", "h1", 100, 10)
    
    # First update
    store.update_analysis(fid, [
        SymbolRecord(id="s1", name="s1", kind="v", location_start=0, location_end=1)
    ], [])
    
    assert len(store.get_symbols_by_file(fid)) == 1
    
    # Second update (empty)
    store.update_analysis(fid, [], [])
    
    assert len(store.get_symbols_by_file(fid)) == 0
~~~~~

### 下一步建议

数据库层就位后，下一步我们应该实现 **任务 1.3: 增量扫描流水线**。

这涉及：
1.  创建一个 `WorkspaceScanner` 类。
2.  实现 "Discovery" 阶段（集成 `git ls-files`）。
3.  实现 "Stat Check" 和 "Hash Check" 阶段，利用我们刚刚创建的 `store.sync_file` 来过滤文件。

如果你同意，我将为你生成实现扫描流水线的计划。
