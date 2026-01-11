[简要回答]
我们将通过“批量数据检索”和“路径解析缓存”来消除 `analyze_paths` 阶段的 N+1 查询问题。这将直接解决掉约 32ms 的数据库交互开销，并为后续跳过非必要的磁盘 I/O 铺平道路。

## [WIP] refactor(perf): 实施批量符号检索与路径解析优化

### 错误分析
目前的 `analyze_paths` 循环存在典型的 **N+1 性能陷阱**：
1.  **数据库陷阱**：对于 440 个文件，`CheckRunner` 会创建 440 个 `IndexCheckSubjectAdapter` 实例，每个实例都会触发至少一次独立的 SQLite `SELECT` 查询来获取符号（耗时 32ms）。
2.  **路径解析冗余**：`AssetPathResolver` 和 `SURIGenerator` 在循环内高频执行 `PosixPath` 的字符串转换和后缀处理。虽然单次耗时极短，但在高频循环中累积了约 10-15ms 的开销。

### 用户需求
优化 `stitcher check` 的分析阶段，减少数据库访问频率和冗余的路径计算。

### 评论
批量处理是提升系统吞吐量的核心手段。将 440 次零散查询合并为一次大批量查询，不仅减少了 Python 与 SQLite 之间的边界切换，还允许数据库引擎更好地利用索引缓存。

### 目标
1.  **扩展 `IndexStore`**：增加 `get_all_symbols_grouped_by_file` 方法，支持一次性获取多个文件的所有符号定义。
2.  **重构 `CheckRunner`**：在进入分析循环前，预先抓取所有目标文件的符号数据，并将其以映射表的形式注入 Adapter。
3.  **优化路径解析**：在 `AssetPathResolver` 中引入简单的 LruCache 或对象重用，减少字符串操作。

### 基本原理
1.  **数据预载 (Eager Loading)**：在批处理场景下，提前加载所需的所有数据（Eager Loading）优于按需加载（Lazy Loading）。
2.  **内存换时间**：通过在内存中构建一个 `Dict[file_path, List[SymbolRecord]]` 的查找表，我们可以将 Adapter 内部的数据库查询降级为简单的内存寻址。

### 标签
#intent/refine #flow/ready #priority/high #comp/index #comp/application #scope/core #task/domain/performance #task/object/n-plus-one-queries #task/action/optimize #task/state/continue

---

### Script

#### Acts 1: 在 `IndexStore` 中实现批量查询

我们在 `store.py` 中添加一个新的高效查询方法。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/store.py
~~~~~
~~~~~python.old
    def get_symbols_by_file_path(self, file_path: str) -> List[SymbolRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE f.path = ?
                """,
                (file_path,),
            ).fetchall()
            return [SymbolRecord(**dict(row)) for row in rows]
~~~~~
~~~~~python.new
    def get_symbols_by_file_path(self, file_path: str) -> List[SymbolRecord]:
        with self.db.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT s.*
                FROM symbols s
                JOIN files f ON s.file_id = f.id
                WHERE f.path = ?
                """,
                (file_path,),
            ).fetchall()
            return [SymbolRecord(**dict(row)) for row in rows]

    def get_symbols_for_files(self, file_paths: List[str]) -> Dict[str, List[SymbolRecord]]:
        if not file_paths:
            return {}

        results = defaultdict(list)
        # SQLite handles large IN clauses well, but we use a join for robustness
        # We use a temporary table or parameter binding if the list is extremely large
        # For ~440 files, simple parameter binding is sufficient.
        placeholders = ",".join(["?"] * len(file_paths))
        query = f"""
            SELECT s.*, f.path as file_path
            FROM symbols s
            JOIN files f ON s.file_id = f.id
            WHERE f.path IN ({placeholders})
        """

        with self.db.get_connection() as conn:
            rows = conn.execute(query, file_paths).fetchall()
            for row in rows:
                data = dict(row)
                path = data.pop("file_path")
                results[path].append(SymbolRecord(**data))
        return results
~~~~~

#### Acts 2: 改造 `IndexCheckSubjectAdapter` 支持数据注入

我们修改构造函数，使其可以接收预加载的符号数据。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
class IndexCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        file_path: str,
        index_store: IndexStore,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._sig_manager = sig_manager
~~~~~
~~~~~python.new
class IndexCheckSubjectAdapter(CheckSubject):
    def __init__(
        self,
        file_path: str,
        index_store: IndexStore,
        doc_manager: DocumentManager,
        sig_manager: SignatureManager,
        preloaded_symbols: Optional[List[SymbolRecord]] = None,
    ):
        self._file_path = file_path
        self._index_store = index_store
        self._doc_manager = doc_manager
        self._sig_manager = sig_manager
        self._preloaded_symbols = preloaded_symbols
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/subject.py
~~~~~
~~~~~python.old
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load data from all sources
        symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)
        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)
~~~~~
~~~~~python.new
    def get_all_symbol_states(self) -> Dict[str, SymbolState]:
        # 1. Load data from all sources
        if self._preloaded_symbols is not None:
            symbols_from_db = self._preloaded_symbols
        else:
            symbols_from_db = self._index_store.get_symbols_by_file_path(self.file_path)

        yaml_docs = self._doc_manager.load_docs_for_path(self.file_path)
~~~~~

#### Acts 3: 在 `CheckRunner` 中实施预加载逻辑

我们在分析循环开始前，批量抓取所有符号。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/check/runner.py
~~~~~
~~~~~python.old
    def analyze_paths(
        self, file_paths: List[str]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        all_results: List[FileCheckResult] = []
        all_conflicts: List[InteractionContext] = []

        for file_path in file_paths:
            subject = IndexCheckSubjectAdapter(
                file_path, self.index_store, self.doc_manager, self.sig_manager
            )
            result, conflicts = self.analyzer.analyze_subject(subject)
~~~~~
~~~~~python.new
    def analyze_paths(
        self, file_paths: List[str]
    ) -> Tuple[List[FileCheckResult], List[InteractionContext]]:
        all_results: List[FileCheckResult] = []
        all_conflicts: List[InteractionContext] = []

        # Optimization: Pre-load all symbols for all files in a single batch query
        all_symbols_map = self.index_store.get_symbols_for_files(file_paths)

        for file_path in file_paths:
            preloaded = all_symbols_map.get(file_path, [])
            subject = IndexCheckSubjectAdapter(
                file_path,
                self.index_store,
                self.doc_manager,
                self.sig_manager,
                preloaded_symbols=preloaded,
            )
            result, conflicts = self.analyzer.analyze_subject(subject)
~~~~~

### 下一步建议
通过批量符号检索，我们已经解决了 `analyze_paths` 中约 20% 的瓶颈（SQLite N+1 问题）。
现在的最大瓶颈是：**`load_docs_for_path` (60ms) 和 `load_composite_hashes` (24ms)**。
- 它们仍在盲目地读取每一个 `.stitcher.yaml` 和 `.json` 文件。
- **下一步目标**：我将为 `IndexCheckSubjectAdapter` 引入一种“读取避障”机制。我们会检查 `.py` 文件的索引状态以及磁盘上对应资产文件的 `mtime`。如果三方（py, yaml, sig）自上次成功检查后均未发生变化，我们将尝试完全跳过这个文件的分析步骤。
