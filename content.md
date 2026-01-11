## [WIP] fix: 修复 Zero-IO 模式下的解析错误传播机制

### 错误分析

集成测试 `test_check_fails_gracefully_on_local_import` 失败，原因是：
1.  **流程变更**：重构后的 `run_check` 使用预构建的索引（通过 `ensure_index_fresh` -> `IndexRunner` -> `FileIndexer`），不再使用 `ScannerService` 直接解析物理文件。因此，测试中 Mock 的 `app.scanner.parser` 不再被调用，无法触发模拟的异常。
2.  **错误吞没**：当前的 `FileIndexer` 在解析发生异常时，仅记录日志并清空该文件的符号数据，而不是向上传播错误或标记失败。这导致即使底层解析失败，`run_check` 依然认为操作成功，违反了“Fail Gracefully”的要求（即应该明确告知用户失败）。

### 用户需求

确保在 Zero-IO 模式下，如果源代码解析失败（例如语法错误或 Parser 崩溃），`stitcher check` 命令能够感知到错误并返回失败状态，同时向用户报告错误信息。

### 评论

为了解决这个问题，我们需要在索引构建链路中打通错误传播通道。这涉及三个层面的修改：
1.  **底层 (`FileIndexer`)**：在统计信息中记录错误数量。
2.  **中间层 (`IndexRunner`)**：检查统计信息，如果有错误，通过 `bus` 报告。
3.  **顶层 (`StitcherApp`)**：感知索引构建的失败状态，并据此决定是否中断 `check` 流程。
4.  **测试**：更新 Mock 目标以匹配新的架构。

### 目标

1.  修改 `FileIndexer.index_files`，使其在 `stats` 字典中包含 `errors` 计数。
2.  修改 `IndexRunner.run_build`，当 `stats["errors"] > 0` 时，通过 `bus` 发送错误消息。
3.  修改 `StitcherApp.ensure_index_fresh`，使其返回构建是否成功的布尔值。
4.  修改 `StitcherApp.run_check`，如果索引构建失败，则设置错误标志。
5.  更新集成测试，Mock 正确的 Parser 实例 (`app.file_indexer.adapters[".py"].parser`)。

### 基本原理

通过在 `stats` 中通过 `errors` 字段显式传递错误计数，我们可以在不抛出异常中断整个索引过程（因为我们希望尽可能多地索引其他文件）的同时，让上层调用者知道发生了部分失败。这保持了索引器的鲁棒性，同时满足了 CLI 命令对错误反馈的需求。

### 标签

#intent/fix #flow/ready #priority/high
#comp/engine #comp/tests #scope/core
#ai/instruct
#task/domain/testing #task/object/zero-io-check #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 更新 `FileIndexer` 以记录错误

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
    def index_files(self, discovered_paths: Set[str]) -> Dict[str, int]:
        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0}

        # Load DB state
        known_files: Dict[str, FileRecord] = {
~~~~~
~~~~~python.new
    def index_files(self, discovered_paths: Set[str]) -> Dict[str, int]:
        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

        # Load DB state
        known_files: Dict[str, FileRecord] = {
~~~~~
~~~~~python.old
        try:
            symbols, references = adapter.parse(abs_path, text_content)
            self.store.update_analysis(file_id, symbols, references)
        except Exception as e:
            log.error(f"Failed to parse {abs_path}: {e}")
            self.store.update_analysis(file_id, [], [])
~~~~~
~~~~~python.new
        try:
            symbols, references = adapter.parse(abs_path, text_content)
            self.store.update_analysis(file_id, symbols, references)
        except Exception as e:
            log.error(f"Failed to parse {abs_path}: {e}")
            # Raise exception to caller if needed?
            # For robustness, we log and clear data, but we must signal error.
            # We can't access stats here directly without refactoring _process_file_content to return status
            # or passing stats dict.
            # Let's re-raise a custom exception or return False?
            # Refactoring _process_file_content to return success boolean seems best.
            # But wait, I can just modify the caller to handle the exception if I re-raise.
            # Or pass a mutable stats object (not ideal).
            # Let's change _process_file_content to return bool.
            self.store.update_analysis(file_id, [], [])
            raise e
~~~~~

> **自我纠正**：`_process_file_content` 之前的实现是捕获所有异常。如果我在那里抛出异常，调用者 `index_files` 需要捕获并更新 stats。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
            if is_new_content:
                stats["updated" if record else "added"] += 1

            self._process_file_content(file_id, abs_path, content_bytes)

        # --- Linking ---
        self.linker.link()
        return stats

    def _process_file_content(self, file_id: int, abs_path: Path, content_bytes: bytes):
        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self.store.update_analysis(file_id, [], [])
            return

        ext = abs_path.suffix
        adapter = self.adapters.get(ext)
        if not adapter:
            self.store.update_analysis(file_id, [], [])
            return

        try:
            symbols, references = adapter.parse(abs_path, text_content)
            self.store.update_analysis(file_id, symbols, references)
        except Exception as e:
            log.error(f"Failed to parse {abs_path}: {e}")
            self.store.update_analysis(file_id, [], [])
~~~~~
~~~~~python.new
            if is_new_content:
                stats["updated" if record else "added"] += 1

            if not self._process_file_content(file_id, abs_path, content_bytes):
                stats["errors"] += 1

        # --- Linking ---
        self.linker.link()
        return stats

    def _process_file_content(
        self, file_id: int, abs_path: Path, content_bytes: bytes
    ) -> bool:
        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self.store.update_analysis(file_id, [], [])
            return True  # Not a parser error, just binary file

        ext = abs_path.suffix
        adapter = self.adapters.get(ext)
        if not adapter:
            self.store.update_analysis(file_id, [], [])
            return True

        try:
            symbols, references = adapter.parse(abs_path, text_content)
            self.store.update_analysis(file_id, symbols, references)
            return True
        except Exception as e:
            log.error(f"Failed to parse {abs_path}: {e}")
            self.store.update_analysis(file_id, [], [])
            return False
~~~~~

#### Acts 2: 更新 `IndexRunner` 以报告错误

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/index.py
~~~~~
~~~~~python.old
        bus.success(
            L.index.run.complete,
            added=stats["added"],
            updated=stats["updated"],
            deleted=stats["deleted"],
            skipped=stats["skipped"],
        )
        return True
~~~~~
~~~~~python.new
        bus.success(
            L.index.run.complete,
            added=stats["added"],
            updated=stats["updated"],
            deleted=stats["deleted"],
            skipped=stats["skipped"],
        )

        if stats.get("errors", 0) > 0:
            bus.error(L.error.generic, error=f"Failed to index {stats['errors']} file(s). Check logs for details.")
            return False

        return True
~~~~~

#### Acts 3: 更新 `StitcherApp` 以处理索引失败

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def ensure_index_fresh(self) -> None:
        self.index_runner.run_build(self.workspace)

    def _configure_and_scan(self, config: StitcherConfig) -> List[ModuleDef]:
~~~~~
~~~~~python.new
    def ensure_index_fresh(self) -> bool:
        return self.index_runner.run_build(self.workspace)

    def _configure_and_scan(self, config: StitcherConfig) -> List[ModuleDef]:
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python.old
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        self.ensure_index_fresh()
        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
~~~~~
~~~~~python.new
    def run_check(self, force_relink: bool = False, reconcile: bool = False) -> bool:
        if not self.ensure_index_fresh():
            self.scanner.had_errors = True
        
        configs, _ = self._load_configs()
        all_results: List[FileCheckResult] = []
~~~~~

#### Acts 4: 更新集成测试以 Mock 正确的 Parser

我们需要 Mock `app.file_indexer.adapters[".py"].parser` 而不是 `app.scanner.parser`。

~~~~~act
patch_file
packages/stitcher-application/tests/integration/test_parser_robustness.py
~~~~~
~~~~~python.old
    # SETUP: Mock the parser to simulate a crash on specific file
    # We access the parser instance directly attached to the scanner
    real_parse = app.scanner.parser.parse

    def failing_parse(source_code, file_path=""):
        if "core.py" in str(file_path):
            raise ValueError("Simulated parser crash for testing")
        return real_parse(source_code, file_path)

    monkeypatch.setattr(app.scanner.parser, "parse", failing_parse)
~~~~~
~~~~~python.new
    # SETUP: Mock the parser to simulate a crash on specific file
    # In Zero-IO mode, parsing happens in the Indexer via PythonAdapter
    # We need to find the correct parser instance to mock.
    
    python_adapter = app.file_indexer.adapters[".py"]
    # Verify we got the adapter (the key might vary if not registered as .py, but StitcherApp does register it as .py)
    assert python_adapter is not None
    
    real_parse = python_adapter.parser.parse

    def failing_parse(source_code, file_path=""):
        if "core.py" in str(file_path):
            raise ValueError("Simulated parser crash for testing")
        return real_parse(source_code, file_path)

    monkeypatch.setattr(python_adapter.parser, "parse", failing_parse)
~~~~~

### 下一步建议
运行测试，确认修复有效。
