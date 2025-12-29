简要回答
我们遇到了三个集成测试失败，主要涉及 `pump` 命令在处理签名基线和旧版本 Schema 迁移时的逻辑缺陷。

`pump` 命令目前在更新文档时，会错误地将当前的“代码签名”直接覆盖为新的“基线”，这导致了“签名漂移”检测失效（它本应保留旧基线以便 `check` 能够发现代码变更）。此外，`pump` 缺乏显式的 Reformatting 阶段，导致旧版本的签名文件即使在处理后也没有迁移到新 Schema。

我将生成一个 `[fix]` 计划，通过在 `run_pump` 中引入智能的基线保留逻辑和显式的 Reformatting 步骤来修复这些问题。

## [WIP] fix(app): 修复 pump 命令中的签名基线破坏和 Schema 迁移遗漏

### 错误分析
1.  **Baseline Corruption**: 测试 `test_pump_does_not_corrupt_code_signature_baseline` 失败。`run_pump` 在将提取到的文档保存到签名文件时，简单粗暴地将当前计算出的代码结构哈希 (`current_code_structure_hash`) 赋值给了基线 (`baseline_code_structure_hash`)。这导致如果用户修改了代码签名（漂移）并运行 `pump`，`pump` 会隐式地“批准”这个变更，使得后续的 `check` 无法检测到签名漂移。**修复**：在 `pump` 更新签名条目时，必须检查并保留已存在的代码签名基线。
2.  **Legacy Schema Migration**: 测试 `test_pump_does_not_rewrite_synced_legacy_signatures` 失败。`pump` 仅在检测到文档变更（`updated_keys` 或 `reconciled_keys` 非空）时才写入签名文件。如果项目文档是同步的，`pump` 什么也不做，导致旧版本的签名文件（使用旧 Key 名）不会被迁移到新 Schema。**修复**：在 `run_pump` 结束前，增加一个显式的 `reformat` 阶段，确保所有扫描过的模块的签名文件都符合当前 Schema。
3.  **Atomic Failure**: 测试 `test_pump_is_atomic_per_file` 失败。这可能是由于上述逻辑的副作用，或者是 `run_pump` 错误地报告了成功状态。我们将通过修复前两个核心逻辑问题来观察此测试是否随之通过。

### 用户需求
确保 `stitcher pump` 命令在执行文档提取时：
1.  **绝对不** 隐式更新代码签名的基线，除非该函数是全新的。
2.  **总是** 确保存储的签名文件符合最新的 Schema，即使没有文档内容变更。

### 评论
这是一组关键的稳定性修复。Stitcher 的核心价值在于精准的状态追踪，`pump` 作为一种“同步”操作，绝不能破坏 `check` 所依赖的基线数据。

### 目标
1.  修改 `StitcherApp.run_pump` 方法。
2.  实现“保留现有基线”的逻辑：当更新签名指纹时，如果 `stored_hashes` 中已存在 `baseline_code_structure_hash`，则保留它，而不是使用当前的计算值覆盖。
3.  在 `run_pump` 的返回路径前，添加 `reformat_hashes_for_module` 调用循环。

### 基本原理
通过将“文档更新”与“代码签名基线更新”解耦，我们保证了 `check` 命令的权威性。`pump` 只应该负责 `yaml_content_hash` 的更新（因为它确实在修改 YAML），而对 `code_structure_hash` 应该保持只读/保留态度，除非是初始化新条目。

### 标签
#intent/fix #flow/ready #priority/high #comp/runtime #concept/state #scope/core #ai/instruct #task/domain/testing #task/object/pump-command #task/action/bug-fix #task/state/begin

---

### Script

#### Acts 1: 修复 `core.py` 中的 `run_pump` 逻辑

我们将修改 `packages/stitcher-application/src/stitcher/app/core.py`。
主要改动：
1.  在处理 `updated_keys` 时，增加逻辑判断：如果存在旧的 `baseline_code_structure_hash`，则保留之。
2.  在方法末尾添加 `reformat_hashes_for_module` 循环。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python
                # For keys where code doc was authoritative (updated/force-hydrated)
                for fqn in result["updated_keys"]:
                    fp = computed_fingerprints.get(fqn, Fingerprint())
                    # Atomically convert current to baseline for both code and doc hashes
                    if "current_code_structure_hash" in fp:
                        fp["baseline_code_structure_hash"] = fp[
                            "current_code_structure_hash"
                        ]
                        del fp["current_code_structure_hash"]
                    if "current_code_signature_text" in fp:
                        fp["baseline_code_signature_text"] = fp[
                            "current_code_signature_text"
                        ]
                        del fp["current_code_signature_text"]
                    if fqn in current_yaml_map:
                        fp["baseline_yaml_content_hash"] = current_yaml_map[fqn]
                    new_hashes[fqn] = fp

                # For keys where yaml doc was authoritative (reconciled)
~~~~~
~~~~~python
                # For keys where code doc was authoritative (updated/force-hydrated)
                for fqn in result["updated_keys"]:
                    fp = computed_fingerprints.get(fqn, Fingerprint())

                    # Check for existing baseline to preserve
                    stored_fp = new_hashes.get(fqn)

                    # Atomically convert current to baseline, BUT preserve existing code baselines
                    # to prevent implicit acceptance of signature drift.
                    if "current_code_structure_hash" in fp:
                        if stored_fp and "baseline_code_structure_hash" in stored_fp:
                            fp["baseline_code_structure_hash"] = stored_fp[
                                "baseline_code_structure_hash"
                            ]
                        else:
                            fp["baseline_code_structure_hash"] = fp[
                                "current_code_structure_hash"
                            ]
                        del fp["current_code_structure_hash"]

                    if "current_code_signature_text" in fp:
                        if stored_fp and "baseline_code_signature_text" in stored_fp:
                            fp["baseline_code_signature_text"] = stored_fp[
                                "baseline_code_signature_text"
                            ]
                        else:
                            fp["baseline_code_signature_text"] = fp[
                                "current_code_signature_text"
                            ]
                        del fp["current_code_signature_text"]

                    if fqn in current_yaml_map:
                        fp["baseline_yaml_content_hash"] = current_yaml_map[fqn]
                    new_hashes[fqn] = fp

                # For keys where yaml doc was authoritative (reconciled)
~~~~~

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/core.py
~~~~~
~~~~~python
        if total_updated == 0:
            bus.info(L.pump.run.no_changes)
        else:
            bus.success(L.pump.run.complete, count=total_updated)

        return PumpResult(success=True, redundant_files=redundant_files)

    def run_strip(self, files: Optional[List[Path]] = None) -> List[Path]:
~~~~~
~~~~~python
        if total_updated == 0:
            bus.info(L.pump.run.no_changes)
        else:
            bus.success(L.pump.run.complete, count=total_updated)

        # Reformat Phase: Ensure all processed modules have up-to-date signature schema
        for module in all_modules:
            self.sig_manager.reformat_hashes_for_module(module)

        return PumpResult(success=True, redundant_files=redundant_files)

    def run_strip(self, files: Optional[List[Path]] = None) -> List[Path]:
~~~~~

### 下一步建议
执行测试以验证修复是否有效。重点关注之前失败的 `test_pump_regression.py` 和 `test_pump_state_integrity.py`。
