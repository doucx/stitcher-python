简要回答
是的，测试按预期失败了，这确认了应用层 `PumpRunner` 中缺少返回冗余文件列表的逻辑。

我将生成一个修复计划，修改 `stitcher-application` 中的 `pump.py`。修复的核心逻辑是：在处理每个文件时，如果发现某个文档字符串已成功被 Stitcher 接管（即存在于源码中，且本次操作将其写入或确认到了 YAML 中），且本次操作没有执行剥离（Strip），则该文件被标记为“包含冗余文档”。

这个列表将被填充到 `PumpResult` 中返回，从而使 CLI 层能够检测到并提示用户。

## [WIP] fix(app): 修复 PumpRunner 不返回冗余文件列表的问题

### 用户需求
修复 `stitcher pump` 命令在成功提取文档后，未能向 CLI 报告冗余文件列表，导致 CLI 无法提示用户进行剥离操作的 Bug。

### 评论
这个修复补全了 `pump` 命令交互体验的最后一块拼图。它确保了“提取 -> 确认 -> 剥离”工作流的闭环。逻辑上，只有当文件没有错误（即 YAML 更新已持久化）时，我们才将其标记为冗余，这是为了防止用户在持久化失败的情况下误删源码文档。

### 目标
1.  修改 `packages/stitcher-application/src/stitcher/app/runners/pump.py`。
2.  在 `run` 方法中引入 `redundant_files_list` 收集器。
3.  在处理每个文件的循环中，检测是否存在“源码中有文档且未被剥离”的情况 (`file_has_redundancy`)。
4.  确保仅在文件处理无错误（`not file_has_errors`）时，才将该文件加入冗余列表。
5.  在 `PumpResult` 中返回填充好的列表。

### 基本原理
当 `pump` 操作成功将源码中的文档同步到 YAML（或确认 YAML 内容有效）时，源码中的文档字符串在逻辑上就变成了“冗余数据”。通过显式识别并返回这些文件，应用层为上层（CLI）提供了必要的上下文，使其能够智能地引导用户进行清理工作，而无需应用层自己处理 UI 交互。

### 标签
#intent/fix #flow/ready #priority/high
#comp/runtime #scope/core
#ai/instruct
#task/domain/application-logic #task/object/pump-runner #task/action/fix-redundancy-reporting
#task/state/end #task/status/completed

---

### Script

#### Acts 1: 实现冗余文件检测逻辑

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
        # --- Phase 3 & 4: Planning & Execution ---
        # Apply decisions, write files, and record stats
        strip_jobs = defaultdict(list)
        total_updated_keys = 0
        total_reconciled_keys = 0
        unresolved_conflicts_count = 0

        for module in all_modules:
            file_plan = self._generate_execution_plan(module, decisions, strip)

            source_docs = self.doc_manager.flatten_module_docs(module)
            current_yaml_docs = self.doc_manager.load_docs_for_module(module)
            stored_hashes = self.sig_manager.load_composite_hashes(module)

            # Pre-compute current fingerprints for efficiency
            current_fingerprints = self.sig_manager.compute_fingerprints(module)

            new_yaml_docs = current_yaml_docs.copy()
            new_hashes = copy.deepcopy(stored_hashes)

            file_had_updates = False
            file_has_errors = False  # Check for atomic writes
            updated_keys_in_file = []
            reconciled_keys_in_file = []

            for fqn, plan in file_plan.items():
                if fqn in decisions and decisions[fqn] == ResolutionAction.SKIP:
                    unresolved_conflicts_count += 1
                    file_has_errors = (
                        True  # Mark file as having issues, preventing partial save
                    )
                    bus.error(L.pump.error.conflict, path=module.file_path, key=fqn)
                    continue

                if plan.hydrate_yaml:
                    if (
                        fqn in source_docs
                        and new_yaml_docs.get(fqn) != source_docs[fqn]
                    ):
                        new_yaml_docs[fqn] = source_docs[fqn]
                        updated_keys_in_file.append(fqn)
                        file_had_updates = True

                fp = new_hashes.get(fqn) or Fingerprint()
                fqn_was_updated = False

                if plan.update_code_fingerprint:
                    current_fp = current_fingerprints.get(fqn, Fingerprint())
                    if "current_code_structure_hash" in current_fp:
                        fp["baseline_code_structure_hash"] = current_fp[
                            "current_code_structure_hash"
                        ]
                    if "current_code_signature_text" in current_fp:
                        fp["baseline_code_signature_text"] = current_fp[
                            "current_code_signature_text"
                        ]
                    fqn_was_updated = True

                if plan.update_doc_fingerprint:
                    if fqn in source_docs:
                        doc_hash = self.doc_manager.compute_yaml_content_hash(
                            source_docs[fqn]
                        )
                        fp["baseline_yaml_content_hash"] = doc_hash
                        fqn_was_updated = True

                if fqn_was_updated:
                    new_hashes[fqn] = fp

                if (
                    fqn in decisions
                    and decisions[fqn] == ResolutionAction.HYDRATE_KEEP_EXISTING
                ):
                    reconciled_keys_in_file.append(fqn)

                if plan.strip_source_docstring:
                    strip_jobs[module.file_path].append(fqn)

            # Atomic save logic: Only save if there were updates AND no errors in this file.
            signatures_need_save = new_hashes != stored_hashes

            if not file_has_errors:
                if file_had_updates:
                    module_path = self.root_path / module.file_path
                    doc_path = module_path.with_suffix(".stitcher.yaml")
                    self.doc_manager.adapter.save(doc_path, new_yaml_docs)

                if signatures_need_save:
                    self.sig_manager.save_composite_hashes(module, new_hashes)

            if updated_keys_in_file:
                total_updated_keys += len(updated_keys_in_file)
                bus.success(
                    L.pump.file.success,
                    path=module.file_path,
                    count=len(updated_keys_in_file),
                )

            if reconciled_keys_in_file:
                total_reconciled_keys += len(reconciled_keys_in_file)
                bus.info(
                    L.pump.info.reconciled,
                    path=module.file_path,
                    count=len(reconciled_keys_in_file),
                )

        # --- Phase 5: Stripping ---
        if strip_jobs:
            total_stripped_files = 0
            for file_path, whitelist in strip_jobs.items():
                source_path = self.root_path / file_path
                if not whitelist:
                    continue
                try:
                    original_content = source_path.read_text("utf-8")
                    stripped_content = self.transformer.strip(
                        original_content, whitelist=whitelist
                    )
                    if original_content != stripped_content:
                        source_path.write_text(stripped_content, "utf-8")
                        bus.success(
                            L.strip.file.success,
                            path=source_path.relative_to(self.root_path),
                        )
                        total_stripped_files += 1
                except Exception as e:
                    bus.error(L.error.generic, error=e)

            if total_stripped_files > 0:
                bus.success(L.strip.run.complete, count=total_stripped_files)

        # Phase 6: Ensure Signatures Integrity
        # This is a safety sweep. In most cases, Phase 4 handles it via 'signatures_need_save'.
        # But if files were skipped or other edge cases, we might want to check again?
        # Actually, Phase 4 covers the main "Update Logic".
        # Doing a reformat here might mask atomic failures if we aren't careful.
        # Let's rely on Phase 4's explicit save logic for now to respect atomicity.

        # Final Reporting
        if unresolved_conflicts_count > 0:
            bus.error(L.pump.run.conflict, count=unresolved_conflicts_count)
            return PumpResult(success=False)

        # We define activity as actual changes to data (updates or strips).
        # Reconciliation is a resolution state change but not a data "pump", so we respect
        # existing test expectations that reconciliation alone = "no changes" in terms of content output.
        has_activity = (total_updated_keys > 0) or strip_jobs

        if not has_activity:
            bus.info(L.pump.run.no_changes)
        else:
            bus.success(L.pump.run.complete, count=total_updated_keys)

        return PumpResult(success=True, redundant_files=[])
~~~~~
~~~~~python.new
        # --- Phase 3 & 4: Planning & Execution ---
        # Apply decisions, write files, and record stats
        strip_jobs = defaultdict(list)
        redundant_files_list: List[Path] = []
        total_updated_keys = 0
        total_reconciled_keys = 0
        unresolved_conflicts_count = 0

        for module in all_modules:
            file_plan = self._generate_execution_plan(module, decisions, strip)

            source_docs = self.doc_manager.flatten_module_docs(module)
            current_yaml_docs = self.doc_manager.load_docs_for_module(module)
            stored_hashes = self.sig_manager.load_composite_hashes(module)

            # Pre-compute current fingerprints for efficiency
            current_fingerprints = self.sig_manager.compute_fingerprints(module)

            new_yaml_docs = current_yaml_docs.copy()
            new_hashes = copy.deepcopy(stored_hashes)

            file_had_updates = False
            file_has_errors = False  # Check for atomic writes
            file_has_redundancy = False
            updated_keys_in_file = []
            reconciled_keys_in_file = []

            for fqn, plan in file_plan.items():
                if fqn in decisions and decisions[fqn] == ResolutionAction.SKIP:
                    unresolved_conflicts_count += 1
                    file_has_errors = (
                        True  # Mark file as having issues, preventing partial save
                    )
                    bus.error(L.pump.error.conflict, path=module.file_path, key=fqn)
                    continue

                if plan.hydrate_yaml:
                    if (
                        fqn in source_docs
                        and new_yaml_docs.get(fqn) != source_docs[fqn]
                    ):
                        new_yaml_docs[fqn] = source_docs[fqn]
                        updated_keys_in_file.append(fqn)
                        file_had_updates = True

                fp = new_hashes.get(fqn) or Fingerprint()
                fqn_was_updated = False

                if plan.update_code_fingerprint:
                    current_fp = current_fingerprints.get(fqn, Fingerprint())
                    if "current_code_structure_hash" in current_fp:
                        fp["baseline_code_structure_hash"] = current_fp[
                            "current_code_structure_hash"
                        ]
                    if "current_code_signature_text" in current_fp:
                        fp["baseline_code_signature_text"] = current_fp[
                            "current_code_signature_text"
                        ]
                    fqn_was_updated = True

                if plan.update_doc_fingerprint:
                    if fqn in source_docs:
                        doc_hash = self.doc_manager.compute_yaml_content_hash(
                            source_docs[fqn]
                        )
                        fp["baseline_yaml_content_hash"] = doc_hash
                        fqn_was_updated = True

                if fqn_was_updated:
                    new_hashes[fqn] = fp

                if (
                    fqn in decisions
                    and decisions[fqn] == ResolutionAction.HYDRATE_KEEP_EXISTING
                ):
                    reconciled_keys_in_file.append(fqn)

                if plan.strip_source_docstring:
                    strip_jobs[module.file_path].append(fqn)

                # Check for redundancy:
                # If the doc exists in source and we are not stripping it in this run,
                # it is potentially redundant because we have either updated or reconciled it in YAML.
                if fqn in source_docs and not plan.strip_source_docstring:
                    file_has_redundancy = True

            # Atomic save logic: Only save if there were updates AND no errors in this file.
            signatures_need_save = new_hashes != stored_hashes

            if not file_has_errors:
                if file_had_updates:
                    module_path = self.root_path / module.file_path
                    doc_path = module_path.with_suffix(".stitcher.yaml")
                    self.doc_manager.adapter.save(doc_path, new_yaml_docs)

                if signatures_need_save:
                    self.sig_manager.save_composite_hashes(module, new_hashes)

                if file_has_redundancy:
                    redundant_files_list.append(Path(module.file_path))

            if updated_keys_in_file:
                total_updated_keys += len(updated_keys_in_file)
                bus.success(
                    L.pump.file.success,
                    path=module.file_path,
                    count=len(updated_keys_in_file),
                )

            if reconciled_keys_in_file:
                total_reconciled_keys += len(reconciled_keys_in_file)
                bus.info(
                    L.pump.info.reconciled,
                    path=module.file_path,
                    count=len(reconciled_keys_in_file),
                )

        # --- Phase 5: Stripping ---
        if strip_jobs:
            total_stripped_files = 0
            for file_path, whitelist in strip_jobs.items():
                source_path = self.root_path / file_path
                if not whitelist:
                    continue
                try:
                    original_content = source_path.read_text("utf-8")
                    stripped_content = self.transformer.strip(
                        original_content, whitelist=whitelist
                    )
                    if original_content != stripped_content:
                        source_path.write_text(stripped_content, "utf-8")
                        bus.success(
                            L.strip.file.success,
                            path=source_path.relative_to(self.root_path),
                        )
                        total_stripped_files += 1
                except Exception as e:
                    bus.error(L.error.generic, error=e)

            if total_stripped_files > 0:
                bus.success(L.strip.run.complete, count=total_stripped_files)

        # Phase 6: Ensure Signatures Integrity
        # This is a safety sweep. In most cases, Phase 4 handles it via 'signatures_need_save'.
        # But if files were skipped or other edge cases, we might want to check again?
        # Actually, Phase 4 covers the main "Update Logic".
        # Doing a reformat here might mask atomic failures if we aren't careful.
        # Let's rely on Phase 4's explicit save logic for now to respect atomicity.

        # Final Reporting
        if unresolved_conflicts_count > 0:
            bus.error(L.pump.run.conflict, count=unresolved_conflicts_count)
            return PumpResult(success=False)

        # We define activity as actual changes to data (updates or strips).
        # Reconciliation is a resolution state change but not a data "pump", so we respect
        # existing test expectations that reconciliation alone = "no changes" in terms of content output.
        has_activity = (total_updated_keys > 0) or strip_jobs

        if not has_activity:
            bus.info(L.pump.run.no_changes)
        else:
            bus.success(L.pump.run.complete, count=total_updated_keys)

        return PumpResult(success=True, redundant_files=redundant_files_list)
~~~~~

### 下一步建议
运行测试 `pytest packages/stitcher-cli/tests/integration/test_pump_strip_interaction.py` 以验证修复是否生效。
如果测试通过，说明 `pump` 命令的重构（净化应用层 + 修复 CLI 交互）已圆满完成。
