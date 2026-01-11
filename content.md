Of course. The test failure indicates that while the command is correctly identified as failing, the error message propagated to the user is too generic. The original exception detail (`Simulated parser crash`) is lost and replaced with "Failed to index 1 file(s)".

This is a classic error propagation problem. The `FileIndexer` correctly catches the specific error but only signals a generic failure (by returning `False`) to its caller, `IndexRunner`, which then constructs its own generic message.

I will fix this by enriching the communication channel (`stats` dictionary) between `FileIndexer` and `IndexRunner` to include the specific error messages.

## [WIP] fix: Propagate specific parsing errors to the user

### 錯誤分析

测试失败，因为 `IndexRunner` 报告了一个通用的“索引失败”消息，而不是由模拟解析器生成的具体错误（`Simulated parser crash`）。

根本原因在于：
1.  `FileIndexer._process_file_content` 捕获了具体的 `Exception`, 记录了详细日志，但只向上返回一个布尔值 `False`。
2.  `FileIndexer.index_files` 看到 `False` 后，只增加了 `stats["errors"]` 的计数，丢失了原始异常对象。
3.  `IndexRunner.run_build` 只知道有 `N` 个文件失败，无法访问具体的失败原因，因此只能生成一个通用错误消息。

### 用户需求

当索引构建过程中文件解析失败时，`stitcher check` 命令应向用户报告一个包含具体失败原因的、有意义的错误消息，而不仅仅是一个通用的“检查日志”提示。

### 评论

为了解决这个问题，我将修改 `FileIndexer`，使其在捕获到解析异常时，不仅仅是增加一个错误计数，而是将具体的异常信息也记录在 `stats` 字典中。然后，`IndexRunner` 将利用这些详细信息来生成一个对用户更有帮助的错误报告。

### 目标

1.  修改 `FileIndexer._process_file_content`，移除其内部的异常捕获。让异常自然地冒泡到调用者。
2.  修改 `FileIndexer.index_files`，在循环中捕获来自 `_process_file_content` 的异常。
3.  在 `stats` 字典中添加一个新的键 `error_details` (一个列表)，用于存储失败的文件路径和具体的错误信息。
4.  修改 `IndexRunner.run_build`，当检测到错误时，从 `stats["error_details"]` 中提取第一条错误信息并报告给用户。

### 基本原理

通过让异常冒泡到 `index_files` 的循环中，我们可以在正确的作用域（既能访问异常对象，又能访问 `stats` 字典）捕获错误。这允许我们在不中断整个索引过程的前提下，收集所有详细的失败信息。然后，这些信息被传递给 `IndexRunner`，它作为“报告者”，可以选择性地向用户展示最重要的错误，从而在鲁棒性和用户体验之间取得平衡。

### 标签

#intent/fix #flow/ready #priority/high
#comp/engine #comp/tests #scope/core
#ai/brainstorm
#task/domain/testing #task-object/zero-io-check #task/action/bug-fix #task/state/continue

---

### Script

#### Acts 1: 让 `FileIndexer` 捕获并记录详细错误

我将重构 `FileIndexer`，使其能够捕获并存储详细的错误信息。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
    def index_files(self, discovered_paths: Set[str]) -> Dict[str, int]:
        stats = {"added": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": 0}

        # Load DB state
        known_files: Dict[str, FileRecord] = {
            r.path: r for r in self.store.get_all_files_metadata()
        }
~~~~~
~~~~~python.new
    def index_files(self, discovered_paths: Set[str]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
        }

        # Load DB state
        known_files: Dict[str, FileRecord] = {
            r.path: r for r in self.store.get_all_files_metadata()
        }
~~~~~

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
            if is_new_content:
                stats["updated" if record else "added"] += 1

            if not self._process_file_content(file_id, abs_path, content_bytes):
                stats["errors"] += 1
~~~~~
~~~~~python.new
            if is_new_content:
                stats["updated" if record else "added"] += 1

            try:
                self._process_file_content(file_id, abs_path, content_bytes)
            except Exception as e:
                stats["errors"] += 1
                stats["error_details"].append((str(abs_path), str(e)))
~~~~~

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
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
~~~~~python.new
    def _process_file_content(
        self, file_id: int, abs_path: Path, content_bytes: bytes
    ) -> None:
        try:
            text_content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            self.store.update_analysis(file_id, [], [])
            return  # Not a parser error, just binary file

        ext = abs_path.suffix
        adapter = self.adapters.get(ext)
        if not adapter:
            self.store.update_analysis(file_id, [], [])
            return

        # Let exceptions bubble up to be caught by the caller
        symbols, references = adapter.parse(abs_path, text_content)
        self.store.update_analysis(file_id, symbols, references)
~~~~~

#### Acts 2: 让 `IndexRunner` 报告详细错误

现在，我将更新 `IndexRunner`，使其能够报告更具体的错误信息。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/index.py
~~~~~
~~~~~python.old
        if stats.get("errors", 0) > 0:
            bus.error(L.error.generic, error=f"Failed to index {stats['errors']} file(s). Check logs for details.")
            return False

        return True
~~~~~
~~~~~python.new
        if stats.get("errors", 0) > 0:
            # Report the first detailed error to give the user immediate context
            if stats["error_details"]:
                path, err = stats["error_details"][0]
                bus.error(L.error.generic, error=f"Failed to parse {path}: {err}")
            else:
                bus.error(L.error.generic, error=f"Failed to index {stats['errors']} file(s). Check logs for details.")
            return False

        return True
~~~~~

### 下一步建议

这次的修改直接解决了错误信息丢失的问题。`FileIndexer` 现在会将详细的异常信息传递给 `IndexRunner`，后者会将其报告给用户。测试中的断言现在应该可以找到具体的错误字符串了。

请重新运行测试套件以确认修复。
