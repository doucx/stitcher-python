## [WIP] feat: Implement identity-based reference query in Index and SemanticGraph

### 用户需求

为了实现基于身份的重构（即通过 SURI ID 而不仅仅是 FQN 查找引用），我们需要升级底层的查询基础设施。
1.  **IndexStore**: `find_references` 需要支持同时查询 `target_id` (SURI) 和 `target_fqn`。
2.  **ReferenceType**: 需要扩展枚举以支持 Sidecar 特有的引用类型 (`SIDECAR_ID`, `SIDECAR_NAME`)。
3.  **SemanticGraph**: `find_usages` 需要先解析符号的 ID，然后执行联合查询，并将结果映射为统一的 `UsageLocation` 对象。

### 评论

这是“重构 2.0”的核心驱动。通过在底层支持 ID 查询，我们不再需要在应用层（Refactor Planner）去猜测 Sidecar 文件的位置和内容。我们只需询问索引：“谁引用了这个符号（无论是通过名字还是通过 ID）？”，索引就会返回所有 Python 文件和 Sidecar 文件的确切位置。这将极大地简化重构逻辑并提高准确性。

### 目标

1.  修改 `stitcher-lang-python/src/stitcher/lang/python/analysis/models.py`，扩展 `ReferenceType` 枚举。
2.  修改 `stitcher-index/src/stitcher/index/store.py`，更新 `find_references` 方法以支持 `target_id` 参数和 OR 查询逻辑。
3.  修改 `stitcher-analysis/src/stitcher/analysis/semantic/graph.py`，更新 `find_usages` 以利用新的查询能力。

### 基本原理

*   **IndexStore**: SQL 查询将变为 `WHERE target_fqn = ? OR target_id = ?`。这将捕获所有已链接的强引用（ID）和未链接的弱引用（FQN）。
*   **SemanticGraph**: 作为查询门面，它负责先将用户提供的 FQN 解析为 ID（如果存在），然后向 Store 发起全量查询。它还需要处理不同类型的 `kind` 映射，确保上层 Refactor 引擎能区分这是代码引用还是 Sidecar 引用。

### 标签

#intent/build #flow/ready #priority/critical #comp/index #comp/analysis #concept/search #scope/core #ai/instruct #task/domain/storage #task/object/index-query #task/action/upgrade #task/state/continue

---

### Script

#### Acts 1: 扩展 ReferenceType

我们需要在 Python 模型中添加 Sidecar 引用类型。虽然放在 `stitcher-lang-python` 略显不妥，但鉴于它是目前定义 `UsageLocation` 的地方，且 Sidecar 是 Python 生态的一部分，这是最务实的做法。

~~~~~act
patch_file
packages/stitcher-lang-python/src/stitcher/lang/python/analysis/models.py
~~~~~
~~~~~python.old
class ReferenceType(Enum):
    SYMBOL = "symbol"
    IMPORT_PATH = "import_path"
~~~~~
~~~~~python.new
class ReferenceType(Enum):
    SYMBOL = "symbol"
    IMPORT_PATH = "import_path"
    SIDECAR_ID = "json_suri"      # Reference in Signature (.json) via SURI
    SIDECAR_NAME = "yaml_fqn"     # Reference in Doc (.yaml) via FQN
~~~~~

#### Acts 2: 升级 IndexStore 查询逻辑

修改 `find_references` 以支持 ID 查询。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
    def find_references(self, target_fqn: str) -> List[Tuple[ReferenceRecord, str]]:
        with self.db.get_connection() as conn:
            # Join references with files to get the path
            rows = conn.execute(
                """
                SELECT r.*, f.path as file_path
                FROM "references" r
                JOIN files f ON r.source_file_id = f.id
                WHERE r.target_fqn = ?
                """,
                (target_fqn,),
            ).fetchall()
            return [
                (
                    ReferenceRecord(
                        **{k: v for k, v in dict(row).items() if k != "file_path"}
                    ),
                    row["file_path"],
                )
                for row in rows
            ]
~~~~~
~~~~~python.new
    def find_references(
        self, target_fqn: str, target_id: Optional[str] = None
    ) -> List[Tuple[ReferenceRecord, str]]:
        with self.db.get_connection() as conn:
            # Join references with files to get the path
            # We search for matches by FQN (weak/unlinked refs) OR by ID (strong/linked refs)
            query = """
                SELECT r.*, f.path as file_path
                FROM "references" r
                JOIN files f ON r.source_file_id = f.id
                WHERE r.target_fqn = ?
            """
            params = [target_fqn]

            if target_id:
                query += " OR r.target_id = ?"
                params.append(target_id)

            rows = conn.execute(query, tuple(params)).fetchall()
            return [
                (
                    ReferenceRecord(
                        **{k: v for k, v in dict(row).items() if k != "file_path"}
                    ),
                    row["file_path"],
                )
                for row in rows
            ]
~~~~~

同时更新 Protocol 定义以匹配实现。

~~~~~act
patch_file
packages/stitcher-spec/src/stitcher/spec/storage.py
~~~~~
~~~~~python.old
    def find_symbol_by_fqn(
        self, target_fqn: str
    ) -> Optional[Tuple[SymbolRecord, str]]: ...

    def find_references(self, target_fqn: str) -> List[Tuple[ReferenceRecord, str]]: ...

    def get_all_files_metadata(self) -> List[FileRecord]: ...
~~~~~
~~~~~python.new
    def find_symbol_by_fqn(
        self, target_fqn: str
    ) -> Optional[Tuple[SymbolRecord, str]]: ...

    def find_references(
        self, target_fqn: str, target_id: Optional[str] = None
    ) -> List[Tuple[ReferenceRecord, str]]: ...

    def get_all_files_metadata(self) -> List[FileRecord]: ...
~~~~~

#### Acts 3: 升级 SemanticGraph 查询逻辑

更新 `find_usages` 以解析 ID 并处理新的引用类型。

~~~~~act
patch_file
packages/stitcher-analysis/src/stitcher/analysis/semantic/graph.py
~~~~~
~~~~~python.old
    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        usages = []

        # 1. Find all references (usages)
        db_refs = self.index_store.find_references(target_fqn)
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                ref_type = ReferenceType.SYMBOL  # Fallback

            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    end_lineno=ref.end_lineno,
                    end_col_offset=ref.end_col_offset,
                    ref_type=ref_type,
                    target_node_fqn=ref.target_fqn,
                )
            )

        # 2. Find the definition itself and treat it as a usage site
~~~~~
~~~~~python.new
    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        usages = []

        # 0. Resolve Symbol ID (SURI) from FQN if possible
        target_id = None
        symbol_res = self.index_store.find_symbol_by_fqn(target_fqn)
        if symbol_res:
            symbol_record, _ = symbol_res
            target_id = symbol_record.id

        # 1. Find all references (usages) by FQN or ID
        db_refs = self.index_store.find_references(target_fqn, target_id=target_id)
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                # If kind is unknown to ReferenceType, fallback based on context or keep generic
                # For now, fallback to SYMBOL if not recognized, but ideally we should match kinds.
                # Sidecar kinds (json_suri, yaml_fqn) are added to ReferenceType enum.
                ref_type = ReferenceType.SYMBOL

            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=ref.lineno,
                    col_offset=ref.col_offset,
                    end_lineno=ref.end_lineno,
                    end_col_offset=ref.end_col_offset,
                    ref_type=ref_type,
                    target_node_fqn=ref.target_fqn or target_fqn, # Fallback if target_fqn is NULL (SURI refs)
                )
            )

        # 2. Find the definition itself and treat it as a usage site
~~~~~

### 下一步建议

基础设施已经升级完毕。现在，Refactor 引擎可以通过 `find_usages` 找到所有类型的引用（代码、Doc、Signature）。

下一步是**重构 `GlobalBatchRenamer` 和 `Planner`**。我们需要：
1.  在 `GlobalBatchRenamer` 中移除对 `SidecarUpdateMixin` 的依赖。
2.  实现一个分发逻辑：
    *   `ReferenceType.SYMBOL` / `IMPORT_PATH` -> 走 Python CST Transformer。
    *   `ReferenceType.SIDECAR_ID` -> 走 JSON Updater (更新 Key SURI 中的 fragment)。
    *   `ReferenceType.SIDECAR_NAME` -> 走 YAML Updater (更新 Key FQN)。

这将彻底完成重构逻辑的现代化。我建议下一个计划专注于实现这个分发和处理逻辑。
