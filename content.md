## [WIP] fix: 修复重构引擎漏掉符号定义点的问题

### 用户需求
当执行符号重命名时，不仅要更新所有的引用点（usages），还必须更新符号本身的定义行（definition），以避免产生 `ImportError`。

### 评论
这是重构引擎的基础性缺陷。解决它需要打通 `IndexStore` 到 `GlobalBatchRenamer` 的“定义点”查询路径。

### 目标
1.  在 `IndexStore` 中增加根据 FQN 查找符号定义位置的方法。
2.  修改 `GlobalBatchRenamer`，使其在分析阶段同时收集“引用点”和“定义点”。
3.  确保 `UsageScanVisitor` 能够准确捕获定义点的行列号。

### 标签
#intent/fix #flow/ready #priority/critical #comp/engine #comp/index #concept/history #scope/core #ai/instruct #task/domain/refactor #task/object/definition-renaming #task/action/fix #task/state/begin

---

### Script

#### Acts 1: 升级 `IndexStore` 以支持通过 FQN 查找符号

我们需要在 `IndexStore` 中增加一个方法，用于从 `symbols` 表中检索特定 FQN 的位置信息。

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

    def find_symbol_location(self, fqn: str) -> Optional[Tuple[SymbolRecord, str]]:
        """
        Finds the definition site of a specific FQN.
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
                (fqn,),
            ).fetchone()
            if row:
                data = dict(row)
                file_path = data.pop("file_path")
                return SymbolRecord(**data), file_path
        return None
~~~~~

#### Acts 2: 升级 `SemanticGraph` 接口

`SemanticGraph` 应该能够返回定义点的位置。

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

    def find_definition(self, target_fqn: str) -> Optional[UsageLocation]:
        """Query the Index DB for the definition site of the given FQN."""
        result = self.index_store.find_symbol_location(target_fqn)
        if not result:
            return None

        sym, file_path_str = result
        return UsageLocation(
            file_path=self.root_path / file_path_str,
            lineno=sym.lineno,
            col_offset=sym.col_offset,
            end_lineno=sym.end_lineno,
            end_col_offset=sym.end_col_offset,
            ref_type=ReferenceType.SYMBOL,
            target_node_fqn=target_fqn,
        )
~~~~~

#### Acts 3: 修改 `GlobalBatchRenamer` 以包含定义点

这是修复核心逻辑的关键步骤：在收集 usages 时，顺便把定义点也加进去。

~~~~~act
patch_file
packages/stitcher-refactor/src/stitcher/refactor/engine/renamer.py
~~~~~
~~~~~python.old
    def analyze(self) -> List[WriteFileOp]:
        ops: List[WriteFileOp] = []
        usages_by_file: Dict[Path, List[UsageLocation]] = defaultdict(list)

        # 1. Collect all usages for all renames and group by file
        for old_fqn in self.rename_map.keys():
            usages = self.ctx.graph.find_usages(old_fqn)
            for usage in usages:
                usages_by_file[usage.file_path].append(usage)

        # 2. For each affected file, apply a single transformation that handles ALL renames
~~~~~
~~~~~python.new
    def analyze(self) -> List[WriteFileOp]:
        ops: List[WriteFileOp] = []
        usages_by_file: Dict[Path, List[UsageLocation]] = defaultdict(list)

        # 1. Collect all usages AND definitions for all renames and group by file
        for old_fqn in self.rename_map.keys():
            # Add Definition Site
            definition = self.ctx.graph.find_definition(old_fqn)
            if definition:
                usages_by_file[definition.file_path].append(definition)

            # Add Usage Sites (References)
            usages = self.ctx.graph.find_usages(old_fqn)
            for usage in usages:
                usages_by_file[usage.file_path].append(usage)

        # 2. For each affected file, apply a single transformation that handles ALL renames
~~~~~

### 下一步建议
我们已经打通了从数据库检索定义点并将其送入 CST 转换器的路径。由于 `UsageScanVisitor` 在扫描阶段已经将 `ClassDef.name` 和 `FunctionDef.name` 标记为了符号位置，现有的 `SymbolRenamerTransformer` 应该能够通过位置匹配自动完成重命名。

我建议立即运行测试，观察那 4 个失败的集成测试是否已经转绿。如果仍有失败，我们需要检查 `UsageScanVisitor` 是否漏掉了一些特定的定义场景。
