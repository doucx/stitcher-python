You are absolutely right. The test failed, but the failure mode (`got None`) provides a crucial insight that my previous fix did not account for. My apologies. The `None` value indicates that the `baseline_yaml_content_hash` field was never written to the lock file for that symbol, which means the logic flow is more broken than a simple hash mismatch.

Your analysis is correct. The root cause is the unconditional call to `save_docs_for_module` and the subsequent logic that doesn't correctly prioritize the pre-existing Sidecar file as the source of truth for the lock file's baseline.

Let's formulate a more robust fix based on a clearer principle:
1.  **Read First**: Always check for an existing Sidecar file first.
2.  **Prioritize Sidecar**: If it exists and contains content, its IR is the **only** source of truth for calculating the lock file's `yaml_hash`.
3.  **Fallback to Source**: Only if the Sidecar is missing or empty should we fall back to extracting docs from the source code.
4.  **Write Last**: The action of writing a new Sidecar file should only happen during the fallback step.

I will now generate a new, corrected plan that implements this robust logic.

## [WIP] fix: Implement robust baseline logic in Init and enhance index stats

### 错误分析
The previous `init` implementation had a fatal flaw: it did not correctly prioritize an existing `.stitcher.yaml` file as the source of truth for the lock file's baseline hash. It would either ignore the sidecar's content or, in some flows, not generate a hash at all, leading to the `None` value seen in the test failure. This violates the principle of idempotency and data preservation.

The indexer's statistics were also opaque, failing to provide visibility into how many sidecar files were being processed, which is crucial for user confidence and debugging.

### 用户需求
1.  `stitcher init` must be幂等, respecting and preserving existing `.stitcher.yaml` files as the authoritative baseline for the lock file.
2.  The `stitcher index build` command must report the number of sidecar files it processes.

### 评论
This fix is critical for ensuring Stitcher's behavior is predictable and non-destructive. A tool designed to manage baselines cannot be the agent that corrupts them. The corrected logic establishes a clear order of precedence (Sidecar > Source Code) that aligns with user expectations.

### 目标
1.  **Refactor `InitRunner`**: Implement a "read-before-write" strategy. First, attempt to load the Sidecar. If it exists, use its content for the lock file. If not, extract from source, create the Sidecar, and then use that content for the lock file.
2.  **Enhance `FileIndexer`**: Modify the indexer to count processed `.stitcher.yaml` files.
3.  **Update `IndexRunner` and I18N**: Propagate the new sidecar count to the user-facing output message.

### 基本原理
The `InitRunner` refactoring involves separating the logic for reading existing docs from the logic for creating them. By loading both potential IR sources (from disk and from the AST) and then using a conditional to decide which one is authoritative (`ir_from_sidecar` if it exists, otherwise `ir_from_source`), we guarantee the correct baseline is used. The indexer fix remains a straightforward addition of a counter and updating the reporting chain.

### 标签
#intent/fix #flow/ready #priority/critical #comp/application #comp/index #concept/state #scope/core #ai/delegate #task/domain/testing #task/object/init-idempotency #task/action/implementation #task/state/continue

---

### Script

#### Acts 1: Implement robust baseline logic in `InitRunner`

This is the core fix. We will replace the flawed logic in `init.py` with the new, robust strategy.

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/init.py
~~~~~
~~~~~python.old
                output_path = self.doc_manager.save_docs_for_module(module)

                # Compute logical/relative paths for SURI generation
                module_abs_path = self.root_path / module.file_path
                module_ws_rel = self.workspace.to_workspace_relative(module_abs_path)

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
                # 1. Load from both potential sources to determine the source of truth.
                ir_from_sidecar = self.doc_manager.load_docs_for_module(module)
                ir_from_source = self.doc_manager.flatten_module_docs(module)

                ir_map = {}
                output_path = None

                if ir_from_sidecar:
                    # 2. Sidecar exists and has content. It is the definitive source of truth for the lock file.
                    ir_map = ir_from_sidecar
                else:
                    # 3. Sidecar does not exist or is empty. Use source docs as the source of truth.
                    ir_map = ir_from_source
                    # And if there are docs to save, create the sidecar file now.
                    if ir_map:
                        output_path = self.doc_manager.save_docs_for_module(module)

                # Compute logical/relative paths for SURI generation
                module_abs_path = self.root_path / module.file_path
                module_ws_rel = self.workspace.to_workspace_relative(module_abs_path)

                computed_fingerprints = self._compute_fingerprints(module)
                # Compute hashes from the final, authoritative ir_map.
                yaml_hashes = {
                    fqn: self.doc_manager.compute_ir_hash(ir)
                    for fqn, ir in ir_map.items()
                }
~~~~~

#### Acts 2: Enhance `FileIndexer` statistics

Now we apply the same patches as before to the indexer to add sidecar counting.

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

#### Acts 3: Update `IndexRunner` and I18N assets

Finally, propagate the new statistic to the user interface.

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
The patches have been applied. Please run the test suite again.

`pytest packages/stitcher-application/tests/integration/test_init_sidecar_idempotency.py`

Both tests should now pass, confirming that `init` preserves existing baselines and that `index build` provides transparent statistics. Once confirmed, we can remove the temporary test file.
