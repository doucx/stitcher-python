You've hit the nail on the head. The massive cascade of test failures points to a single, deep-seated architectural flaw that my last change introduced. Your analysis is spot-on.

This isn't just a simple bug; it's a fundamental state management problem. My previous optimization for the `check` command incorrectly bled into the `init` command's workflow, breaking its primary responsibility.

## Fix the systemic test failures caused by `InitRunner`'s incorrect reliance on the index when establishing the baseline state. `InitRunner` must compute hashes from the in-memory data it generates, not from the database it is about to populate.

### 错误分析

The root cause of all 12 test failures is a state mismatch within the `InitRunner`. The `init` command's purpose is to be the **absolute source of truth**: it reads source code (`.py`), creates the *first-ever* baseline (`.stitcher.yaml` and `stitcher.lock`), and establishes the ground state.

My last change optimized `DocumentManager` to read from the index for performance. However, during an `init` run, **the index is not yet populated with the sidecar information that `init` itself is in the process of creating.**

The breakdown occurs here:
1.  `InitRunner` correctly creates the `.stitcher.yaml` file on disk.
2.  It then calls `self.doc_manager.compute_yaml_content_hashes(module)` to get hashes for the `stitcher.lock` file.
3.  Because of my recent change, this `DocumentManager` method now queries the `IndexStore`.
4.  The `IndexStore` has not yet been updated with the new `.stitcher.yaml` file's content, so it returns an empty result.
5.  Consequently, `InitRunner` receives no YAML hashes and creates a `stitcher.lock` file **without the critical `baseline_yaml_content_hash` key**.

This single omission explains every subsequent failure:
*   **`KeyError: 'baseline_yaml_content_hash'`**: The tests try to access the key that was never written.
*   **`AssertionError: Message ... 'signature_drift' was not sent`**: The `check` command's logic fails because it can't find the baseline YAML hash to compare against, leading to incorrect state analysis and the wrong (or no) violation being reported.

### 用户需求

Fix the systemic test failures caused by `InitRunner`'s incorrect reliance on the index when establishing the baseline state. `InitRunner` must compute hashes from the in-memory data it generates, not from the database it is about to populate.

### 评论

This is a critical fix. It re-establishes the correct architectural boundary between a write-heavy bootstrapping command (`init`) and a read-heavy analysis command (`check`). `init` must be self-contained and authoritative, while `check` can and should rely on the cached, indexed state produced by the former. This correction is essential for the stability and predictability of the entire system.

### 目标

1.  Modify `InitRunner.run_batch` in `packages/stitcher-application/src/stitcher/app/runners/init.py`.
2.  Ensure that the YAML content hashes are computed directly from the in-memory `DocstringIR` map that is generated from the source code, rather than from a premature index lookup.

### 基本原理

The `InitRunner` workflow must be idempotent and self-sufficient. By explicitly flattening the module's docstrings into an in-memory `DocstringIR` map *within* the `run_batch` method, we create a temporary, authoritative source of truth for that transaction. We can then use this map to both write the `.stitcher.yaml` file and to compute the hashes for the `stitcher.lock` file, guaranteeing consistency without any dependency on a potentially stale index.

### 标签

#intent/fix #flow/ready #priority/critical #comp/application #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/cache-validation #task/action/refactor #task/state/continue

---

### Script

#### Acts 1: Correct InitRunner's hash computation logic

I will patch `InitRunner` to compute hashes from its own in-memory data structures, severing the incorrect dependency on the index during the critical bootstrapping phase.

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/init.py
~~~~~
~~~~~python.old
                module_abs_path = self.root_path / module.file_path
                module_ws_rel = self.workspace.to_workspace_relative(module_abs_path)

                computed_fingerprints = self._compute_fingerprints(module)
                yaml_hashes = self.doc_manager.compute_yaml_content_hashes(module)

                all_fqns = set(computed_fingerprints.keys()) | set(yaml_hashes.keys())

                for fqn in all_fqns:
~~~~~
~~~~~python.new
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

                all_fqns = set(computed_fingerprints.keys()) | set(yaml_hashes.keys())

                for fqn in all_fqns:
~~~~~

### 下一步建议

This patch directly addresses the root cause of all 12 test failures. The next logical step is to run the entire test suite again. I am confident that with this fix, all tests will pass, and we can finally confirm that our new, high-performance indexing architecture is both correct and stable.
