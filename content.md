好的，测试已经成功地暴露了问题。现在我将生成一个计划来修复它们。

**错误分析**:

1.  **`test_init_respects_existing_sidecar_baseline` 失败**: 测试断言失败，`stored_yaml_hash` 为 `None`。这比预想的更严重：`InitRunner` 在发现 `.stitcher.yaml` 已存在时，不仅没有优先使用其内容，甚至完全跳过了为该符号生成 `baseline_yaml_content_hash`。原因是 `ir_map` 完全依赖于从源码 AST 提取的 `flatten_module_docs`，而 `save_docs_for_module` 会跳过已存在的文件，导致 `init` 流程中没有一个环节去读取已存在的 Sidecar 内容来更新 Lock 文件。
2.  **`test_index_stats_should_distinguish_sidecars` 失败**: 测试断言失败，因为 `L.index.run.complete` 消息的参数中不包含 `sidecars` 字段。`FileIndexer` 的统计逻辑是扁平的，没有区分普通源码文件和 Sidecar 文件，因此无法在最终的报告中体现 Sidecar 的处理情况。

**解决方案**:

1.  **`InitRunner` 基线修正**: 修改 `InitRunner`，使其在计算 `yaml_hashes` 时，优先从已存在的 `.stitcher.yaml` 文件加载 IR（通过 `doc_manager.load_docs_for_module`）。只有当 Sidecar 文件不存在时，才回退到从源码中提取 IR（通过 `doc_manager.flatten_module_docs`）。这确保了 `init` 操作会尊重并保护已有的 Sidecar 基线。
2.  **索引统计增强**:
    *   在 `FileIndexer` 中增加一个 `sidecars` 计数器，当处理（新增或更新）一个 `.stitcher.yaml` 文件时，递增此计数器。
    *   在 `IndexRunner` 中，将这个新的 `sidecars` 统计数据传递给消息总线。
    *   更新 `en` 和 `zh` 语言的 I18N 资源文件，以在 `L.index.run.complete` 消息中显示 Sidecar 计数。

## [WIP] fix: 修正 Init 基线逻辑并增强索引统计

### 用户需求
1.  `stitcher init` 必须是幂等的，且不能破坏已有的 Sidecar 资产。
2.  索引操作（`stitcher index build`）应当在输出中明确告知用户处理了多少个 Sidecar 文件。

### 评论
这是一个关键的正确性修复。`init` 作为一个“建立基线”的命令，其核心职责是稳定性和可预测性。破坏现有资产是不可接受的。同样，索引统计的透明度对于用户理解系统后台行为至关重要。

### 目标
1.  修改 `InitRunner` 以优先使用现有 Sidecar 文件内容作为基线。
2.  修改 `FileIndexer` 以便在其统计输出中区分 Sidecar 文件。
3.  修改 `IndexRunner` 以报告 Sidecar 统计信息。
4.  更新 I18N 消息模板以显示 Sidecar 数量。

### 基本原理
通过调整 `InitRunner` 中 `ir_map` 的数据来源优先级，可以轻松解决基线问题。对于统计，通过在 `FileIndexer` 的文件处理循环中增加一个基于文件名的条件判断，即可实现对 Sidecar 的分类计数。

### 标签
#intent/fix #flow/ready #priority/high #comp/application #comp/index #concept/state #scope/core #scope/ux #ai/delegate #task/domain/testing #task/object/init-idempotency #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: 修正 `InitRunner` 的基线逻辑

我们将修改 `init.py`，确保它在生成 Lock 文件时优先读取已存在的 Sidecar 文件。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/init.py
~~~~~
~~~~~python.old
                # Generate IRs from source code; this is the source of truth for init.
                ir_map = self.doc_manager.flatten_module_docs(module)

                computed_fingerprints = self._compute_fingerprints(module)
                # CRITICAL FIX: Compute hashes from the in-memory IR map, NOT from the index.
                yaml_hashes = {
                    fqn: self.doc_manager.compute_ir_hash(ir)
                    for fqn, ir in ir_map.items()
                }
~~~~~
~~~~~python.new
                # Prioritize existing sidecar file as the source of truth for the baseline.
                ir_map = self.doc_manager.load_docs_for_module(module)
                if not ir_map:
                    # If no sidecar exists, fall back to extracting from source.
                    ir_map = self.doc_manager.flatten_module_docs(module)

                computed_fingerprints = self._compute_fingerprints(module)
                # Hashes are now computed from the correct source of truth (sidecar or source)
                yaml_hashes = {
                    fqn: self.doc_manager.compute_ir_hash(ir)
                    for fqn, ir in ir_map.items()
                }
~~~~~

#### Acts 2: 增强 `FileIndexer` 的统计能力

现在，我们来修改索引器，使其能够统计 Sidecar 文件。

~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
    def index_files(self, discovered_paths: Set[str]) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "added": 0,
            "updated": 0,
            "deleted": 0,
            "skipped": 0,
            "errors": 0,
            "error_details": [],
            "modified_paths": set(),
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
            "modified_paths": set(),
            "sidecars": 0,
        }
~~~~~
~~~~~act
patch_file
packages/stitcher-index/src/stitcher/index/indexer.py
~~~~~
~~~~~python.old
            file_id, is_new_content = self.store.sync_file(
                rel_path_str, current_hash, current_mtime, current_size
            )
            if is_new_content:
                stats["updated" if record else "added"] += 1
                stats["modified_paths"].add(rel_path_str)
~~~~~
~~~~~python.new
            file_id, is_new_content = self.store.sync_file(
                rel_path_str, current_hash, current_mtime, current_size
            )
            if is_new_content:
                stats["updated" if record else "added"] += 1
                stats["modified_paths"].add(rel_path_str)
                if rel_path_str.endswith(".stitcher.yaml"):
                    stats["sidecars"] += 1
~~~~~

#### Acts 3: 更新 `IndexRunner` 以报告新统计数据

接着，让 `IndexRunner` 将 Sidecar 统计数据传递给消息总线。

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
~~~~~
~~~~~python.new
        bus.success(
            L.index.run.complete,
            added=stats["added"],
            updated=stats["updated"],
            deleted=stats["deleted"],
            skipped=stats["skipped"],
            sidecars=stats.get("sidecars", 0),
        )
~~~~~

#### Acts 4: 更新 I18N 消息模板

最后，更新语言文件以显示新的统计信息。

~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/en/index/run.json
~~~~~
~~~~~json.old
{
  "start": "🔄 Starting incremental index build...",
  "complete": "✨ Indexing complete. Added: {added}, Updated: {updated}, Deleted: {deleted}, Skipped: {skipped}"
}
~~~~~
~~~~~json.new
{
  "start": "🔄 Starting incremental index build...",
  "complete": "✨ Indexing complete. Added: {added}, Updated: {updated}, Deleted: {deleted}, Skipped: {skipped}, Sidecars: {sidecars}"
}
~~~~~
~~~~~act
patch_file
packages/stitcher-common/src/stitcher/common/assets/needle/zh/index/run.json
~~~~~
~~~~~json.old
{
  "start": "🔄 开始增量索引构建...",
  "complete": "✨ 索引构建完成。新增: {added}, 更新: {updated}, 删除: {deleted}, 跳过: {skipped}"
}
~~~~~
~~~~~json.new
{
  "start": "🔄 开始增量索引构建...",
  "complete": "✨ 索引构建完成。新增: {added}, 更新: {updated}, 删除: {deleted}, 跳过: {skipped}, Sidecar: {sidecars}"
}
~~~~~

### 下一步建议
现在所有的代码修改都已完成。我建议你再次运行我们之前创建的测试，以验证修复是否成功。

执行 `pytest packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py`，预期所有测试都将通过。
