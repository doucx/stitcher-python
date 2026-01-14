Excellent. With the test harness now correctly validating our caching strategy, we can proceed with the core architectural improvement.

I will now generate the plan to modify `DocumentManager` to prioritize reading from the `IndexStore`, effectively eliminating the I/O bottleneck during the `check` operation.

## [WIP] refactor(sidecar): Optimize DocumentManager to read from index

### 用户需求

Modify the `DocumentManager` to use the `IndexStore` as its primary data source for reading sidecar file content, instead of directly accessing and parsing YAML files from the filesystem.

### 評論

This is the pivotal step in our performance optimization. By shifting the read path from direct file I/O to the indexed database, we are not only addressing the identified bottleneck but also solidifying the "Unified Data Model" concept. The analysis engine will now be almost entirely decoupled from the filesystem for read operations, interacting with a fast, structured, and cached data source (`IndexStore`), which is a significant architectural improvement.

### 目标

1.  Fully implement the logic within `DocumentManager.load_docs_for_path` to query the `IndexStore` for symbols corresponding to a given `.stitcher.yaml` file path.
2.  Implement the helper method `_hydrate_from_symbols` to correctly deserialize the JSON content stored in the database back into `DocstringIR` objects.
3.  Ensure the method gracefully falls back to the legacy file-reading mechanism if the `IndexStore` is unavailable or does not contain the requested information.

### 基本原理

The `FileIndexer` now treats `.stitcher.yaml` files as source code, parsing them and storing their contents as `doc_fragment` symbols in the SQLite database. The `docstring_content` for these symbols is a JSON serialization of the view data.

The optimized `DocumentManager` will leverage this pre-indexed data. When asked for document IRs, it will:
1.  Query the `IndexStore` using the sidecar file's path.
2.  Retrieve the relevant `SymbolRecord` objects.
3.  For each symbol, it will take the `docstring_content` (JSON string), parse it into a Python dictionary, and then use the configured `DocstringSerializer` to convert this "view data" back into a rich `DocstringIR` object.

This process replaces slow, repeated `ruamel.yaml` parsing with a fast database query and a much faster `json.loads` operation, fully capitalizing on the增量索引 mechanism.

### 标签

#intent/refine #flow/ready #priority/high #comp/lang-sidecar #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/cache-validation #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: Implement index-first data loading in DocumentManager

We will replace the existing `DocumentManager` implementation with one that prioritizes reading from the index.

~~~~~act
patch_file
packages/stitcher-lang-sidecar/src/stitcher/lang/sidecar/manager.py
~~~~~
~~~~~python.old
    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]:
        if not file_path:
            return {}
        module_path = self.root_path / file_path
        doc_path = self.resolver.get_doc_path(module_path)

        # 1. Try loading from Index (Unified Data Model)
        if self.index_store:
            try:
                rel_doc_path = doc_path.relative_to(self.root_path).as_posix()
                symbols = self.index_store.get_symbols_by_file_path(rel_doc_path)
                # If we have symbols (even if empty list, meaning file tracked but empty), we trust index.
                # However, if the file is not in index (get_symbols returns []), it might be untracked or new.
                # For robustness, if symbols is empty list, we double check if file exists on disk?
                # Actually, StitcherApp ensures index freshness.
                if symbols:
                    return self._hydrate_from_symbols(symbols)
            except ValueError:
                # Path issue (e.g. peripheral), fallback to IO
                pass

        # 2. Fallback to File IO (Legacy/No-Index mode)
        return self._sidecar_adapter.load_doc_irs(doc_path, self.serializer)

    def _hydrate_from_symbols(
        self, symbols: List["SymbolRecord"]
    ) -> Dict[str, DocstringIR]:
        docs = {}
        for sym in symbols:
            # We only care about doc fragments here
            if sym.kind != "doc_fragment" or not sym.docstring_content:
                continue

            try:
                # The content in DB is JSON-serialized View Data (from SidecarIndexerAdapter)
                view_data = json.loads(sym.docstring_content)
                # Convert View Data -> IR using the current configured strategy
                ir = self.serializer.from_view_data(view_data)
                docs[sym.name] = ir
            except Exception:
                # If data is corrupt, skip
                continue
        return docs
~~~~~
~~~~~python.new
    def load_docs_for_path(self, file_path: str) -> Dict[str, DocstringIR]:
        if not file_path:
            return {}
        module_path = self.root_path / file_path
        doc_path = self.resolver.get_doc_path(module_path)

        # 1. Try loading from Index (Unified Data Model)
        if self.index_store:
            try:
                rel_doc_path = doc_path.relative_to(self.root_path).as_posix()
                symbols = self.index_store.get_symbols_by_file_path(rel_doc_path)
                # If the index returns a list (even empty), it means the file is tracked.
                # An empty list signifies a tracked but empty .stitcher.yaml file.
                # We can trust the index completely because `ensure_index_fresh` runs before `check`.
                if symbols is not None:
                    return self._hydrate_from_symbols(symbols)
            except ValueError:
                # This can happen if the path is outside the project root (e.g., a peripheral).
                # In this case, we fall back to direct I/O.
                pass

        # 2. Fallback to File IO (for peripherals or non-indexed scenarios)
        return self._sidecar_adapter.load_doc_irs(doc_path, self.serializer)

    def _hydrate_from_symbols(
        self, symbols: List["SymbolRecord"]
    ) -> Dict[str, DocstringIR]:
        docs = {}
        for sym in symbols:
            # We only care about doc fragments from sidecar files.
            if sym.kind != "doc_fragment" or not sym.docstring_content:
                continue

            try:
                # The content in DB is a JSON string representing the "View Data".
                view_data = json.loads(sym.docstring_content)
                # Convert this View Data -> IR using the currently configured strategy.
                ir = self.serializer.from_view_data(view_data)
                # The symbol's name is the FQN fragment (e.g., "MyClass.my_method").
                docs[sym.name] = ir
            except (json.JSONDecodeError, TypeError):
                # If data is corrupt or not in the expected format, skip this entry.
                continue
        return docs
~~~~~

### 下一步建议

我们已经完成了核心的性能优化。现在最重要的一步是运行完整的测试套件，特别是我们新加的 `test_check_cache.py`，来确认我们的修改是正确且有效的。

同时，再次运行性能剖析脚本将为我们提供量化的数据，以证明这次架构重构带来的显著性能提升。

如果所有测试都通过，我们就可以认为这个任务已经完成，并准备提交这些变更。
