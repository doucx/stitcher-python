好的，我们将开始执行“Stitcher 2.0 实施路线图”的阶段 1。

第一步是升级 `stitcher-index` 的底层存储结构，使其能够承载新的语义数据（签名文本和文档哈希）。

## [WIP] feat: 扩展 stitcher-index Schema 以支持签名文本和文档哈希

### 用户需求
根据 [Stitcher 2.0 确定性链接实施路线图：Index-First 架构](Stitcher%202.0%20确定性链接实施路线图：Index-First%20架构.md)，为了实现 "Query-First" 的运行模式，`stitcher-index` 必须存储代码实体的原始签名文本 (`signature_text`) 和文档字符串的哈希值 (`docstring_hash`)。这将允许上层应用（如 `check` 和 `pump`）直接通过数据库查询进行比对，而无需再次读取源码文件。

### 评论
这是一个基础性的架构变更。通过在索引层持久化这些信息，我们将“源码解析”这一昂贵操作的频率降到了最低（仅在文件变更时发生），从而为后续的高性能操作奠定基础。

### 目标
1.  修改 `schema.sql`，在 `symbols` 表中增加 `signature_text` 和 `docstring_hash` 两个字段。
2.  更新 `SymbolRecord` 数据类，使其包含这两个新字段。
3.  更新 `IndexStore.update_analysis` 方法，确保新字段被正确写入数据库。

### 基本原理
目前的 Schema 仅存储了位置和结构哈希，对于需要展示 Diff 或判断文档是否过时的场景（Check/Pump），信息量不足。新增的字段填补了这一空白：
- `signature_text`:用于在 CLI 中直接展示“签名漂移”的 Diff，无需读取磁盘上的旧文件。
- `docstring_hash`: 用于快速判断文档是否发生变更，作为“脏检查”的依据。

### 标签
#intent/build #flow/ready #priority/high #comp/engine #concept/state #scope/core #ai/instruct #task/domain/storage #task/object/stitcher-index #task/action/upgrade-schema #task/state/begin

---

### Script

#### Acts 1: 扩展数据库 Schema

在 `symbols` 表中添加 `signature_text` 和 `docstring_hash` 字段。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/schema.sql
~~~~~
~~~~~sql.old
    -- Structural hash of the symbol's signature
    signature_hash TEXT,

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
~~~~~
~~~~~sql.new
    -- Structural hash of the symbol's signature
    signature_hash TEXT,
    
    -- The raw text signature of the symbol (e.g. "def foo(a: int) -> str:")
    signature_text TEXT,
    
    -- The SHA256 hash of the docstring content
    docstring_hash TEXT,

    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
~~~~~

#### Acts 2: 更新 SymbolRecord 数据模型

在 `SymbolRecord` 数据类中添加对应的可选字段。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/types.py
~~~~~
~~~~~python.old
    canonical_fqn: Optional[str] = None
    alias_target_fqn: Optional[str] = None
    alias_target_id: Optional[str] = None
    signature_hash: Optional[str] = None
~~~~~
~~~~~python.new
    canonical_fqn: Optional[str] = None
    alias_target_fqn: Optional[str] = None
    alias_target_id: Optional[str] = None
    signature_hash: Optional[str] = None
    signature_text: Optional[str] = None
    docstring_hash: Optional[str] = None
~~~~~

#### Acts 3: 更新数据库写入逻辑

修改 `IndexStore.update_analysis` 方法，在插入符号时包含新字段。

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
~~~~~
~~~~~python.new
            # 2. Insert new symbols
            if symbols:
                conn.executemany(
                    """
                    INSERT INTO symbols (
                        id, file_id, name, logical_path, kind, 
                        canonical_fqn, alias_target_fqn, alias_target_id,
                        lineno, col_offset, end_lineno, end_col_offset, signature_hash,
                        signature_text, docstring_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                            s.signature_text,
                            s.docstring_hash,
                        )
                        for s in symbols
                    ],
                )
~~~~~

### 下一步建议

完成 Schema 升级后，我们需要立即升级 `PythonAdapter` 以填充这些新字段。具体的下一步是：
1.  在 `stitcher-python-adapter` 中实现 `DocstringHasher`。
2.  更新 `PythonAdapter` 的提取逻辑，计算并填充 `signature_text` 和 `docstring_hash`。
