## [WIP] fix: Resolve ReferenceRecord instantiation error and refactor terminology

### 错误分析

测试 `packages/stitcher-index/tests/unit/test_store.py::test_analysis_update` 失败，错误信息为 `TypeError: ReferenceRecord.__init__() got an unexpected keyword argument 'id'`。

这源于 `store.py` 中的 `get_references_by_file` 方法：
```python
            rows = conn.execute(
                "SELECT * FROM 'references' WHERE source_file_id = ?", (file_id,)
            ).fetchall()
            return [ReferenceRecord(**dict(row)) for row in rows]
```
数据库表 `references` 有一个 `id` 主键列（自增整数），但 `ReferenceRecord` dataclass 定义中没有包含 `id` 字段。当 `**dict(row)` 将 `id` 传递给构造函数时，导致了 TypeError。

**解决方案**:
我们需要更新 `ReferenceRecord` 定义，使其包含可选的 `id` 字段，或者在转换时排除 `id`。鉴于数据库记录通常需要 ID 进行后续操作（如删除特定引用），在 dataclass 中包含 `id` 是更优的做法。

### 用户需求

1.  修复 `test_store.py` 中的 `ReferenceRecord` 初始化错误。
2.  探讨并决定是继续使用 "id" 还是改用 "suri" (Stitcher URI) 来指代符号的全局标识符。

### 评论

关于术语选择 ("id" vs "suri")：

*   **SURI (Stitcher Uniform Resource Identifier)** 是我们定义的**格式标准**（如 `py://...`）。
*   **ID (Identifier)** 是它在数据库表中的**角色**（主键）。

在数据库 Schema (`schema.sql`) 中使用 `id` 作为列名是符合 SQL 惯例的（Primary Key 通常叫 `id`）。但在 Python 代码 (`types.py`, `store.py`) 中，为了避免混淆（特别是与整数型的 `rowid` 混淆），明确语义是有价值的。

然而，如果我们看 `SymbolRecord`，它的主键就是那个 URI 字符串。如果把它改名叫 `suri`，虽然语义明确，但与数据库列名 `id` 不一致，需要 ORM 层做映射。

**决策建议**:
保持数据库列名为 `id`（符合 SQL 范式）。但在文档和变量命名中，我们可以更明确。
对于 Python dataclass：
*   `SymbolRecord.id`: 这就是 SURI。保持 `id` 简单直接，因为它确实是对象的身份。
*   `ReferenceRecord.target_id`: 指向目标的 SURI。
*   `ReferenceRecord.id`: 引用的数据库行 ID (Integer)。

**关于你的问题 "我们是将它用 “id” 键表示更好，还使用 surl 表示更好？"**：
我认为在**代码变量名**和**文档**中强调 `suri` 是好的（例如 `target_suri`），但在**数据结构字段名**（Schema 和 Dataclass）中，`id` 更通用且不易过时。如果我们未来改变了 ID 的格式（不再是 URI），叫 `suri` 就尴尬了。

因此，我建议：**Schema 和 Dataclass 字段名保持 `id`，但在注释和逻辑变量名中使用 `suri` 来强调其格式约束。**

本次修复将集中在解决 Crash 问题上。

### 目标

1.  修改 `packages/stitcher-index/src/stitcher/index/types.py`，为 `ReferenceRecord` 添加可选的 `id: Optional[int]` 字段。
2.  验证测试通过。

### 基本原理

这是标准的 Bug 修复流程。我们不仅要修复代码，还要确保数据模型与数据库 Schema 的对齐。

### 标签

#intent/fix #flow/ready #priority/high #comp/engine #concept/state #scope/core #ai/refine #task/domain/storage #task/object/stitcher-index #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 更新 `ReferenceRecord` 定义

我们在 `types.py` 中为 `ReferenceRecord` 添加 `id` 字段。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/types.py
~~~~~
~~~~~python
@dataclass
class ReferenceRecord:
    target_id: str
    kind: str
    location_start: int
    location_end: int
    source_file_id: Optional[int] = None  # Optional when inserting
~~~~~
~~~~~python
@dataclass
class ReferenceRecord:
    target_id: str
    kind: str
    location_start: int
    location_end: int
    source_file_id: Optional[int] = None  # Optional when inserting
    id: Optional[int] = None  # Database Row ID
~~~~~

### 下一步建议

修复此 Bug 后，数据库层的基础设施就算稳固了。接下来的逻辑步骤是构建 **任务 1.3: 增量扫描流水线**。

该流水线是 `stitcher-index` 的心脏，它将负责：
1.  **Discovery**: 快速找出所有文件。
2.  **Stat Check**: 比较 `mtime`。
3.  **Hash Check**: 比较内容哈希。

我建议创建一个新的模块 `packages/stitcher-index/src/stitcher/index/scanner.py` 来承载此逻辑。如果你准备好了，我们可以开始。
