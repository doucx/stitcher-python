Excellent. The failing tests confirm that our test suite is now correctly capturing the requirements defined in the truth table, and that the implementation is lagging behind. This is the "Red" state of TDD. Now, we can proceed to the "Green" state by fixing the code.

My analysis revealed two distinct bugs: one in the planning phase (`_generate_execution_plan`) and one in the execution phase (the `run` method's main loop). I will fix both.

## [WIP] fix: 修正 pump 的执行计划和指纹更新逻辑

### 错误分析
1.  **计划生成器缺陷**: `_generate_execution_plan` 方法未能根据真值表为 `update_code_fingerprint` 标志赋值。除了用户明确选择 `SKIP` 的情况外，所有其他决策（包括无冲突、覆盖、保留）都应将此标志设为 `True`，以确保代码状态与指纹同步。
2.  **执行器逻辑缺失**: `run` 方法的执行循环完全没有处理 `plan.update_code_fingerprint` 标志的逻辑。它错误地将“为新密钥更新代码指纹”的逻辑与“更新文档指纹”的逻辑混在了一起，并且从未更新现有密钥的代码指纹。

### 用户需求
修复 `pump` 命令的实现，使其完全符合新单元测试和真值表所定义的行为。这包括修正执行计划的生成逻辑和指纹的更新逻辑。

### 评论
这个修复是本次重构的核心。通过将 `pump` 的行为与清晰的、经过单元测试验证的规范（真值表）对齐，我们确保了其状态管理的一致性和可预测性。将代码和文档指纹的更新逻辑解耦，并正确地执行计划，将消除许多潜在的状态损坏错误。

### 目标
1.  **修复计划器**: 修改 `_generate_execution_plan` 方法，使其在所有非 `SKIP` 的情况下都将 `exec_plan.update_code_fingerprint` 设置为 `True`。
2.  **修复执行器**:
    *   在 `run` 方法中，为每个模块预先计算其当前的代码指纹，以提高效率。
    *   重构 `run` 方法的内部循环，使其能够独立地、正确地根据 `plan.update_code_fingerprint` 和 `plan.update_doc_fingerprint` 标志来更新相应的指纹。

### 基本原理
我们将分两步修复 `pump.py` 文件：
1.  首先，我们将重构 `_generate_execution_plan` 方法，使其逻辑更简洁，并直接映射真值表中的规则。所有非 `SKIP` 的决策路径都将设置 `update_code_fingerprint` 标志。
2.  其次，我们将重构 `run` 方法中的核心执行循环。我们将解耦当前混乱的指纹更新逻辑，引入一个清晰的流程：检查 `update_code_fingerprint` 标志并更新代码哈希，然后独立地检查 `update_doc_fingerprint` 标志并更新文档哈希。这将确保 `pump` 的行为是原子化且正确的。

### 标签
#intent/fix #flow/ready #priority/high #comp/engine #concept/state #concept/executor #scope/core #ai/instruct #task/domain/testing #task/object/pump-runner #task/action/refactor #task/state/continue

---
### Script

#### Acts 1: 修正执行计划生成器的逻辑

我们首先修复 `_generate_execution_plan` 方法，使其正确地根据真值表生成计划。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
    def _generate_execution_plan(
        self,
        module: ModuleDef,
        decisions: Dict[str, ResolutionAction],
        strip_requested: bool,
    ) -> Dict[str, FunctionExecutionPlan]:
        """根据用户决策和命令行标志，生成最终的函数级执行计划。"""
        plan: Dict[str, FunctionExecutionPlan] = {}
        source_docs = self.doc_manager.flatten_module_docs(module)

        for fqn in module.get_all_fqns():
            decision = decisions.get(fqn)
            has_source_doc = fqn in source_docs
            exec_plan = FunctionExecutionPlan(fqn=fqn)

            if decision == ResolutionAction.SKIP:
                pass  # All flags default to False
            elif (
                decision == ResolutionAction.HYDRATE_OVERWRITE
                or (decision is None and has_source_doc)
            ):
                exec_plan.hydrate_yaml = True
                exec_plan.update_doc_fingerprint = True
                if strip_requested:
                    exec_plan.strip_source_docstring = True
            elif decision == ResolutionAction.HYDRATE_KEEP_EXISTING:
                if strip_requested:
                    exec_plan.strip_source_docstring = True

            plan[fqn] = exec_plan

        return plan
~~~~~
~~~~~python.new
    def _generate_execution_plan(
        self,
        module: ModuleDef,
        decisions: Dict[str, ResolutionAction],
        strip_requested: bool,
    ) -> Dict[str, FunctionExecutionPlan]:
        """根据用户决策和命令行标志，生成最终的函数级执行计划。"""
        plan: Dict[str, FunctionExecutionPlan] = {}
        source_docs = self.doc_manager.flatten_module_docs(module)

        for fqn in module.get_all_fqns():
            decision = decisions.get(fqn)
            has_source_doc = fqn in source_docs
            exec_plan = FunctionExecutionPlan(fqn=fqn)

            if decision == ResolutionAction.SKIP:
                pass  # All flags default to False
            else:
                # All other cases require updating the code fingerprint.
                exec_plan.update_code_fingerprint = True

                if (
                    decision == ResolutionAction.HYDRATE_OVERWRITE
                    or (decision is None and has_source_doc)
                ):
                    exec_plan.hydrate_yaml = True
                    exec_plan.update_doc_fingerprint = True
                    if strip_requested:
                        exec_plan.strip_source_docstring = True
                elif decision == ResolutionAction.HYDRATE_KEEP_EXISTING:
                    if strip_requested:
                        exec_plan.strip_source_docstring = True
            plan[fqn] = exec_plan

        return plan
~~~~~

#### Acts 2: 修正执行器中指纹更新的逻辑

现在，我们重构 `run` 方法中的循环，以正确地执行计划所指定的指纹更新操作。

~~~~~act
patch_file
packages/stitcher-application/src/stitcher/app/runners/pump.py
~~~~~
~~~~~python.old
        for module in all_modules:
            file_plan = self._generate_execution_plan(module, decisions, strip)
            
            source_docs = self.doc_manager.flatten_module_docs(module)
            current_yaml_docs = self.doc_manager.load_docs_for_module(module)
            stored_hashes = self.sig_manager.load_composite_hashes(module)
            
            new_yaml_docs = current_yaml_docs.copy()
            new_hashes = copy.deepcopy(stored_hashes)
            
            file_had_updates = False
            file_has_errors = False # Check for atomic writes
            updated_keys_in_file = []
            reconciled_keys_in_file = []

            for fqn, plan in file_plan.items():
                if fqn in decisions and decisions[fqn] == ResolutionAction.SKIP:
                    unresolved_conflicts_count += 1
                    file_has_errors = True # Mark file as having issues, preventing partial save
                    bus.error(L.pump.error.conflict, path=module.file_path, key=fqn)
                    continue

                if plan.hydrate_yaml:
                    if fqn in source_docs and new_yaml_docs.get(fqn) != source_docs[fqn]:
                        new_yaml_docs[fqn] = source_docs[fqn]
                        updated_keys_in_file.append(fqn)
                        file_had_updates = True

                fp = new_hashes.get(fqn) or Fingerprint()
                
                if plan.update_doc_fingerprint:
                    if fqn in source_docs:
                        doc_hash = self.doc_manager.compute_yaml_content_hash(source_docs[fqn])
                        fp["baseline_yaml_content_hash"] = doc_hash
                        # If we have a new key (or recovering from invalid legacy), 
                        # we should try to grab its code hash too if available
                        if fqn not in stored_hashes:
                             current_fp = self.sig_manager.compute_fingerprints(module).get(fqn, Fingerprint())
                             if "current_code_structure_hash" in current_fp:
                                 fp["baseline_code_structure_hash"] = current_fp["current_code_structure_hash"]
                        new_hashes[fqn] = fp
                        file_had_updates = True
                
                if fqn in decisions and decisions[fqn] == ResolutionAction.HYDRATE_KEEP_EXISTING:
                    reconciled_keys_in_file.append(fqn)

                if plan.strip_source_docstring:
                    strip_jobs[module.file_path].append(fqn)

            # Atomic save logic: Only save if there were updates AND no errors in this file.
            # We also check if new_hashes != stored_hashes to support recovering legacy/corrupt signature files
            # even if 'file_had_updates' (meaning doc updates) is False.
            signatures_need_save = (new_hashes != stored_hashes)
            
            if not file_has_errors:
                if file_had_updates:
                    module_path = self.root_path / module.file_path
                    doc_path = module_path.with_suffix(".stitcher.yaml")
                    self.doc_manager.adapter.save(doc_path, new_yaml_docs)
                
                if file_had_updates or signatures_need_save:
                    self.sig_manager.save_composite_hashes(module, new_hashes)
                
            if updated_keys_in_file:
                total_updated_keys += len(updated_keys_in_file)
                bus.success(L.pump.file.success, path=module.file_path, count=len(updated_keys_in_file))
            
            if reconciled_keys_in_file:
                total_reconciled_keys += len(reconciled_keys_in_file)
                bus.info(L.pump.info.reconciled, path=module.file_path, count=len(reconciled_keys_in_file))
~~~~~
~~~~~python.new
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
            file_has_errors = False # Check for atomic writes
            updated_keys_in_file = []
            reconciled_keys_in_file = []

            for fqn, plan in file_plan.items():
                if fqn in decisions and decisions[fqn] == ResolutionAction.SKIP:
                    unresolved_conflicts_count += 1
                    file_has_errors = True # Mark file as having issues, preventing partial save
                    bus.error(L.pump.error.conflict, path=module.file_path, key=fqn)
                    continue

                if plan.hydrate_yaml:
                    if fqn in source_docs and new_yaml_docs.get(fqn) != source_docs[fqn]:
                        new_yaml_docs[fqn] = source_docs[fqn]
                        updated_keys_in_file.append(fqn)
                        file_had_updates = True

                fp = new_hashes.get(fqn) or Fingerprint()
                fqn_was_updated = False
                
                if plan.update_code_fingerprint:
                    current_fp = current_fingerprints.get(fqn, Fingerprint())
                    if "current_code_structure_hash" in current_fp:
                        fp["baseline_code_structure_hash"] = current_fp["current_code_structure_hash"]
                    if "current_code_signature_text" in current_fp:
                        fp["baseline_code_signature_text"] = current_fp["current_code_signature_text"]
                    fqn_was_updated = True

                if plan.update_doc_fingerprint:
                    if fqn in source_docs:
                        doc_hash = self.doc_manager.compute_yaml_content_hash(source_docs[fqn])
                        fp["baseline_yaml_content_hash"] = doc_hash
                        fqn_was_updated = True
                
                if fqn_was_updated:
                    new_hashes[fqn] = fp
                
                if fqn in decisions and decisions[fqn] == ResolutionAction.HYDRATE_KEEP_EXISTING:
                    reconciled_keys_in_file.append(fqn)

                if plan.strip_source_docstring:
                    strip_jobs[module.file_path].append(fqn)

            # Atomic save logic: Only save if there were updates AND no errors in this file.
            signatures_need_save = (new_hashes != stored_hashes)
            
            if not file_has_errors:
                if file_had_updates:
                    module_path = self.root_path / module.file_path
                    doc_path = module_path.with_suffix(".stitcher.yaml")
                    self.doc_manager.adapter.save(doc_path, new_yaml_docs)
                
                if signatures_need_save:
                    self.sig_manager.save_composite_hashes(module, new_hashes)
                
            if updated_keys_in_file:
                total_updated_keys += len(updated_keys_in_file)
                bus.success(L.pump.file.success, path=module.file_path, count=len(updated_keys_in_file))
            
            if reconciled_keys_in_file:
                total_reconciled_keys += len(reconciled_keys_in_file)
                bus.info(L.pump.info.reconciled, path=module.file_path, count=len(reconciled_keys_in_file))
~~~~~

### 下一步建议
现在，代码已经被修正以符合我们增强后的测试规范。请再次运行测试套件。我们预期的结果是所有测试都将通过。一旦通过，我们就可以生成一个 `[COMMIT]` 计划来正式地将这项重构工作记录到版本历史中。
