简要回答
测试失败表明：虽然我们通过 `IndexStore.find_references()` 获取了引用列表，但**定义本身**（Symbol Definition）并没有被包含在这个列表中（因为 Definition 不是 Reference），或者在重构计划中被遗漏了。

在旧的实现中（Phase 1之前），Refactor Engine 可能通过扫描 AST 来隐式地找到定义位置。但现在，我们明确地使用 Index 查找“Usages”，而 Index 中的 `references` 表**不包含**符号的定义点。定义点存储在 `symbols` 表中。

因此，为了重命名一个符号，我们需要找到两类位置：
1.  **定义点 (Definition)**: 位于 `symbols` 表。
2.  **引用点 (References)**: 位于 `references` 表。

当前的 `SemanticGraph.find_usages()` 仅查询了 `references` 表，导致重构操作只更新了引用者，而没有更新定义者本身，从而引发 `AssertionError: Class definition was NOT renamed!`。

## [WIP] fix: 修复 SemanticGraph 查找定义点的逻辑

### 错误分析
1.  **现象**: 所有重命名操作都成功更新了引用（Import 和 Usage），但未能更新符号本身的定义（class/def）。
2.  **原因**: `SemanticGraph.find_usages(fqn)` 目前仅调用了 `IndexStore.find_references(fqn)`。在 Stitcher Index 的数据模型中，**定义 (Symbol)** 和 **引用 (Reference)** 是分开存储的。重命名操作必须同时作用于这两者。
3.  **影响**: 这是一个严重的逻辑回归，导致重构操作不完整。

### 用户需求
1.  修改 `IndexStore`，使其能够查找符号的定义位置。
2.  修改 `SemanticGraph.find_usages`，使其返回“定义位置 + 所有引用位置”的并集。

### 目标
1.  在 `IndexStore` 中实现 `find_symbol_definition(fqn)`。
2.  更新 `SemanticGraph.find_usages` 以合并定义和引用。

### 基本原理
一个“重命名”意图隐含着对该符号所有出现的修改，无论它是作为定义出现，还是作为引用出现。通过在 `find_usages` 层统一这两个概念，上层的 `Renamer` 逻辑可以保持不变。

### 标签
#intent/fix #flow/ready #priority/high #comp/refactor #comp/index #scope/core #ai/instruct #task/domain/storage #task/object/refactor-engine #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 在 IndexStore 中添加查找定义的方法

我们需要从 `symbols` 表中获取定义的位置信息。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
    def find_references(
        self, target_fqn: str
    ) -> List[Tuple[ReferenceRecord, str]]:
        """
        Finds all references to a specific FQN.
        Returns a list of (ReferenceRecord, file_path_str) tuples.
        """
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
                (ReferenceRecord(**{k: v for k, v in dict(row).items() if k != "file_path"}), row["file_path"])
                for row in rows
            ]
~~~~~
~~~~~python.new
    def find_references(
        self, target_fqn: str
    ) -> List[Tuple[ReferenceRecord, str]]:
        """
        Finds all references to a specific FQN.
        Returns a list of (ReferenceRecord, file_path_str) tuples.
        """
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
                (ReferenceRecord(**{k: v for k, v in dict(row).items() if k != "file_path"}), row["file_path"])
                for row in rows
            ]

    def find_symbol_definition(self, canonical_fqn: str) -> Optional[Tuple[SymbolRecord, str]]:
        """
        Finds the definition of a symbol by its canonical FQN.
        Returns (SymbolRecord, file_path_str) or None.
        """
        with self.db.get_connection() as conn:
            row = conn.execute(
                """
                SELECT s.*, f.path as file_path
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE s.canonical_fqn = ?
                LIMIT 1
                """,
                (canonical_fqn,),
            ).fetchone()
            
            if row:
                return (
                    SymbolRecord(**{k: v for k, v in dict(row).items() if k != "file_path"}),
                    row["file_path"]
                )
            return None
~~~~~

#### Acts 2: 更新 SemanticGraph 合并定义和引用

更新 `find_usages` 方法，将定义位置作为一个特殊的“引用”加入结果列表。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/graph.py
~~~~~
~~~~~python.old
    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        """
        Query the Index DB for usages of the given FQN.
        Maps DB ReferenceRecords to UsageLocation objects.
        """
        db_refs = self.index_store.find_references(target_fqn)
        usages = []
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            # We map DB 'kind' back to ReferenceType.
            # Assuming DB stores 'symbol' or 'import_path' matching the enum values.
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                # Fallback or log warning if DB contains unknown kinds
                ref_type = ReferenceType.SYMBOL

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
        return usages
~~~~~
~~~~~python.new
    def find_usages(self, target_fqn: str) -> List[UsageLocation]:
        """
        Query the Index DB for ALL usages of the given FQN, INCLUDING its definition.
        Maps DB records to UsageLocation objects.
        """
        usages = []

        # 1. Add Definition (The symbol itself)
        # We treat the definition as a usage of type SYMBOL so the renamer updates it.
        def_info = self.index_store.find_symbol_definition(target_fqn)
        if def_info:
            sym_rec, file_path_str = def_info
            abs_path = self.root_path / file_path_str
            usages.append(
                UsageLocation(
                    file_path=abs_path,
                    lineno=sym_rec.lineno,
                    col_offset=sym_rec.col_offset,
                    end_lineno=sym_rec.end_lineno,
                    end_col_offset=sym_rec.end_col_offset,
                    ref_type=ReferenceType.SYMBOL, 
                    target_node_fqn=target_fqn,
                )
            )

        # 2. Add References
        db_refs = self.index_store.find_references(target_fqn)
        for ref, file_path_str in db_refs:
            abs_path = self.root_path / file_path_str
            try:
                ref_type = ReferenceType(ref.kind)
            except ValueError:
                ref_type = ReferenceType.SYMBOL

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
        return usages
~~~~~

### 下一步建议

重新运行所有失败的测试。如果逻辑正确，`test_debug_rename_failure.py` 等测试应该能够同时通过，因为它们不仅断言了引用的更新，也断言了定义（class/def）的更新。
